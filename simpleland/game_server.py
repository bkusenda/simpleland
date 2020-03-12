
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
from simpleland.event_manager import SLPeriodicEvent
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.object_manager import SLObjectManager
from simpleland.physics_engine import SLPhysicsEngine
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.utils import gen_id
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

class GameServer:

    def __init__(self):
        self.game = SLGame()
        self.load_game_data()
        self.clients = {}
        self.steps_per_second = 60
        self.snapshots = TimeLoggingContainer(100)
        self.snapshot_counter = 0
        self.snapshot_timestamp = 0

    def get_game(self)->SLGame:
        return self.game

    def load_game_data(self):
        print("Starting Game")

        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=50)
        wall.set_data_value("type","static")


        # Create Hostile
        # hostile_object = SLObject(SLBody(mass=50, moment=1))
        # hostile_object.set_position(position=SLVector(6, 6))
        # hostile_object.set_data_value("type","hostile", create_time)

        # SLShapeFactory.attach_circle(hostile_object, 1)
        # SLShapeFactory.attach_psquare(hostile_object,0.5)

        # # Add objects to game
        # self.game.attach_objects([hostile_object])
        self.game.add_object(wall)


        for i in range(20):
            o = SLObject(SLBody(mass=5, moment=1))
            o.set_position(position=SLVector(
                random.random() * 100 - 50,
                random.random()  * 100 - 50))
            #radius = max(mass/8,0.5)
            o.set_data_value("energy",30)
            o.set_data_value("type","astroid")
            o.set_data_value("image", "astroid2")
            o.set_last_change(self.game.clock.get_time())
            o.get_body().angle = random.random() * 360
            SLShapeFactory.attach_circle(o,0.5)
            #SLShapeFactory.attach_psquare(o,0.4)
            self.game.add_object(o)

        for i in range(100):
            o = SLObject(SLBody(body_type=pymunk.Body.STATIC))
            o.set_position(position=SLVector(
                random.random() * 80 - 40,
                random.random()  * 80 - 40))
            o.set_data_value("energy",10)
            o.set_data_value("type","food")
            o.set_data_value("image", "energy1")

            o.set_last_change(self.game.clock.get_time())
            SLShapeFactory.attach_circle(o,0.9)
            self.game.add_object(o)

        def new_food_func(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
            for i in range(0,random.randint(0,1)):
                o = SLObject(SLBody(body_type=pymunk.Body.KINEMATIC))
                o.set_position(position=SLVector(
                    random.random()  * 40 - 20,
                    random.random()  * 40 - 20))
                o.set_data_value("energy",10)
                o.set_data_value("type","food")
                o.set_data_value("image", "energy1")
                o.set_last_change(self.game.clock.get_time())
            
                SLShapeFactory.attach_circle(o,0.5)
                self.game.add_object(o)
            return [], False
        new_food_event = SLPeriodicEvent(new_food_func,execution_interval=2000)
        self.game.event_manager.add_event(new_food_event)

        # TODO, move to standard event callback
        def collision_callback(arbiter:pymunk.Arbiter,space,data):
            food_objs = []
            player_objs = []
            for s in arbiter.shapes:
                s:SLShape = s
                t, o = self.game.object_manager.get_latest_by_id(s.get_object_id())
                if o is None:
                    return
                if o.get_data_value("type") == "food":
                    food_objs.append(o)
                elif o.get_data_value("type") == "player":
                    player_objs.append(o)
            # print(" food objs {}".format(len(food_objs)))
            # print(" player_objs {}".format(len(player_objs)))

            if len(food_objs) ==1 and len(player_objs) ==1:
                food_energy = food_objs[0].get_data_value('energy')
                player_energy = player_objs[0].get_data_value('energy')
                player_objs[0].set_data_value("energy",
                    player_energy + food_energy)
                player_objs[0].set_last_change(self.game.clock.get_time())
                self.game.remove_object(food_objs[0])
                return False
            else:
                return True
                #self.game.object_manager.remove_by_id(food_objs[0].get_id())
        self.game.physics_engine.enable_collision_detection(collision_callback)
        print("Loading Game Complete")

    def get_client(self, client_id)->ClientInfo:
        client = self.clients.get(client_id,None)
        if client is None:
            client = ClientInfo(client_id)
            self.clients[client.id] = client
        return client
    
    def get_player(self, client):
        if client.player_id is None:
            player = self.new_player()
            client.player_id = player.get_id()
        else:
            player = self.get_player_by_id(client.player_id)
        return player

    # New Round callback
    
    # Make callback
    def new_player(self)->SLPlayer:
        # Create Player
        create_time = self.game.clock.get_time()
        player_object = SLObject(SLBody(mass=8, moment=30), camera=SLCamera(distance=22))
        player_object.set_position(SLVector(10, 10))
        
        player_object.set_data_value("type","player")
        player_object.set_data_value("energy", 100)
        player_object.set_data_value("image", "1")

        # SLShapeFactory.attach_psquare(player_object, 1)
        SLShapeFactory.attach_circle(player_object, 0.8)
        player = SLPlayer(gen_id())
        player.attach_object(player_object)
        self.get_game().add_object(player_object)
        self.get_game().add_player(player)
        print("PLayer Obj {}".format(player_object.get_id()))

        def event_callback(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
            t, obj = om.get_latest_by_id(data['obj_id'])
            if obj is None:
                return [], True
            new_energy = obj.get_data_value("energy") - 2
            if new_energy <= 0:
                om.remove_by_id(obj.get_id())
                return [], True
            obj.set_data_value('energy',new_energy)
            obj.set_last_change(self.game.clock.get_time())
            print(new_energy)
            return [], False

        decay_event = SLPeriodicEvent(
            event_callback,
            execution_interval=2000,
            data={'obj_id':player_object.get_id()})

        self.get_game().event_manager.add_event(decay_event)
        return player

    def get_player_by_id(self,player_id):
        return self.get_game().player_manager.get_player(player_id)

    def run(self):
        done = False
        while not done:
            self.game.process_events()
            self.game.apply_physics()
            snapshot_timestamp, snapshot = self.game.create_snapshot(self.game.clock.get_time())
            self.snapshots.add(snapshot_timestamp,snapshot)
            self.snapshot_timestamp = snapshot_timestamp
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
        all_events_data = {}
        for event_dict in request_data['items']:
            all_events_data.update(event_dict)

        if len(all_events_data) > 0:
            gameserver.get_game().event_manager.load_snapshot(all_events_data)
        
        message = "UPDATE"
        # Diabled snapshot sharing, TODO: support snapshot update + replay multiple napshots to catchup
        # snapshot_timestamp, snapshot = gameserver.snapshots.get_prev_entry(client.last_snapshot_time_ms)
        # if snapshot is None:
        #     print("Building new snapshot")

        if len(client.unconfirmed_messages) <10:
            snapshot_timestamp, snapshot = gameserver.game.create_snapshot(client.last_snapshot_time_ms)
        else:
            print("To many unconfirmed, packets full update required") #TODO add replay
            snapshot_timestamp, snapshot = gameserver.game.create_snapshot(0)
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

        chunk_size = 4000
        chunks = math.ceil(len(response_data_st)/chunk_size)
        # client.
        # print(chunks)
        socket = self.request[1]
        # time.sleep(random.random()/1000 * 20)

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
        # print("sent")

class GameUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    
    def __init__(self,conn,handler,gameserver):
        socketserver.UDPServer.__init__(self,conn,handler)
        self.gameserver = gameserver

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=10001, help="port")
    args = parser.parse_args()

    HOST, PORT = "0.0.0.0", args.port

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
