
import argparse
import json
import logging
import math
import random
import socketserver
import struct
import threading
import time
from multiprocessing import Queue
from typing import Any, Dict, Tuple

import lz4.frame
import numpy as np
import pymunk
from pymunk import Vec2d

from simpleland.common import (SimClock, SLBody, SLCamera, SLCircle, SLClock,
                               SLLine, SLObject, SLPolygon, SLShape, SLSpace,
                               SLVector, TimeLoggingContainer)
from simpleland.event_manager import SLPeriodicEvent, SLSoundEvent, SLDelayedEvent
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.object_manager import SLObjectManager
from simpleland.physics_engine import SLPhysicsEngine
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.utils import gen_id
from simpleland.config import PhysicsConfig,ServerConfig,RendererConfig,ClientConfig
import pygame

class ContentManager:

    def __init__(self,config):
        self.config = config

    def load(self,game:SLGame):
        print("Starting Game")

        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=50)
        wall.set_data_value("type","static")
        game.add_object(wall)

        # Create some Astroids
        for i in range(20):
            o = SLObject(SLBody(mass=5, moment=1))
            o.set_position(position=SLVector(
                random.random() * 100 - 50,
                random.random()  * 100 - 50))
            o.set_data_value("energy",30)
            o.set_data_value("type","astroid")
            o.set_data_value("image", "astroid2")
            o.set_last_change(game.clock.get_time())
            o.get_body().angle = random.random() * 360
            SLShapeFactory.attach_circle(o,1)
            game.add_object(o)

        for i in range(3):
            o = SLObject(SLBody(body_type=pymunk.Body.STATIC))
            o.set_position(position=SLVector(
                random.random() * 80 - 40,
                random.random()  * 80 - 40))
            o.set_data_value("energy",10)
            o.set_data_value("type","food")
            o.set_data_value("image", "energy1")

            o.set_last_change(game.clock.get_time())
            SLShapeFactory.attach_circle(o,1)
            game.add_object(o)

        def new_food_event_callback(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
            for i in range(0,random.randint(0,1)):
                o = SLObject(SLBody(body_type=pymunk.Body.KINEMATIC))
                o.set_position(position=SLVector(
                    random.random()  * 40 - 20,
                    random.random()  * 40 - 20))
                o.set_data_value("energy",10)
                o.set_data_value("type","food")
                o.set_data_value("image", "energy1")
                o.set_last_change(game.clock.get_time())
            
                SLShapeFactory.attach_circle(o,1)
                game.add_object(o)
            return [], False
        new_food_event = SLPeriodicEvent(new_food_event_callback,execution_interval=2000)
        game.event_manager.add_event(new_food_event)

        # TODO, move to standard event callback
        def collision_callback(arbiter:pymunk.Arbiter,space,data):
            food_objs = []
            player_objs = []
            for s in arbiter.shapes:
                s:SLShape = s
                t, o = game.object_manager.get_latest_by_id(s.get_object_id())
                if o is None:
                    return
                if o.get_data_value("type") == "food":
                    food_objs.append(o)
                elif o.get_data_value("type") == "player":
                    player_objs.append(o)

            if len(food_objs) ==1 and len(player_objs) ==1:
                food_energy = food_objs[0].get_data_value('energy')
                player_energy = player_objs[0].get_data_value('energy')
                player_objs[0].set_data_value("energy",
                    player_energy + food_energy)
                player_objs[0].set_last_change(game.clock.get_time())
                game.remove_object(food_objs[0])
                sound_event = SLSoundEvent(
                    creation_time=game.clock.get_time(), 
                    sound_id="bleep2")
                game.event_manager.add_event(sound_event)
                
                return False
            else:
                return True
                #self.game.object_manager.remove_by_id(food_objs[0].get_id())
        game.physics_engine.set_collision_callback(collision_callback)

        def pre_physics_callback(game:SLGame):
            new_events = []
            for k,p in game.player_manager.players_map.items():
                # print(p.get_object_id())
                if p.get_object_id() is None:
                    continue
                t, o = game.object_manager.get_latest_by_id(p.get_object_id())
                if o is None:
                    continue
                if o.is_deleted == False and o.get_data_value("energy") <= 0:
                    print("Player is dead")
                    lives_used = p.get_data_value("lives_used", 0)
                    p.set_data_value("lives_used",lives_used+1)
                    game.remove_object(o)
                    # Delete and create event

                    def event_callback(event: SLDelayedEvent ,data:Dict[str,Any],om:SLObjectManager):
                        print("Here")
                        self.new_player(game,player_id=p.get_id())
                        return []

                    new_ship_event = SLDelayedEvent(
                        func = event_callback,
                        execution_time=game.clock.get_time() + 2000,
                        data={'player_id':p.get_id()})

                    new_events.append(new_ship_event)
                                # Response
            return new_events
        game.set_pre_physics_callback(pre_physics_callback)

        print("Loading Game Complete")

    # Make callback
    def new_player(self, game:SLGame, player_id=None)->SLPlayer:
        # Create Player
        if player_id is None:
            player_id = gen_id()
        player = game.player_manager.get_player(player_id)
        
        if player is None:
            player = SLPlayer(player_id)
        print("playerData: {}".format(player.data))

        create_time = game.clock.get_time()
        player_object = SLObject(SLBody(mass=8, moment=30), 
            camera=SLCamera(distance=40))
        player_object.set_position(position=SLVector(
                random.random() * 80 - 40,
                random.random()  * 80 - 40))
        
        player_object.set_data_value("type","player")
        player_object.set_data_value("energy", 100)
        player_object.set_data_value("image", "1")
        player_object.set_data_value("player_id", player.get_id())

        # SLShapeFactory.attach_psquare(player_object, 1)
        SLShapeFactory.attach_circle(player_object, 1)

        player.attach_object(player_object)
        game.add_object(player_object)
        game.add_player(player)
        print("PLayer Obj {}".format(player_object.get_id()))

        def event_callback(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
            t, obj = om.get_latest_by_id(data['obj_id'])
            if obj is None or obj.is_deleted:
                return [], True
            new_energy = max(obj.get_data_value("energy") -10,0)
            #     # om.remove_by_id(obj.get_id())
            #     return [], False
            print(new_energy)
            obj.set_data_value('energy',new_energy)
            obj.set_last_change(game.clock.get_time())
            return [], False

        decay_event = SLPeriodicEvent(
            event_callback,
            execution_interval=2000,
            data={'obj_id':player_object.get_id()})

        game.event_manager.add_event(decay_event)
        return player

    def post_process_frame(self,render_time, game:SLGame, player, renderer:SLRenderer):
        if player is None:
            print("Player Dead")
        else:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used",0)))

            obj = game.object_manager.get_by_id(player.get_object_id(),render_time)
            if obj is not None:
                lines.append("Current Energy: {}".format(obj.get_data_value("energy",0)))
        
            renderer.render_to_console(lines,x=5,y=5)

            if obj is None:
                renderer.render_to_console(['You Died'],x=50,y=50,fsize=50)
