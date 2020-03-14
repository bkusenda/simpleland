from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d


from .common import (SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock)
from .player import SLPlayer
from .utils import gen_id
from .object_manager import SLObjectManager
from .config import PhysicsConfig

class SLPhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self,clock:SimClock,config:PhysicsConfig):
        self.config = config
        self.clock = clock
        self.config = PhysicsConfig()
        self.space = SLSpace()
        self.space.damping = self.config.space_damping

    def enable_collision_detection(self, callback):
        h = self.space.add_collision_handler(1, 1)
        def begin(arbiter, space, data):
            return callback(arbiter,space,data)
        h.begin = begin

    def add_object(self, obj: SLObject):
        body = obj.body
        body.last_change = self.clock.get_time()

        def limit_velocity(b, gravity, damping, dt):
            max_velocity = self.config.default_max_velocity
            if b.velocity.length < self.config.default_min_velocity:
                b.velocity = SLVector(0.0,0.0)
            pymunk.Body.update_velocity(b, gravity, damping, dt)
            l = b.velocity.length
            scale = 1
            if l > max_velocity:
                scale = max_velocity / l
            b.velocity = b.velocity * scale
        
        body.velocity_func = limit_velocity
        

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

    def update(self,tick_rate:float):
        self.space.step(1.0/tick_rate)