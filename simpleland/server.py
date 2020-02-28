
import logging
from typing import Tuple

import numpy as np

from simpleland.common import (SLObject, SLVector, SLShape, SLCamera, SLBody)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer

from pymunk import Vec2d
import pymunk
import socketserver, threading, time
from simpleland.utils import gen_id


#https://gist.github.com/arthurafarias/7258a2b83433dfda013f1954aaecd50a


class GameServer:

    def __init__(self):
        self.game:SLGame = None
        self.name = "Hi im a game server"
        self.start_new_game()

    def start_new_game(self):
        print("Starting Game")

        # Create Game
        game = SLGame()

        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=20)

        # Create Hostile
        hostile_object = SLObject(SLBody(mass=50, moment=1))
        hostile_object.set_position(position=SLVector(6, 6))
        SLShapeFactory.attach_circle(hostile_object, 1)
        SLShapeFactory.attach_psquare(hostile_object,0.5)

        # Add objects to game
        game.attach_objects([hostile_object])
        game.attach_objects([wall])

        def collision_callback(arbiter:pymunk.Arbiter,space,data):
            for s in arbiter.shapes:
                s:SLShape = s
                o = game.object_manager.get_by_id(s.get_object_id())
                o.set_energy(o.get_energy() - 1)

        game.physics_engine.enable_collision_detection(collision_callback)
        game.start()

        self.game = game

    def get_game(self)->SLGame:
        if self.game is None:
            self.start_new_game()
        return self.game
    
    def new_player(self):
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

import json
import math
class UDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        gameserver = self.server.gameserver

        # Process Request data
        request_st = self.request[0].strip()
        try:
            request_data = json.loads(request_st, cls=StateDecoder)
        except Exception as e:
            print(request_st)
            raise e

        if request_data['player_id'] == "":
            player = gameserver.new_player()
        else:
            player = gameserver.get_player_by_id(request_data['player_id'])

        gameserver.get_game().event_manager.load_snapshot(request_data['event_manager'])
        # print(gameserver.get_game().event_manager.get_events())
        gameserver.get_game().step()

        response_data = {}
        response_data['player'] = player.get_snapshot()
        response_data['game_snapshot'] = gameserver.get_game().get_game_snapshot()
        response_data_st = json.dumps(response_data, cls= StateEncoder)
        chunk_size = 3000
        chunks = math.ceil(len(response_data_st)/chunk_size)

        for i in range(chunks):
            header = "{},{}<<<".format(i+1,chunks)
            data_chunk = header + response_data_st[i*chunk_size:(i+1)*chunk_size]
            socket = self.request[1]
            current_thread = threading.current_thread()
            socket.sendto(data_chunk.encode('utf-8'), self.client_address)

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
        while True: time.sleep(100)
    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        server.server_close()
        exit()