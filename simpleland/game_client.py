
import socket
import sys

import logging
from typing import Tuple

import numpy as np

from simpleland.common import (TimeLoggingContainer, SLObject, SLVector, SLShape, SLCamera, SLBody, SLClock, SimClock)
from simpleland.physics_engine import SLPhysicsEngine
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer

from pymunk import Vec2d
import pymunk

import os
import json
import time
import lz4.frame
import struct
import threading
import argparse
import random

HEADER_SIZE = 16
def receive_data(sock):
    done = False
    all_data = b''
    while not done:
        sock.settimeout(1.0)
        data, server = sock.recvfrom(4096)
        chunk_num,chunks  = struct.unpack('ll',data[:HEADER_SIZE])
        all_data += data[HEADER_SIZE:]
        if chunk_num == chunks:
            done = True
    return lz4.frame.decompress(all_data).decode('utf-8')

def send_request(request_data , server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        data_st = json.dumps(request_data, cls=StateEncoder)
        # Send data
        sent = sock.sendto(lz4.frame.compress(bytes(data_st,'utf-8')), 
            server_address)
        data = receive_data(sock)
    except Exception as e:
        print(e)
        return None
    finally:
        sock.close()
    return json.loads(data, cls=StateDecoder)

from multiprocessing import Queue
LATENCY_LOG_SIZE = 10000
import math

from simpleland.common import build_interpolated_object

class ClientConnector:
    # TODO, change to client + server connection

    def __init__(self, client_id, server_address = ('localhost', 10001)):
        self.server_address = server_address
        self.incomming_buffer:Queue= Queue()# event buffer
        self.outgoing_buffer:Queue = Queue()# state buffer
        self.running = True
        self.client_id = client_id

        self.latency_log = [None for i in range(LATENCY_LOG_SIZE)]
        self.last_latency_ms = None
        self.request_counter =0
        self.absolute_server_time = None

        self.clock = SimClock() # clock for controlling network tick speed
        self.ticks_per_second = 64
        self.last_received_snapshots = []

    def add_network_info(self,latency:int, success:bool):

        self.latency_log[self.request_counter % LATENCY_LOG_SIZE] = {'latency':latency, 'success': success}
    
    def get_avg_latency(self):
        vals = [i for i in self.latency_log if i is not None]
        return math.fsum(vals['latency'])/len(vals)

    def get_success_rate(self):
        vals = [i for i in self.latency_log if i is not None]
        success = sum([1 for v in vals if v['success']])
        return success/len(vals)

    def create_request(self):
        request_info = {
            'client_id' : "" if self.client_id is None else self.client_id,
            'last_latency_ms' : self.last_latency_ms,
            'snapshots_received': self.last_received_snapshots,
            'message':"UPDATE"
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
                'info':request_info,
                'items': outgoing_items},
            self.server_address)
        last_latency_ms = (time.time() * 1000) - start_time

        if response is None:
            print("Packet loss or error occurred")
            self.add_network_info(last_latency_ms,False)
        else:
            # Log latency
            self.add_network_info(last_latency_ms,True)
            response_info = response['info']
            self.last_received_snapshots = [response_info['snapshot_timestamp']]

            # set clock
            self.absolute_server_time = (time.time()*1000) - float(response_info['server_time_ms']) - last_latency_ms
            
            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter +=1
        self.clock.tick(self.ticks_per_second)


    def start_connection(self, callback=None):
        print("Starting connection to server")

        while self.running:
            self.create_request()

from simpleland.config import GameConfig, ClientConfig  


class GameClient:

    def __init__(self, 
            game: SLGame, 
            renderer: SLRenderer, 
            config: ClientConfig, 
            connector: ClientConnector):

        self.config = config
        self.game:SLGame = SLGame(config)
        self.connector = connector
        self.render_delay_in_ms = 25 #tick gap + latency
        self.frames_per_second = config

        # RL Agent will be different

        self.server_info_history = TimeLoggingContainer(100)
        self.player:SLHumanPlayer = None #TODO: move to history data managed for rendering consistency
        self.step_counter = 0
        self.renderer = renderer

    def load_response_data(self):
        done = False
        while (not done):
            if self.connector.incomming_buffer.qsize() ==0:
                incomming_data = None
            else:
                incomming_data = self.connector.incomming_buffer.get()
            if incomming_data is None:
                done = True
                break
            else:
                self.game.load_snapshot(incomming_data['snapshot'])
                self.server_info_history.add(
                    incomming_data['info']['snapshot_timestamp'],
                    incomming_data['info'])

    def run_step(self):
            # Process Any Local Events

        if self.connector.absolute_server_time is not None:
            self.game.clock.set_absolute_time(self.connector.absolute_server_time)
        
        render_time = max(0,self.game.clock.get_time() - self.render_delay_in_ms)

        # Get Input Events and put in output buffer
        if self.player is not None:
            self.game.event_manager.add_events(self.player.pull_input_events())

        event_snapshot = self.game.event_manager.get_snapshot()
        if self.connector.outgoing_buffer.qsize() < 30:
            self.connector.outgoing_buffer.put(event_snapshot)

        # Clear Events after sending to Server 
        # TODO: add support for selective removal of events. eg keep local events  like quite request
        self.game.event_manager.clear()

        # Get Game Snapshot
        self.load_response_data()

        server_info_timestamp, server_info = self.server_info_history.get_prev_entry(render_time)
        #Note, loaded immediately rather than at render time. this could be an issue?
        if server_info is not None and server_info['player_id'] is not "":
            self.player = self.game.player_manager.get_player(server_info['player_id'])
            # obj = self.game.get_object_manager().get_by_id(self.player.get_object_id(),render_time)

        # Render
        if self.player is not None:

            self.renderer.process_frame(
                render_time,
                self.player.get_object_id(),
                self.game.object_manager)
            self.renderer.render_frame()
        self.renderer.play_sounds(self.game.get_sound_events(render_time))
        self.game.process_events()
        self.game.clock.tick(self.config.frames_per_second)
        self.step_counter += 1

    def run(self):

        # Create Renderer
        while self.game.game_state == "RUNNING":
            self.run_step()
from simpleland.utils import gen_id
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", default="640x480",help="resolution eg, [f,640x480]")
    parser.add_argument("--hostname", default="localhost",help="hostname or ip, default is localhost")
    parser.add_argument("--port", default=10001, help="port")
    parser.add_argument("--client_id", default=gen_id(), help="user id, default is random")
    parser.add_argument("--render_shapes", action='store_true', help="render actual shapes")

    args = parser.parse_args()

    config = GameConfig()

    if args.resolution == 'f':
        import pygame
        pygame.init()
        infoObject = pygame.display.Info()
        config.renderer.resolution = (infoObject.current_w, infoObject.current_h)
    else:
        res_string = args.resolution.split("x")
        config.renderer.resolution = (int(res_string[0]), int(res_string[1]))

    connector = ClientConnector(client_id = args.client_id, server_address=(args.hostname,args.port))
    connector_thread =threading.Thread(target=connector.start_connection, args=())
    connector_thread.daemon = True
    connector_thread.start()

    config.renderer.render_shapes = args.render_shapes


    game = SLGame(config)

    renderer = SLRenderer(config.renderer)
    game_client = GameClient(
        game = game, 
        renderer=renderer,
        config = config.client,
        connector=connector)

    game_client.run()

if __name__ == "__main__":
    main()
