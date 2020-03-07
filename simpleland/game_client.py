
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

SNAPSHOT_LOG_SIZE = 30

from multiprocessing import Queue
LATENCY_LOG_SIZE = 100
import math

from simpleland.common import build_interpolated_object
    
def interpolate_snapshots(snapshot_1, snapshot_2, lookup_time):
    
    if snapshot_1 is None:
        return snapshot_2
    if snapshot_2 is None:
        return snapshot_1
    if snapshot_1 is None and snapshot_2 is None:
        return None
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
    om1 = snapshot_1['snapshot']['object_manager']
    om2 = snapshot_2['snapshot']['object_manager']
    for k, obj_data_1 in om1.items():
            if k not in om2:
                continue
            obj_data_2 = om2[k]
            obj_1 = SLObject.build_from_dict(obj_data_1)
            obj_2 = SLObject.build_from_dict(obj_data_2)
            new_obj = build_interpolated_object(obj_1, obj_2, fraction)
            new_snapshot['snapshot']['object_manager'][k] = new_obj.get_snapshot()
    return new_snapshot

class ClientConnector:
    # TODO, change to client + server connection

    def __init__(self, server_address = ('localhost', 10000)):
        self.server_address = server_address
        self.incomming_buffer:Queue= Queue()# event buffer
        self.outgoing_buffer:Queue = Queue()# state buffer
        self.running = True
        self.client_id = None

        self.latency_log = [None for i in range(LATENCY_LOG_SIZE)]
        self.last_latency_ms = None
        self.request_counter =0
        self.absolute_server_time = None

        self.clock = SimClock() # clock for controlling network tick speed
        self.ticks_per_second = 40

    def add_latency(self,latency: float):
        self.latency_log[self.request_counter % LATENCY_LOG_SIZE] = latency
    
    def avg(self):
        vals = [i for i in self.latency_log if i is not None]
        return math.fsum(vals)/len(vals)

    def start_connection(self):
        print("Starting connection to server")

        while self.running:
            request_info = {
                'client_id' : "" if self.client_id is None else self.client_id,
                'last_latency_ms' : self.last_latency_ms,
                'message':"FULL_UPDATE"
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
            if self.request_counter == 0 or self.absolute_server_time is None:
                absolute_server_time = (time.time()*1000) - float(response_info['server_time_ms'])
                self.absolute_server_time =  absolute_server_time
            
            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter +=1
            self.clock.tick(self.ticks_per_second)
        
class GameClient:

    def __init__(self, connector: ClientConnector):
        self.game:SLGame = SLGame()
        self.game.start()
        self.snapshot_manager = SnapshotManager(SNAPSHOT_LOG_SIZE)
        self.connector = connector
        self.render_delay_in_ms = 200
        self.frames_per_second = 60

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

            # Process Any Local Events
            self.game.process_all_events(self.game.clock.get_time())

            if self.connector.absolute_server_time is not None:
                self.game.clock.set_time(self.connector.absolute_server_time)

            # Get Input Events and put in output buffer
            if player is not None:
                self.game.event_manager.add_events(player.pull_input_events())

            event_snapshot = self.game.event_manager.get_snapshot()
            if self.connector.outgoing_buffer.qsize() < 3:
                self.connector.outgoing_buffer.put(event_snapshot)

            # Clear Events after sending to Server 
            # TODO: add support for selective removal of events. eg keep local events  like quite request
            self.game.event_manager.clear()

            # Get Game Snapshot
            self.load_response_data()


            # Load Snapshot
            lookup_snapshot_time_ms = self.game.clock.get_time() - self.render_delay_in_ms
            prev_snapshot, next_snapshot = self.snapshot_manager.get_snapshot_pair_by_id(lookup_snapshot_time_ms)
            server_data = interpolate_snapshots(prev_snapshot, next_snapshot,lookup_snapshot_time_ms)
            if server_data is None:
                max_snapshot_id, server_data = self.snapshot_manager.get_latest_snapshot()
                print("expected {} received {}".format(lookup_snapshot_time_ms,max_snapshot_id))
            # If Snapshot exists
            if server_data is not None:
                # print("newSnap")
                snapshot = server_data['snapshot']
                server_info = server_data['info']
                self.game.update_game_state(snapshot)
                if server_info['player_id'] != "":
                    player = self.game.player_manager.get_player(server_info['player_id'])

            # Render
            if player is not None:
                renderer.process_frame(
                    player.get_object_id(),
                    self.game.object_manager)
                renderer.render_frame()
            self.game.clock.tick(self.frames_per_second)
            step_counter += 1


import threading

def main():
    connector = ClientConnector()
    connector_thread =threading.Thread(target=connector.start_connection, args=())
    connector_thread.daemon = True
    connector_thread.start()

    game_manager = GameClient(connector=connector)
    game_manager.run(resolution=(640, 480))


if __name__ == "__main__":
    main()
