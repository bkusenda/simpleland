
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
from typing import Any, Dict, List, Tuple

import lz4.frame
import numpy as np
import pygame
import pymunk
from pymunk import Vec2d

from .common import (SimClock, SLBody, SLCamera, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLShape, SLSpace, SLVector,
                     TimeLoggingContainer)
from .config import ClientConfig, PhysicsConfig, RendererConfig, ServerConfig
from .event_manager import (SLAdminEvent, SLDelayedEvent, SLEvent,
                            SLEventManager, SLInputEvent, SLMechanicalEvent,
                            SLPeriodicEvent, SLSoundEvent, SLViewEvent)
from .game import SLGame, StateDecoder, StateEncoder
from .itemfactory import SLItemFactory, SLShapeFactory
from .object_manager import SLObjectManager
from .physics_engine import SLPhysicsEngine
from .player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from .renderer import SLRenderer
from .utils import gen_id


def input_event_callback(input_event: SLInputEvent, game: SLGame) -> List[SLEvent]:

    # for event in pygame.event.get():
    #     # print("%s" % event.type)
    #     if event.type == pygame.QUIT:
    #         admin_event = SLAdminEvent('QUIT')
    #         events.append(admin_event)
    #         print("Adding admin_event (via pygame_event) %s" % admin_event)
    #     elif event.type == pygame.MOUSEBUTTONDOWN:
    #         # print("here %s" % event.button)
    #         if event.button == 4:
    #             view_event = SLViewEvent(player.get_object_id(), 1, SLVector.zero())
    #             events.append(view_event)
    #         elif event.button == 5:
    #             view_event = SLViewEvent(player.get_object_id(), -1, SLVector.zero())
    #             events.append(view_event)
    keys = input_event.input_data['inputs']
    if len(keys) == 0:
        return []

    player = game.player_manager.get_player(input_event.player_id)
    t, obj = game.object_manager.get_latest_by_id(player.get_object_id())
    if obj is None:
        return []

    move_speed = 0.04
    obj_orientation_diff = 0
    if '17' in keys:
        obj_orientation_diff = 1

    if '5' in keys:
        obj_orientation_diff = -1

    # Object Movement
    force = 1
    direction = SLVector.zero()
    if '23' in keys:
        direction += SLVector(0, 1)

    if '19' in keys:
        direction += SLVector(0, -1)

    if '1' in keys:
        direction += SLVector(-1, 0)

    if '4' in keys:
        direction += SLVector(1, 0)

    if '10' in keys:
        print("Adding admin_event ...TODO!!")

    mag = direction.length
    if mag != 0:
        direction = ((1.0 / mag) * force * direction)
    else:
        direction = SLVector.zero()

    orientation_diff = obj_orientation_diff * move_speed

    direction = direction * 25
    obj.set_last_change(game.clock.get_time())
    body = obj.get_body()

    direction = direction.rotated(body.angle)
    body.apply_impulse_at_world_point(direction, body.position)
    body.angular_velocity += orientation_diff

    if body.angular_velocity > 3:
        body.angular_velocity = 3
    elif body.angular_velocity < -3:
        body.angular_velocity = -3
    return []


class ContentManager:

    def __init__(self, config):
        self.config = config
        self.config['space_size'] = 50

    def get_random_pos(self):
        return SLVector(
            random.random() * self.config['space_size'] - (self.config['space_size']/2),
            random.random() * self.config['space_size'] - (self.config['space_size']/2))

    def load(self, game: SLGame):
        print("Starting Game")

        # Create Wall
        wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                    SLVector(0, 0),
                                    size=self.config['space_size'])
        wall.set_data_value("type", "static")
        game.add_object(wall)

        # Create some Large Recangls
        for i in range(4):
            o = SLObject(SLBody(body_type=pymunk.Body.STATIC))
            o.set_position(position=self.get_random_pos())
            o.set_data_value("energy", 30)
            o.set_data_value("type", "wall")
            o.set_data_value("image", "lava1")
            o.set_last_change(game.clock.get_time())
            o.get_body().angle = random.random() * 360
            SLShapeFactory.attach_rectangle(o, 10, 3)  # .attach_circle(o,1)
            game.add_object(o)

        # Create some Astroids
        for i in range(20):
            o = SLObject(SLBody(mass=5, moment=1))
            o.set_position(position=self.get_random_pos())
            o.set_data_value("energy", 30)
            o.set_data_value("type", "astroid")
            o.set_data_value("image", "astroid2")
            o.set_last_change(game.clock.get_time())
            o.get_body().angle = random.random() * 360
            # SLShapeFactory.attach_rectangle(o,2,2)
            SLShapeFactory.attach_circle(o, 2)

            game.add_object(o)

        for i in range(3):
            o = SLObject(SLBody(body_type=pymunk.Body.STATIC))
            o.set_position(position=SLVector(
                random.random() * 80 - 40,
                random.random() * 80 - 40))
            o.set_data_value("energy", 10)
            o.set_data_value("type", "food")
            o.set_data_value("image", "energy1")

            o.set_last_change(game.clock.get_time())
            SLShapeFactory.attach_circle(o, 1)
            game.add_object(o)

        def new_food_event_callback(event: SLPeriodicEvent, data: Dict[str, Any], om: SLObjectManager):
            for i in range(0, random.randint(0, 1)):
                o = SLObject(SLBody(body_type=pymunk.Body.KINEMATIC))
                o.set_position(position=self.get_random_pos())
                o.set_data_value("energy", 10)
                o.set_data_value("type", "food")
                o.set_data_value("image", "energy1")
                o.set_last_change(game.clock.get_time())

                SLShapeFactory.attach_circle(o, 1)
                game.add_object(o)
            return [], False
        new_food_event = SLPeriodicEvent(new_food_event_callback, execution_interval=2000)
        game.event_manager.add_event(new_food_event)

        # TODO, move to standard event callback
        def collision_callback(arbiter: pymunk.Arbiter, space, data):
            food_objs = []
            player_objs = []
            for s in arbiter.shapes:
                s: SLShape = s
                t, o = game.object_manager.get_latest_by_id(s.get_object_id())
                if o is None:
                    return False
                if o.get_data_value("type") == "food":
                    food_objs.append(o)
                elif o.get_data_value("type") == "player":
                    player_objs.append(o)

            if len(food_objs) == 1 and len(player_objs) == 1:
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
                # self.game.object_manager.remove_by_id(food_objs[0].get_id())
        game.physics_engine.set_collision_callback(collision_callback)

        def pre_physics_callback(game: SLGame):
            new_events = []
            for k, p in game.player_manager.players_map.items():
                # print(p.get_object_id())
                if p.get_object_id() is None:
                    continue
                t, o = game.object_manager.get_latest_by_id(p.get_object_id())
                if o is None or o.is_deleted:
                    continue
                if o.get_data_value("energy") <= 0:
                    print("Player is dead")
                    lives_used = p.get_data_value("lives_used", 0)
                    p.set_data_value("lives_used", lives_used+1)
                    game.remove_object(o)
                    # Delete and create event

                    def event_callback(event: SLDelayedEvent, data: Dict[str, Any], om: SLObjectManager):
                        self.new_player(game, player_id=data['player_id'])
                        print("New Player Created")
                        return []

                    new_ship_event = SLDelayedEvent(
                        func=event_callback,
                        execution_time=game.clock.get_time() + 2000,
                        data={'player_id': p.get_id()})

                    new_events.append(new_ship_event)
                    # Response
            return new_events
        game.set_pre_physics_callback(pre_physics_callback)
        game.set_input_event_callback(input_event_callback)

        print("Loading Game Complete")

    # Make callback
    def new_player(self, game: SLGame, player_id=None) -> SLPlayer:
        # Create Player
        if player_id is None:
            player_id = gen_id()
        player = game.player_manager.get_player(player_id)

        if player is None:
            player = SLPlayer(player_id)
        print("playerData: {}".format(player.data))

        create_time = game.clock.get_time()
        player_object = SLObject(SLBody(mass=8, moment=30),
                                 camera=SLCamera(distance=30))
        player_object.set_position(position=self.get_random_pos())

        player_object.set_data_value("type", "player")
        player_object.set_data_value("energy", 100)
        player_object.set_data_value("image", "1")
        player_object.set_data_value("player_id", player.get_id())

        # SLShapeFactory.attach_rectangle(player_object, 2,2)
        SLShapeFactory.attach_circle(player_object, 1)

        player.attach_object(player_object)
        game.add_object(player_object)
        game.add_player(player)
        print("PLayer Obj {}".format(player_object.get_id()))

        def event_callback(event: SLPeriodicEvent, data: Dict[str, Any], om: SLObjectManager):
            t, obj = om.get_latest_by_id(data['obj_id'])
            if obj is None or obj.is_deleted:
                return [], True
            new_energy = max(obj.get_data_value("energy") - 1, 0)
            #     # om.remove_by_id(obj.get_id())
            #     return [], False
            print(new_energy)
            obj.set_data_value('energy', new_energy)
            obj.set_last_change(game.clock.get_time())
            return [], False

        decay_event = SLPeriodicEvent(
            event_callback,
            execution_interval=2000,
            data={'obj_id': player_object.get_id()})

        game.event_manager.add_event(decay_event)
        return player

    def post_process_frame(self, render_time, game: SLGame, player: SLPlayer, renderer: SLRenderer):
        if player is None:
            print("Player Dead")
        else:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))

            obj = game.object_manager.get_by_id(player.get_object_id(), render_time)
            if obj is not None:
                lines.append("Current Energy: {}".format(obj.get_data_value("energy", 0)))

            renderer.render_to_console(lines, x=5, y=5)

            if obj is None:
                renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)
