
import argparse
import json
import logging
import math
import os
import random
import socket
import struct
import sys
import threading
import time
from multiprocessing import Queue
from typing import List
from typing import Tuple

import lz4.frame
import numpy as np
from pyinstrument import Profiler

from .common import ( Body, Camera,  Shape,  TimeLoggingContainer)
from .object import GObject
from .config import ClientConfig, GameConfig
from .content import Content
from .common import StateDecoder, StateEncoder
from .player import Player
from .inputs import get_input_events
from .renderer import Renderer
from .utils import gen_id
from .event import InputEvent, Event
from .utils import TickPerSecCounter
from . import gamectx
from .clock import clock,StepClock
import gym

HEADER_SIZE = 16
LATENCY_LOG_SIZE = 10000

def receive_data(sock):
    done = False
    all_data = b''
    while not done:
        sock.settimeout(5.0)
        data, server = sock.recvfrom(1500)
        chunk_num, chunks = struct.unpack('ll', data[:HEADER_SIZE])
        all_data += data[HEADER_SIZE:]
        if chunk_num == chunks:
            done = True
    # all_data = lz4.frame.decompress(all_data)
    all_data = all_data.decode("utf-8")
    return all_data


def send_request(request_data, server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        data_st = json.dumps(request_data, cls=StateEncoder)
        # Send data
        data_bytes = bytes(data_st, 'utf-8')
        # print(f"bytes:{len(data_bytes)}")
        # data_bytes = lz4.frame.compress(data_bytes)
        sent = sock.sendto(data_bytes,
                           server_address)
        data = receive_data(sock)
    except Exception as e:
        print(e)
        return None
    finally:
        sock.close()
    return json.loads(data, cls=StateDecoder)

class RemoteClient:
    """
    Stores session info 
    """

    def __init__(self, client_id):
        self.id = client_id
        self.last_snapshot_time_ms = 0
        self.latency_history = [None for i in range(LATENCY_LOG_SIZE)]
        self.player_id = None
        self.conn_info = None
        self.request_counter = 0
        self.unconfirmed_messages = set()
        self.outgoing_events:List[Event] = []

    def add_event(self,e:Event):
        self.outgoing_events.append(e)
    
    def clear_events(self):
        self.outgoing_events = []
    
    def pull_events_snapshot(self):
        results = []
        for e in self.outgoing_events:
            results.append(e.get_snapshot())
        self.clear_events()
        return results

    def add_latency(self, latency: float):
        self.latency_history[self.request_counter % LATENCY_LOG_SIZE] = latency
        self.request_counter += 1

    def avg(self):
        vals = [i for i in self.latency_history if i is not None]
        return math.fsum(vals)/len(vals)

    def get_id(self):
        return self.id

    def __repr__(self):
        return "Client: id: {}, player_id: {}".format(self.id,self.player_id)


class ClientConnector:
    # TODO, change to client + server connection

    def __init__(self, config:ClientConfig):
        self.config = config
        self.incomming_buffer: Queue = Queue()  # event buffer
        self.outgoing_buffer: Queue = Queue()  # state buffer
        self.running = True
        self.client_id = self.config.client_id

        self.latency_log = [None for i in range(LATENCY_LOG_SIZE)]
        self.last_latency_ms = None
        self.last_latency_ticks = None
        self.request_counter = 0
        self.server_tick = None
        self.connection_clock = StepClock()

        self.ticks_per_second = 60
        self.last_received_snapshots = []
        self.sync_freq = 0
        self.last_sync = 0

    def add_network_info(self, latency: int, success: bool):
        self.latency_log[self.request_counter % LATENCY_LOG_SIZE] = {'latency': latency, 'success': success}

    def get_avg_latency(self):
        vals = [i for i in self.latency_log if i is not None]
        return math.fsum(vals['latency'])/len(vals)

    def get_success_rate(self):
        vals = [i for i in self.latency_log if i is not None]
        success = sum([1 for v in vals if v['success']])
        return success/len(vals)

    def create_request(self):
        request_info = {
            'client_id': "" if self.client_id is None else self.client_id,
            'last_latency_ticks': self.last_latency_ticks,
            'snapshots_received': self.last_received_snapshots,
            'player_type': self.config.player_type,
            'is_human':self.config.is_human,
            'message': "UPDATE"
        }

        # Get items:
        outgoing_items = []
        done = False
        while (not done):
            if self.outgoing_buffer.qsize() == 0:
                done = True
                break
            outgoing_item = self.outgoing_buffer.get()
            if outgoing_item is None or len(outgoing_item) == 0:
                done = True
            else:
                outgoing_items.append(outgoing_item)

        start_time = time.time()
        response = send_request({
            'info': request_info,
            'items': outgoing_items},
            server_address = (self.config.server_hostname,self.config.server_port))
        self.last_latency_ms = time.time() - start_time
        self.last_latency_ticks = int(60 * self.last_latency_ms)

        if response is None:
            print("Packet loss or error occurred")
            self.add_network_info(self.last_latency_ms, False)
        else:
            # Log latency
            self.add_network_info(self.last_latency_ms, True)
            response_info = response['info']
            self.last_received_snapshots = [response_info['snapshot_timestamp']]

            # set clock
            if time.time() - self.last_sync > self.sync_freq:
                self.server_tick = response_info['server_tick'] - (self.last_latency_ticks//2)
                tick_delta = self.server_tick - clock.get_time()
                if abs(tick_delta)>100:
                    clock.set_absolute_time(self.server_tick)
                elif tick_delta>0:
                    #
                    clock.set_absolute_time(clock.get_exact_time()+1)
                elif tick_delta<0:
                    clock.set_absolute_time(clock.get_exact_time()-1)

                    # clock.set_absolute_time(clock.get_exact_time()-time_delta//time_delta)
                self.last_sync = time.time()

            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter += 1
        self.connection_clock.tick(self.ticks_per_second)

    def start_connection(self, callback=None):
        print("Starting connection to server")

        while self.running:
            self.create_request()


class GameClient:

    def __init__(self,
                 renderer: Renderer,
                 config: ClientConfig):

        self.config = config
        self.content:Content = gamectx.content
        self.render_delay_in_ms = renderer.config.render_delay_in_ms  # tick gap + latency
        self.frames_per_second = config.frames_per_second
        self.render_last_update = 0
        self.render_update_freq = 0 if self.frames_per_second == 0 else (1.0/self.frames_per_second)  * 1000
        self.frame_limit = False# self.frames_per_second != gamectx.config.tick_rate

        self.server_info_history = TimeLoggingContainer(100)
        self.player: Player = None  # TODO: move to history data managed for rendering consistency
        self.step_counter = 0
        self.renderer:Renderer = renderer
        self.tick_counter = TickPerSecCounter(2)
        self.render_time = 0
        if self.config.is_human:            
            self.renderer.initialize()

        self.connector = None
        if self.config.is_remote:
            print("Creating remote connection")
            self.connector = ClientConnector(config= config)
            #TODO, separate process instead?
            self.connector_thread = threading.Thread(target=self.connector.start_connection, args=())
            self.connector_thread.daemon = True
            self.connector_thread.start()
        else:
            self.player = self.content.new_player(
                client_id = config.client_id, 
                player_type=config.player_type, 
                is_human=self.config.is_human)

    # def sync_time(self):
    #     if self.connector is None:
    #         return
    #     if self.connector.server_tick is not None:
    #         clock.set_absolute_time(self.connector.server_tick)

    def send_local_events(self):
        if self.connector is None:
            return
        event_snapshot = gamectx.event_manager.get_client_snapshot()
        if len(event_snapshot) >0 and self.connector.outgoing_buffer.qsize() < 30:
            self.connector.outgoing_buffer.put(event_snapshot)

        # Clear Events after sending to Server
        # TODO: add support for selective removal of events. eg keep local events  like quite request
        gamectx.event_manager.clear()

    def get_remote_state(self):
        if self.connector is None:
            return
        done = False
        while (not done):
            if self.connector.incomming_buffer.qsize() == 0:
                incomming_data = None
            else:
                incomming_data = self.connector.incomming_buffer.get()

            if incomming_data is None:
                done = True
                break
            else:
                gamectx.load_snapshot(incomming_data['snapshot'])
                # self.sync_time()

                self.server_info_history.add(
                    incomming_data['info']['snapshot_timestamp'],
                    incomming_data['info'])

    def update_player_info(self,render_time):
        if self.connector is None:
            return
        server_info_timestamp, server_info = self.server_info_history.get_prev_entry(render_time)
        # server_info_timestamp, server_info = self.server_info_history.get_latest_with_timestamp()
        # Note, loaded immediately rather than at render time. this could be an issue?
        if server_info is not None and server_info['player_id'] is not None and server_info['player_id'] != "":
            self.player = gamectx.player_manager.get_player(str(server_info['player_id']))


    def run_step(self):
       
        self.render_time = max(0, clock.get_time() - self.render_delay_in_ms)
        # Get Input Events and put in output buffer
        # TODO: make logic cleaner
        if self.player is not None:
            events = []
            if self.config.is_human:
                input_events = get_input_events(self.player)
                events.extend(input_events)
            events.extend(self.player.pull_input_events())
            gamectx.event_manager.add_events(events)
        
        # Send events
        self.send_local_events()
        # Get Game Snapshot
        self.get_remote_state()
        self.update_player_info(self.render_time)
        self.tick_counter.tick()
        self.step_counter += 1
    
    def render(self,force=False):
        # if (force or not self.frame_limit or ((self.render_time - self.render_last_update)*2 >= self.render_update_freq)):
        self.renderer.set_log_info("TPS: {} ".format(self.tick_counter.avg()))
        self.renderer.process_frame(
            render_time=self.render_time,
            player=self.player)

        self.content.post_process_frame(
            render_time=self.render_time,
            player=self.player,
            renderer=self.renderer)
        self.renderer.render_frame()
        self.render_last_update = self.render_time

        if self.config.is_human:
            self.renderer.play_sounds(gamectx.get_sound_events())

    def get_rgb_array(self):
        return self.renderer.get_last_frame()
            