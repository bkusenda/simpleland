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

def get_default_velocity_callback(clock, config):
    def limit_velocity(b, gravity, damping, dt):
        max_velocity = config.default_max_velocity
        if b.velocity.length < config.default_min_velocity:
            b.velocity = SLVector(0.0,0.0)
        pymunk.Body.update_velocity(b, gravity, damping, dt)
        l = b.velocity.length
        scale = 1
        if l > max_velocity:
            scale = max_velocity / l
        b.velocity = b.velocity * scale
    return limit_velocity

def get_default_position_callback(clock, config):
    def position_callback(body:SLBody, dt):
        init_p = body.position
        pymunk.Body.update_position(body,dt)
        new_p = body.position
        if init_p != new_p:
            body.last_change = clock.get_time()
    return position_callback

class SLPhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self,clock:SimClock,config:PhysicsConfig):
        self.config = config
        self.clock = clock
        self.space = SLSpace()
        self.space.damping = self.config.space_damping

        # Called at each step when velocity is updated
        self.velocity_callback = get_default_velocity_callback(self.clock,self.config)
        
        # Called at each step when position is updated
        self.position_callback= get_default_position_callback(self.clock,self.config)

    def set_collision_callback(self, callback):
        h = self.space.add_collision_handler(1, 1)
        def begin(arbiter, space, data):
            return callback(arbiter,space,data)
        h.begin = begin

    def set_velocity_callback(self,callback):
        self.velocity_callback = callback
    
    def set_position_callback(self,callback):
        self.position_callaback = callback

    def add_object(self, obj: SLObject):
        body = obj.body
        body.last_change = self.clock.get_time()
        body.velocity_func = self.velocity_callback 
        body.position_func = self.position_callback
        self.space.add(obj.get_body(), obj.get_shapes())

    def remove_object(self,obj):
        self.space.remove(obj.get_shapes())
        self.space.remove(obj.get_body())

    def update(self,tick_rate:float):
        self.space.step(1.0/tick_rate)