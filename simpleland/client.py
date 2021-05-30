
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

from .common import ( TimeLoggingContainer)
from .camera import Camera
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
        sock.settimeout(1.0)
        data, server = sock.recvfrom(4096)
        chunk_num, chunks = struct.unpack('ll', data[:HEADER_SIZE])
        all_data += data[HEADER_SIZE:]
        if chunk_num == chunks:
            done = True
    all_data = lz4.frame.decompress(all_data)
    return all_data.decode("utf-8")


def send_request(request_data, server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        data_st = json.dumps(request_data, cls=StateEncoder)
        # Send data
        data_bytes = bytes(data_st, 'utf-8')
        # print(f"bytes:{len(data_bytes)}")
        data_bytes = lz4.frame.compress(data_bytes)
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
        self.ticks_per_second = 20

        self.connection_clock = StepClock(self.ticks_per_second)

        self.last_received_snapshots = []
        self.sync_freq = 2
        self.last_sync = 0

        self.report_freq = .5
        self.last_report = 0

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
        self.last_latency = time.time() - start_time

        if response is None:
            print("Packet loss or error occurred")
            self.add_network_info(self.last_latency_ms, False)
        else:
            # Log latency
            self.add_network_info(self.last_latency_ms, True)
            response_info = response['info']
            self.last_received_snapshots = [response_info['snapshot_timestamp']]

            # set clock
            if (time.time() - self.last_sync )>= self.sync_freq:
                server_game_time = response_info['server_time'] - self.last_latency/2
                if abs(server_game_time - clock.get_game_time()) > 0.1:
                    clock.set_start_time(time.time() - server_game_time)

                self.last_sync = time.time()

            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter += 1
        self.connection_clock.tick()

        if (time.time() - self.last_report) > self.report_freq:
            self.last_report = time.time()

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
        self.frame_limit = False# self.frames_per_second != gamectx.config.tick_rate

        self.server_info_history = TimeLoggingContainer(100)
        self.player: Player = None  # TODO: move to history data managed for rendering consistency
        self.step_counter = 0
        self.renderer:Renderer = renderer
        self.tick_counter = TickPerSecCounter(2)
        self.last_obj_sync = 0
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

    def send_local_events(self):
        if self.connector is None:
            return
        event_snapshot = gamectx.event_manager.get_client_snapshot()
        if len(event_snapshot) >0:
            if self.connector.outgoing_buffer.qsize() < 300:
                self.connector.outgoing_buffer.put(event_snapshot)
            else:
                print("Queue is large")
        

    def sync_with_remote_state(self):
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
                client_obj_ids = set()
                if self.player is not None:
                    player_obj_id = self.player.get_object_id()
                    client_obj_ids.add(player_obj_id)
                client_obj_snapshots = gamectx.load_snapshot(
                    incomming_data['snapshot'],
                    client_obj_ids = client_obj_ids)

                self.server_info_history.add(
                    incomming_data['info']['snapshot_timestamp'],
                    incomming_data['info'])


                sync_required = ((clock.get_exact_time() - self.last_obj_sync) >=100 )
                are_insync = True
                for obj_id, data in client_obj_snapshots.items():
                    local_obj:GObject = gamectx.object_manager.get_by_id(obj_id)
                    obj:GObject = gamectx.build_object_from_dict(data)
                    
                    if sync_required or obj.get_position() == local_obj.get_position():
                        local_obj.load_snapshot(data)
                        local_obj.sync_position()
                    elif obj.get_position() != local_obj.get_position() :                        
                        local_obj.load_snapshot(data,{'position','_action'})
                        are_insync = False
                            
                if are_insync:        
                    self.last_obj_sync = clock.get_exact_time()
  

    def update_player_info(self):
        if self.connector is None:
            return
        server_info_timestamp, server_info = self.server_info_history.get_latest_with_timestamp()
        if server_info is not None and server_info.get('player_id',"") != "":
            self.player = gamectx.player_manager.get_player(str(server_info['player_id']))


    def run_step(self):
     
        if self.player is not None:
            input_events = self.player.pull_input_events()
            if self.config.is_human:
                input_events.extend(get_input_events(self.player))
            
            for event in input_events:
                if self.content.is_valid_input_event(event):
                    gamectx.event_manager.add_event(event)
        
        # Send events
        self.send_local_events()

        # Get Game Snapshot
        self.sync_with_remote_state()
        self.update_player_info()
        self.tick_counter.tick()
        self.step_counter += 1
    
    def render(self,force=False):
        self.renderer.set_log_info("TPS: {} ".format(self.tick_counter.avg()))
        self.renderer.process_frame(player=self.player)
        self.content.post_process_frame( player=self.player, renderer=self.renderer)
        self.renderer.render_frame()

        if self.config.is_human:
            self.renderer.play_sounds(gamectx.get_sound_events())

    def get_rgb_array(self):
        return self.renderer.get_last_frame()
            