
import logging
from typing import Tuple

import numpy as np

from simpleland.common import (SLObject, SLVector, SLShape, SLCamera, SLBody, SimClock)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer

from pymunk import Vec2d
import pymunk
import socketserver, threading, time
from simpleland.utils import gen_id
import math
from simpleland.data_manager import SnapshotManager
import json
import math
import random

#https://gist.github.com/arthurafarias/7258a2b83433dfda013f1954aaecd50a

LATENCY_LOG_SIZE = 100
SNAPSHOT_LOG_SIZE = 100

class ClientInfo:

    def __init__(self):
        self.id = gen_id()
        self.last_snapshot_time_ms = None
        self.latency_history = [None for i in range(LATENCY_LOG_SIZE)]
        self.player_id = None
        self.conn_info = None
        self.request_counter = 0
    
    def add_latency(self,latency: float):
        self.latency_history[self.request_counter % LATENCY_LOG_SIZE] = latency
        self.request_counter +=1

    def avg(self):
        vals = [i for i in self.latency_history if i is not None]
        return math.fsum(vals)/len(vals)

    def get_id(self):
        return self.id

class GameServer:

    def __init__(self):
        self.game = SLGame()
        self.load_game_data()
        self.clock = SimClock()
        self.snapshot_manager = SnapshotManager(SNAPSHOT_LOG_SIZE)
        self.clients = {}
        self.steps_per_second = 20

    def get_game(self)->SLGame:
        return self.game

    def add_snapshot(self):
        snapshot={}
        snapshot_time_ms = math.ceil(self.clock.get_time())
        # print("Adding snapshot {}".format(snapshot_id))
        snapshot['object_manager'] = self.get_game().object_manager.get_snapshot()
        snapshot['player_manager'] = self.get_game().player_manager.get_snapshot()
        snapshot['snapshot_time_ms'] = snapshot_time_ms
        self.snapshot_manager.add_snapshot(snapshot_time_ms,snapshot)

    def load_game_data(self):
        print("Starting Game")

        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=20)

        # Create Hostile
        hostile_object = SLObject(SLBody(mass=50, moment=1))
        hostile_object.set_position(position=SLVector(6, 6))
        SLShapeFactory.attach_circle(hostile_object, 1)
        SLShapeFactory.attach_psquare(hostile_object,0.5)

        for i in range(10):
            mass = math.ceil(random.random()* 10)
            o = SLObject(SLBody(mass=mass, moment=1))
            radius = mass/5
            SLShapeFactory.attach_circle(o,radius)
            self.game.attach_objects([o])

        # Add objects to game
        self.game.attach_objects([hostile_object])
        self.game.attach_objects([wall])

        def collision_callback(arbiter:pymunk.Arbiter,space,data):
            for s in arbiter.shapes:
                s:SLShape = s
                o = self.game.object_manager.get_by_id(s.get_object_id())
                o.set_energy(o.get_energy() - 1)

        self.game.physics_engine.enable_collision_detection(collision_callback)
        self.game.start()

    def get_client(self, client_id):
        client = self.clients.get(client_id,None)
        if client is None:
            client = ClientInfo()
            self.clients[client.id] = client
        return client
    
    def get_player(self, client):
        if client.player_id is None:
            player = self.new_player()
            client.player_id = player.get_id()
        else:
            player = self.get_player_by_id(client.player_id)
        return player

    def new_player(self)->SLPlayer:
        # Create Player
        player_object = SLObject(SLBody(mass=8, moment=30), camera=SLCamera(distance=22))
        player_object.set_position(SLVector(10, 10))
        SLShapeFactory.attach_psquare(player_object, 1)

        player = SLPlayer(gen_id())
        player.attach_object(player_object)
        self.get_game().attach_objects([player_object])
        self.get_game().add_player(player)
        return player

    def get_player_by_id(self,player_id):
        return self.get_game().player_manager.get_player(player_id)

    def run(self):
        done = False
        while not done:
            #PULL EVENTS
            self.get_game().event_manager.add_events(
                self.get_game().player_manager.pull_events())
            self.get_game().event_manager.add_events(
                self.get_game().physics_engine.pull_events())
            self.get_game().check_game_events()

            # APPLY PHYSICS
            self.get_game().physics_engine.apply_events(
                self.get_game().event_manager, self.get_game().object_manager)
            self.get_game().physics_engine.update(self.get_game().object_manager,self.steps_per_second)
            self.get_game().physics_engine.tick(self.steps_per_second)
            self.add_snapshot()

class UDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        gameserver = self.server.gameserver
        # print("Connection made")

        # Process Request data
        request_st = self.request[0].strip()
        try:
            request_data = json.loads(request_st, cls=StateDecoder)
        except Exception as e:
            print(request_st)
            raise e

        request_info = request_data['info']

        client = gameserver.get_client(request_info['client_id'])
        player = gameserver.get_player(client)

        # Load events from client
        all_events_data = {}
        for event_dict in request_data['items']:
            all_events_data.update(event_dict)

        if len(all_events_data) > 0:
            gameserver.get_game().event_manager.load_snapshot(all_events_data)

        snapshot_time_ms, snapshot = gameserver.snapshot_manager.get_latest_snapshot()
        
        message = ""
        if client.last_snapshot_time_ms is not None and snapshot_time_ms == client.last_snapshot_time_ms:
            message = "NO_UPDATE"
            snapshot = None
        else:
            message = "UPDATE"

        response_data = {}
        response_data['info'] = {
            'server_time_ms': gameserver.clock.get_time(),
            'message': message,
            'client_id':client.get_id(),
            'player_id': player.get_id(),
            'snapshot_time_ms': snapshot_time_ms}
        response_data['snapshot'] = snapshot
        response_data_st = json.dumps(response_data, cls= StateEncoder)

        chunk_size = 2048
        chunks = math.ceil(len(response_data_st)/chunk_size)

        for i in range(chunks):
            header = "{},{}<<<".format(i+1,chunks)
            data_chunk = header + response_data_st[i*chunk_size:(i+1)*chunk_size]
            socket = self.request[1]
            current_thread = threading.current_thread()
            socket.sendto(bytes(data_chunk,'utf-8'), self.client_address)
        client.last_snapshot_time_ms = snapshot_time_ms
        # print("sent")

class GameUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    
    def __init__(self,conn,handler,gameserver):
        socketserver.UDPServer.__init__(self,conn,handler)
        self.gameserver = gameserver

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 10000

    gameserver = GameServer()

    server = GameUDPServer((HOST, PORT), UDPHandler, gameserver=gameserver)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True

    try:
        server_thread.start()
        print("Server started at {} port {}".format(HOST, PORT))

        gameserver.run()
        # while True: time.sleep(100)
    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        server.server_close()
        exit()