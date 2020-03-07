from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d


from .common import (PhysicsConfig, SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock)
from .player import SLPlayer
from .utils import gen_id
from .object_manager import SLObjectManager

class SLPhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self,clock:SimClock):
        self.clock = clock
        self.config = PhysicsConfig()
        self.space = SLSpace()
        self.space.damping = self.config.space_damping

    def enable_collision_detection(self, callback):

        h = self.space.add_collision_handler(1, 1)

        def begin(arbiter, space, data):
            callback(arbiter,space,data)
            return True

        h.begin = begin

    def add_object(self, obj: SLObject):
        body = obj.body
        body.last_change = self.clock.get_time()
        def velocity_callback(body:SLBody, gravity, damping, dt):
            init_v = body.velocity
            if init_v.length < 0.5:
                body.velocity = SLVector(0.0,0.0)
            pymunk.Body.update_velocity(body, gravity, damping, dt)
            new_v = body.velocity
            if init_v != new_v:
                body.last_change = self.clock.get_time()
        body.velocity_func = velocity_callback


        def position_callback(body:SLBody, dt):
            init_p = body.position
            pymunk.Body.update_position(body,dt)
            new_p = body.position
            if init_p != new_p:
                body.last_change = self.clock.get_time()
        body.position_func = position_callback
        self.space.add(obj.get_body(), obj.get_shapes())

    def remove_object(self,obj):
        self.space.remove(obj.get_shapes())
        self.space.remove(obj.get_body())

    def update(self, om: SLObjectManager, steps_per_second:float):
        self.space.step(1.0/steps_per_second)