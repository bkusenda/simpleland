
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
from typing import Tuple

import lz4.frame
import numpy as np
from pyinstrument import Profiler

from simpleland.common import (SimClock, Body, Camera, Clock, \
                               Shape, TimeLoggingContainer)
from simpleland.object import GObject
from simpleland.config import ClientConfig, GameConfig
from simpleland.content import Content
from simpleland.common import StateDecoder, StateEncoder
from simpleland.player import Player, get_input_events
from simpleland.renderer import Renderer
from simpleland.utils import gen_id
from simpleland.event import InputEvent
from simpleland.utils import TickPerSecCounter
from simpleland import gamectx

import gym

HEADER_SIZE = 16
LATENCY_LOG_SIZE = 10000

def receive_data(sock):
    done = False
    all_data = b''
    while not done:
        sock.settimeout(1.0)
        data, server = sock.recvfrom(4096)
        chunk_num, chunks = struct.unpack('ll', data[:HEADER_SIZE])
        all_data += data[HEADER_SIZE:]
        if chunk_num == chunks:
            done = True
    return lz4.frame.decompress(all_data).decode('utf-8')


def send_request(request_data, server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        data_st = json.dumps(request_data, cls=StateEncoder)
        # Send data
        sent = sock.sendto(lz4.frame.compress(bytes(data_st, 'utf-8')),
                           server_address)
        data = receive_data(sock)
    except Exception as e:
        print(e)
        return None
    finally:
        sock.close()
    return json.loads(data, cls=StateDecoder)


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
        self.request_counter = 0
        self.absolute_server_time = None

        self.clock = SimClock()  # clock for controlling network tick speed
        self.ticks_per_second = 64
        self.last_received_snapshots = []

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
            'last_latency_ms': self.last_latency_ms,
            'snapshots_received': self.last_received_snapshots,
            'player_type': self.config.player_type,
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

        start_time = time.time() * 1000
        response = send_request({
            'info': request_info,
            'items': outgoing_items},
            server_address = (self.config.server_hostname,self.config.server_port))
        last_latency_ms = (time.time() * 1000) - start_time

        if response is None:
            print("Packet loss or error occurred")
            self.add_network_info(last_latency_ms, False)
        else:
            # Log latency
            self.add_network_info(last_latency_ms, True)
            response_info = response['info']
            self.last_received_snapshots = [response_info['snapshot_timestamp']]

            # set clock
            self.absolute_server_time = (time.time()*1000) - float(response_info['server_time_ms']) - last_latency_ms

            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter += 1
        self.clock.tick(self.ticks_per_second)

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
        self.frame_limit = self.frames_per_second != gamectx.config.tick_rate

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
            self.player = self.content.new_player(client_id = config.client_id, player_type=config.player_type)

    def sync_time(self):
        if self.connector is None:
            return
        if self.connector.absolute_server_time is not None:
            gamectx.clock.set_absolute_time(self.connector.absolute_server_time)


    def send_local_events(self):
        if self.connector is None:
            return
        event_snapshot = gamectx.event_manager.get_snapshot()
        if self.connector.outgoing_buffer.qsize() < 30:
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
                self.server_info_history.add(
                    incomming_data['info']['snapshot_timestamp'],
                    incomming_data['info'])

    def update_player_info(self,render_time):
        if self.connector is None:
            return
        server_info_timestamp, server_info = self.server_info_history.get_prev_entry(render_time)
        # Note, loaded immediately rather than at render time. this could be an issue?
        if server_info is not None and server_info['player_id'] is not None and server_info['player_id'] != "":
            self.player = gamectx.player_manager.get_player(server_info['player_id'])
            # obj = gamectx.get_object_manager().get_by_id(self.player.get_object_id(),render_time)

    def run_step(self):
        self.sync_time()
        
        self.render_time = max(0, gamectx.clock.get_time() - self.render_delay_in_ms)
        # Get Input Events and put in output buffer
        # TODO: make logic cleaner
        if self.player is not None:
            events = []
            if self.config.is_human:
                input_events = get_input_events(self.player.get_id())
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
        if (force or not self.frame_limit or ((self.render_time - self.render_last_update)*2 >= self.render_update_freq)):
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
            self.renderer.play_sounds(gamectx.get_sound_events(self.render_time))

    def get_rgb_array(self):
        return self.renderer.get_last_frame()
            

    
        
