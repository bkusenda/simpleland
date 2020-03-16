
import argparse
import json
import logging
import math
import random
import socketserver
import threading
import time
from multiprocessing import Queue
from typing import Any, Dict, Tuple

import lz4.frame
import numpy as np
import pymunk
from pymunk import Vec2d

from simpleland.common import (SimClock, SLBody, SLCamera,
                               SLCircle, SLClock, SLLine, SLObject, SLPolygon,
                               SLShape, SLSpace, SLVector, TimeLoggingContainer)
from simpleland.event_manager import SLPeriodicEvent, SLSoundEvent
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.object_manager import SLObjectManager
from simpleland.physics_engine import SLPhysicsEngine
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.utils import gen_id
from simpleland.content_manager import ContentManager
import struct

LATENCY_LOG_SIZE = 100
SNAPSHOT_LOG_SIZE = 10 #DO I NEED THIS AT ALL?  Perhapse for replays it will be useful

class ClientInfo:

    def __init__(self, client_id):
        self.id = client_id
        self.last_snapshot_time_ms = 0
        self.latency_history = [None for i in range(LATENCY_LOG_SIZE)]
        self.player_id = None
        self.conn_info = None
        self.request_counter = 0
        self.unconfirmed_messages = set()
    
    def add_latency(self,latency: float):
        self.latency_history[self.request_counter % LATENCY_LOG_SIZE] = latency
        self.request_counter +=1

    def avg(self):
        vals = [i for i in self.latency_history if i is not None]
        return math.fsum(vals)/len(vals)

    def get_id(self):
        return self.id
from simpleland.config import ServerConfig

class GameServer:

    def __init__(self,
                config: ServerConfig, 
                content_manager:ContentManager, 
                game:SLGame):

        self.config = config
        self.game = game
        self.content_manager = content_manager
        self.clients = {}
        self.steps_per_second = config.steps_per_second


    def get_client(self, client_id)->ClientInfo:
        client = self.clients.get(client_id,None)
        if client is None:
            client = ClientInfo(client_id)
            self.clients[client.id] = client
        return client
    
    def get_player(self, client):
        if client.player_id is None:
            player = self.content_manager.new_player(self.game)
            client.player_id = player.get_id()
        else:
            player = self.get_player_by_id(client.player_id)
        return player

    def get_player_by_id(self,player_id):
        return self.game.player_manager.get_player(player_id)

    def run(self):
        done = False
        while not done:
            self.game.run_pre_event_processing()
            self.game.run_event_processing()
            self.game.run_pre_physics_processing()
            self.game.run_physics_processing()
            self.game.tick()

class UDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        gameserver:GameServer = self.server.gameserver

        # Process Request data
        request_st = lz4.frame.decompress(self.request[0]).decode('utf-8').strip()
        try:
            request_data = json.loads(request_st, cls=StateDecoder)
        except Exception as e:
            print(request_st)
            raise e

        request_info = request_data['info']

        request_message = request_info['message']
        client = gameserver.get_client(request_info['client_id'])
        player = gameserver.get_player(client)

        snapshots_received = request_info['snapshots_received']
        
        # simulate missing parts
        skip_remove =  False#random.random() < 0.01

        for t in snapshots_received:
            if t in client.unconfirmed_messages:
                if skip_remove:
                    print("Skipping remove confirmation")
                    continue
                else:
                    client.unconfirmed_messages.remove(t)

        # Load events from client
        all_events_data = []
        for event_dict in request_data['items']:
            all_events_data.extend(event_dict)

        if len(all_events_data) > 0:
            gameserver.game.event_manager.load_snapshot(all_events_data)
        
        message = "UPDATE"

        if len(client.unconfirmed_messages) < gameserver.config.max_unconfirmed_messages_before_new_snapshot:
            snapshot_timestamp, snapshot = gameserver.game.create_snapshot(client.last_snapshot_time_ms)
        else:
            print("To many unconfirmed, packets full update required") #TODO add replay
            snapshot_timestamp, snapshot = gameserver.game.create_snapshot_for_client(0)
            client.unconfirmed_messages.clear()
        client.unconfirmed_messages.add(snapshot_timestamp)
        response_data = {}
        response_data['info'] = {
            'server_time_ms': gameserver.game.clock.get_exact_time(),
            'message': message,
            'client_id':client.get_id(),
            'player_id': player.get_id(),
            'snapshot_timestamp':snapshot_timestamp} # TODO: change to update_timestamp
        response_data['snapshot'] = snapshot

        response_data_st = json.dumps(response_data, cls= StateEncoder)
        response_data_st = bytes(response_data_st,'utf-8')
        response_data_st = lz4.frame.compress(response_data_st)

        chunk_size = gameserver.config.outgoing_chunk_size
        chunks = math.ceil(len(response_data_st)/chunk_size)
        socket = self.request[1]
        for i in range(chunks+1):
            header = struct.pack('ll',i+1,chunks)
            data_chunk = header + response_data_st[i*chunk_size:(i+1)*chunk_size]
            current_thread = threading.current_thread()
            # Simulate packet loss
            # if random.random() < 0.01:
            #     print("random skip chunk")
            #     continue
            socket.sendto(data_chunk, self.client_address)
        
        client.last_snapshot_time_ms = snapshot_timestamp

class GameUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    
    def __init__(self,conn,handler,gameserver):
        socketserver.UDPServer.__init__(self,conn,handler)
        self.gameserver = gameserver
from simpleland.config import ConfigManager

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=10001, help="port")
    args = parser.parse_args()

    HOST, PORT = "0.0.0.0", args.port

    config_manager = ConfigManager()
    #TODO: load from file

    game = SLGame(
            physics_config = config_manager.physics_config, 
            config = config_manager.game_config)

    content_manager = ContentManager(
            config= config_manager.content_config)

    content_manager.load(game)

    gameserver = GameServer(
            config = config_manager.server_config,
            content_manager= content_manager, 
            game = game)

    server = GameUDPServer(
            (HOST, PORT), UDPHandler, 
            gameserver=gameserver)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True

    try:
        server_thread.start()
        print("Server started at {} port {}".format(HOST, PORT))
        gameserver.run()

    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        server.server_close()
        exit()
