
import socket
import sys

import logging
from typing import Tuple

import numpy as np

from simpleland.common import (SLObject, SLVector, SLShape, SLCamera, SLBody, SLClock, SimClock)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.data_manager import SnapshotManager

from pymunk import Vec2d
import pymunk

import os
import json
import time

def receive_data(sock):
    done = False
    all_data = ""
    while not done:
        data, server = sock.recvfrom(4096)
        data_parts = data.decode("utf-8").split("<<<")
        all_data += data_parts[1]
        header = data_parts[0].split(",")
        chunk_num = int(header[0])
        chunks = int(header[1])
        if chunk_num == chunks:
            done = True
    return all_data

def send_request(request_data , server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        data_st = json.dumps(request_data, cls=StateEncoder) + "\n"
        # Send data
        sent = sock.sendto(bytes(data_st,'utf-8'), 
            server_address)
        data = receive_data(sock)
    finally:
        sock.close()
    return json.loads(data, cls=StateDecoder)

SNAPSHOT_LOG_SIZE = 100

from multiprocessing import Queue
LATENCY_LOG_SIZE = 100
import math

from simpleland.common import build_interpolated_object
    
def interpolate_snapshots(snapshot_1, snapshot_2, lookup_time):
    
    if snapshot_1 is None:
        return snapshot_2
    if snapshot_2 is None:
        return snapshot_1
    time1 = snapshot_1['snapshot']['snapshot_time_ms']
    time2 = snapshot_2['snapshot']['snapshot_time_ms']
    new_snapshot = {}
    new_snapshot['info'] = {}
    new_snapshot['info']['message'] = snapshot_1['info']['message']
    new_snapshot['info']['client_id'] = snapshot_1['info']['client_id']
    new_snapshot['info']['player_id'] = snapshot_1['info']['player_id']
    new_snapshot['snapshot']={}
    new_snapshot['info']['snapshot_time_ms'] = lookup_time
    new_snapshot['snapshot']['player_manager'] = snapshot_1['snapshot']['player_manager']
    new_snapshot['snapshot']['object_manager'] = {}
    fraction = (lookup_time - time1)/(time2-time1)
    for k, obj_data_1 in snapshot_1['snapshot']['object_manager'].items():
            obj_data_2 = snapshot_2['snapshot']['object_manager'][k]
            obj_1 = SLObject.build_from_dict(obj_data_1)
            obj_2 = SLObject.build_from_dict(obj_data_2)
            new_obj = build_interpolated_object(obj_1, obj_2, fraction)
            new_snapshot['snapshot']['object_manager'][k] = new_obj.get_snapshot()
    return new_snapshot

class GameClient:
    # TODO, change to client + server connection

    def __init__(self, server_address = ('localhost', 10000)):
        self.server_address = server_address
        self.incomming_buffer:Queue= Queue()# event buffer
        self.outgoing_buffer:Queue = Queue()# state buffer
        self.running = True
        self.client_id = None
        self.ticks_per_second = 20
        self.latency_log = [None for i in range(LATENCY_LOG_SIZE)]
        self.last_latency_ms = None
        self.request_counter =0

        self.clock = SimClock()

    def add_latency(self,latency: float):
        self.latency_log[self.request_counter % LATENCY_LOG_SIZE] = latency
    
    def avg(self):
        vals = [i for i in self.latency_log if i is not None]
        return math.fsum(vals)/len(vals)

    def start_connection(self):
        print("Starting connection to server")

        while self.running:
            #print("tick")
            request_info = {
                'client_id' : "" if self.client_id is None else self.client_id,
                'last_latency_ms' : self.last_latency_ms
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


            # Log latency
            last_latency_ms = (time.time() * 1000) - start_time
            self.add_latency(last_latency_ms)

            response_info = response['info']

            # set clock
            # todo, check for drift and add latency
            if self.request_counter == 0:
                absolute_server_time = (time.time()*1000) - float(response_info['server_time_ms'])
                self.clock.set_time(absolute_server_time)
            
            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter +=1
            self.clock.tick(self.ticks_per_second)

        
class GameManager:

    def __init__(self, client: GameClient):
        self.game:SLGame = SLGame()
        self.game.start()
        self.snapshot_manager = SnapshotManager(SNAPSHOT_LOG_SIZE)
        self.client = client
        self.clock = self.client.clock
        self.render_delay_in_ms = 100
        self.frames_per_second = 60

    def load_response_data(self):
        done = False
        while (not done):
            if self.client.incomming_buffer.qsize() ==0:
                incomming_data = None
            else:
                incomming_data = self.client.incomming_buffer.get()
            if incomming_data is None:
                done = True
                break
            else:
                snapshot_time_ms = int(incomming_data['info']['snapshot_time_ms'])
                self.snapshot_manager.add_snapshot(snapshot_time_ms,incomming_data)


    def run(self, resolution):

        # Create Player
        os.environ['SDL_AUDIODRIVER'] = 'dsp'
        # os.environ["SDL_VIDEODRIVER"] = "dummy"

        # Create Renderer
        renderer = SLRenderer(resolution)
        renderer.on_init()

        # RL Agent will be different
        player:SLHumanPlayer = None
        step_counter = 0

        while self.game.game_state == "RUNNING":

            # Get Input From Players
            self.game.check_game_events()
            if player is not None:
                self.game.event_manager.add_events(player.pull_input_events())
            self.game.event_manager.add_events(self.game.physics_engine.pull_events())

            event_snapshot = self.game.event_manager.get_snapshot()
            if self.client.outgoing_buffer.qsize() < 3:
                self.client.outgoing_buffer.put(event_snapshot)
            self.game.event_manager.clear()

            # Get Game Snapshot
            self.load_response_data()

            snapshot_found = False
            while(not snapshot_found):
                lookup_snapshot_time_ms = self.clock.get_time() - self.render_delay_in_ms
                prev_snapshot, next_snapshot = self.snapshot_manager.get_snapshot_pair_by_id(lookup_snapshot_time_ms)
                server_data = interpolate_snapshots(prev_snapshot, next_snapshot,lookup_snapshot_time_ms)
                snapshot_found = True

            if server_data is not None:
                snapshot = server_data['snapshot']
                server_info = server_data['info']
                if snapshot is not None:
                    if 'object_manager' in snapshot:
                        self.game.object_manager.clear_objects()
                        self.game.object_manager.load_snapshot(snapshot['object_manager'])
                    if 'player_manager' in snapshot:
                        self.game.player_manager.load_snapshot(snapshot['player_manager'])

                if server_info['player_id'] != "":
                    player = self.game.player_manager.get_player(server_info['player_id'])

            # Render
            if player is not None:
                renderer.process_frame(
                    player.get_object_id(),
                    self.game.object_manager)
                renderer.render_frame()
            self.game.physics_engine.tick(self.frames_per_second)
            step_counter += 1


import threading

def main():
    game_client = GameClient()
    client_thread =threading.Thread(target=game_client.start_connection, args=())
    client_thread.daemon = True
    client_thread.start()

    game_manager = GameManager(client=game_client)


    game_manager.run(resolution=(640, 480))


if __name__ == "__main__":
    main()
