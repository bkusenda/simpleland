
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
from simpleland.event_manager import SLPeriodicEvent, SLSoundEvent
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.object_manager import SLObjectManager
from simpleland.physics_engine import SLPhysicsEngine
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.utils import gen_id
import pygame

class ContentManager:

    def __init__(self,game:SLGame):
        self.game = game
        self.image_assets={}
        self.sound_assets={}


    def load_level(self, level_id =1):
        print("Starting Game")

        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=50)
        wall.set_data_value("type","static")

        self.game.add_object(wall)


        for i in range(20):
            o = SLObject(SLBody(mass=5, moment=1))
            o.set_position(position=SLVector(
                random.random() * 100 - 50,
                random.random()  * 100 - 50))
            o.set_data_value("energy",30)
            o.set_data_value("type","astroid")
            o.set_data_value("image", "astroid2")
            o.set_last_change(self.game.clock.get_time())
            o.get_body().angle = random.random() * 360
            SLShapeFactory.attach_circle(o,1)
            self.game.add_object(o)

        for i in range(3):
            o = SLObject(SLBody(body_type=pymunk.Body.STATIC))
            o.set_position(position=SLVector(
                random.random() * 80 - 40,
                random.random()  * 80 - 40))
            o.set_data_value("energy",10)
            o.set_data_value("type","food")
            o.set_data_value("image", "energy1")

            o.set_last_change(self.game.clock.get_time())
            SLShapeFactory.attach_circle(o,1)
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
            
                SLShapeFactory.attach_circle(o,1)
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

            if len(food_objs) ==1 and len(player_objs) ==1:
                food_energy = food_objs[0].get_data_value('energy')
                player_energy = player_objs[0].get_data_value('energy')
                player_objs[0].set_data_value("energy",
                    player_energy + food_energy)
                player_objs[0].set_last_change(self.game.clock.get_time())
                self.game.remove_object(food_objs[0])
                sound_event = SLSoundEvent(
                    creation_time=self.game.clock.get_time(), 
                    sound_id="bleep2")
                self.game.event_manager.add_event(sound_event)
                
                return False
            else:
                return True
                #self.game.object_manager.remove_by_id(food_objs[0].get_id())
        self.game.physics_engine.enable_collision_detection(collision_callback)
        print("Loading Game Complete")

    # Make callback
    def new_player(self)->SLPlayer:
        # Create Player
        create_time = self.game.clock.get_time()
        player_object = SLObject(SLBody(mass=8, moment=30), camera=SLCamera(distance=40))
        player_object.set_position(SLVector(10, 10))
        
        player_object.set_data_value("type","player")
        player_object.set_data_value("energy", 100)
        player_object.set_data_value("image", "1")

        # SLShapeFactory.attach_psquare(player_object, 1)
        SLShapeFactory.attach_circle(player_object, 1)
        player = SLPlayer(gen_id())
        player.attach_object(player_object)
        self.game.add_object(player_object)
        self.game.add_player(player)
        print("PLayer Obj {}".format(player_object.get_id()))

        def event_callback(event: SLPeriodicEvent,data:Dict[str,Any],om:SLObjectManager):
            t, obj = om.get_latest_by_id(data['obj_id'])
            if obj is None:
                return [], True
            new_energy = obj.get_data_value("energy") - 10
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

        self.game.event_manager.add_event(decay_event)
        return player
