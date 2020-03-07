
import logging
from typing import Tuple, Dict, Any

import numpy as np

from simpleland.common import (PhysicsConfig, SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLShape, SLSpace, SLVector, SimClock, SLCamera)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.event_manager import SLPeriodicEvent
from simpleland.object_manager import SLObjectManager

from pymunk import Vec2d
import pymunk
import socketserver, threading, time
from simpleland.utils import gen_id
import math
from simpleland.data_manager import SnapshotManager
import json
import math
import random
from multiprocessing import Queue

LATENCY_LOG_SIZE = 100
SNAPSHOT_LOG_SIZE = 10 #DO I NEED THIS AT ALL?  Perhapse for replays it will be useful

# TODO: logic to confirm receiving updates and/or periodic full update?

def snapshot_filter(snapshot, last_update, force_update_all=False):
    # if True:
    #     return snapshot
    if force_update_all:
        return snapshot
    update_snapshot = {}

    update_snapshot['snapshot_time_ms'] = snapshot['snapshot_time_ms']
    update_snapshot['player_manager'] = snapshot['player_manager']
    update_snapshot['object_manager'] = {}
    for k, v in snapshot['object_manager'].items():
        obj_last_change = v['data']['last_change']
        # if :
        #     continue
        if  (obj_last_change is None) or ((last_update-100) < obj_last_change):
            update_snapshot['object_manager'][k] =v
            print("\t--Updated  ,last_update: {}, obj_last_change: {}".format(last_update,obj_last_change))
        else:
            print("\t--No Update,last_update: {}, obj_last_change: {}".format(last_update,obj_last_change))

            #    if  obj_last_change is None or last_update is None or last_update < obj_last_change:
            # update_snapshot['object_manager'][k] =v
            # print("Updated,last_update: {}, obj_last_change: {}".format(last_update,obj_last_change))
       
        # else:
        #     print("last_update: {}, obj_last_change: {}".format(last_update,obj_last_change))
    return update_snapshot



class ClientInfo:

    def __init__(self):
        self.id = gen_id()
        self.last_snapshot_time_ms = 0
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
        self.snapshot_manager = SnapshotManager(SNAPSHOT_LOG_SIZE)
        self.clients = {}
        self.steps_per_second = 60

    def get_game(self)->SLGame:
        return self.game

    def add_snapshot(self):
        snapshot={}
        snapshot_time_ms = math.ceil(self.game.clock.get_time())

        snapshot['object_manager'] = self.get_game().object_manager.get_snapshot()
        snapshot['player_manager'] = self.get_game().player_manager.get_snapshot()
        snapshot['snapshot_time_ms'] = snapshot_time_ms
        self.snapshot_manager.add_snapshot(snapshot_time_ms,snapshot)

    def load_game_data(self):
        print("Starting Game")

        create_time = self.game.clock.get_time()
        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=20)
        wall.set_data_value("type","static",create_time)


        # Create Hostile
        # hostile_object = SLObject(SLBody(mass=50, moment=1))
        # hostile_object.set_position(position=SLVector(6, 6))
        # hostile_object.set_data_value("type","hostile", create_time)

        # SLShapeFactory.attach_circle(hostile_object, 1)
        # SLShapeFactory.attach_psquare(hostile_object,0.5)

        # # Add objects to game
        # self.game.attach_objects([hostile_object])
        self.game.attach_objects([wall])

        # for i in range(10):
        #     mass = math.ceil(random.random()* 10)
        #     o = SLObject(SLBody(mass=mass, moment=1))
        #     o.set_position(position=SLVector(
        #         random.random() * 40 - 20,
        #         random.random()  * 40 - 20))
        #     radius = max(mass/8,0.5)
        #     o.set_data_value("energy",radius, create_time)
        #     o.set_data_value("type","food",create_time)

        #     SLShapeFactory.attach_circle(o,radius)
        #     self.game.attach_objects([o])





        # def new_food_func(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
        #     for i in range(0,random.randint(0,1)):
        #         mass = math.ceil(random.random()* 10)
        #         o = SLObject(SLBody(mass=mass, moment=1))
        #         o.set_position(position=SLVector(
        #             random.random()  * 40 - 20,
        #             random.random()  * 40 - 20))
        #         radius = max(mass/8,0.5)
        #         o.set_data_value("energy",radius)
        #         o.set_data_value("type","food")
        #         SLShapeFactory.attach_circle(o,radius)
        #         self.game.attach_objects([o])
        #     return [], False
        # new_food_event = SLPeriodicEvent(new_food_func,execution_interval=2000)
        # self.game.event_manager.add_event(new_food_event)

        # TODO, move to standard event callback
        def collision_callback(arbiter:pymunk.Arbiter,space,data):
            food_objs = []
            player_objs = []
            for s in arbiter.shapes:
                s:SLShape = s
                o = self.game.object_manager.get_by_id(s.get_object_id())
                if o is None:
                    return
                if o.get_data_value("type") == "food":
                    food_objs.append(o)
                elif o.get_data_value("type") == "player":
                    player_objs.append(o)
            print(" food objs {}".format(len(food_objs)))
            print(" player_objs {}".format(len(player_objs)))

            if len(food_objs) ==1 and len(player_objs) ==1:
                food_energy = food_objs[0].get_data_value('energy')
                player_energy = player_objs[0].get_data_value('energy')
                player_objs[0].set_data_value("energy",
                    player_energy + food_energy, 
                    self.game.clock.get_time())
                self.game.remove_object(food_objs[0])
                #self.game.object_manager.remove_by_id(food_objs[0].get_id())


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
        create_time = self.game.clock.get_time()
        player_object = SLObject(SLBody(mass=8, moment=30), camera=SLCamera(distance=22))
        player_object.set_position(SLVector(10, 10))
        
        player_object.set_data_value("type","player",create_time)
        player_object.set_data_value("energy", 100,create_time)

        SLShapeFactory.attach_psquare(player_object, 1)

        player = SLPlayer(gen_id())
        player.attach_object(player_object)
        self.get_game().attach_objects([player_object])
        self.get_game().add_player(player)

        def event_callback(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
            obj = om.get_by_id(data['obj_id'])
            if obj is None:
                return [], True
            new_energy = obj.get_data_value("energy") - 2
            if new_energy == 0:
                om.remove_by_id(obj.get_id())
                return [], True
            obj.set_data_value('energy',new_energy,self.game.clock.get_time())
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
            #PULL EVENTS FOR LOCAL PLAYERS
            self.get_game().event_manager.add_events(
                self.get_game().player_manager.pull_events())

            self.get_game().process_all_events(self.game.clock.get_time())

            self.get_game().physics_engine.update(self.get_game().object_manager,self.steps_per_second)
            self.get_game().clock.tick(self.steps_per_second)
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

        request_message = request_info['message']
        client = gameserver.get_client(request_info['client_id'])
        player = gameserver.get_player(client)

        # Load events from client
        all_events_data = {}
        for event_dict in request_data['items']:
            all_events_data.update(event_dict)

        if len(all_events_data) > 0:
            gameserver.get_game().event_manager.load_snapshot(all_events_data)
        print("New Request-----------------------")
        snapshot_time_ms, snapshot = gameserver.snapshot_manager.get_latest_snapshot()
        
        message = ""
        if snapshot_time_ms == client.last_snapshot_time_ms:
            message = "NO_UPDATE"
            snapshot = None
        else:
            if client.last_snapshot_time_ms == 0:
                message = "FULL_UPDATE"
            else:
                message = "PARTIAL_UPDATE"

            snapshot = snapshot_filter(snapshot, 
                client.last_snapshot_time_ms,
                force_update_all=False)
        print("\tClient SnapShot Time: {}".format(client.last_snapshot_time_ms))
        print("\tLookup SnapShot Time: {}".format(snapshot_time_ms))
        response_data = {}
        response_data['info'] = {
            'server_time_ms': gameserver.game.clock.get_time(),
            'message': message,
            'client_id':client.get_id(),
            'player_id': player.get_id(),
            'snapshot_time_ms': snapshot_time_ms}
        response_data['snapshot'] = snapshot
        response_data_st = json.dumps(response_data, cls= StateEncoder)

        chunk_size = 4000
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