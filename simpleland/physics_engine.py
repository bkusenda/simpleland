from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d
from .common import (Body, Circle, Clock, Line,
                     Polygon, Space, Vector, SimClock)
from .object import GObject
# from .player import Player
from .utils import gen_id
from .object_manager import GObjectManager
from .config import PhysicsConfig
import math

def get_default_velocity_callback(clock, config):
    def limit_velocity(b, gravity, damping, dt):
        max_velocity = config.default_max_velocity
        if b.velocity.length < config.default_min_velocity:
            b.velocity = Vector(0.0,0.0)
        pymunk.Body.update_velocity(b, gravity, damping, dt)
        l = b.velocity.length
        scale = 1
        if l > max_velocity:
            scale = max_velocity / l
        b.velocity = b.velocity * scale
    return limit_velocity

def get_default_position_callback(clock, config):
    def position_callback(body:Body, dt):
        init_p = body.position
        pymunk.Body.update_position(body,dt)
        new_p = body.position
        if init_p != new_p:
            body.last_change = clock.get_time()
    return position_callback

class PhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self,clock:SimClock,config:PhysicsConfig):
        self.config = config
        self.clock = clock
        self.space = Space(threaded=True)
        self.space.threads = 2
        self.space.idle_speed_threshold = 0.01
        self.space.damping = self.config.space_damping
        self.sim_timestep = self.config.sim_timestep
        dt = 1.0/self.config.tick_rate
        self.steps_per_update = math.ceil(dt/self.sim_timestep)
        actual_tick_rate = 1/ (self.steps_per_update * self.sim_timestep)
        print("Actual Physics Tick Rate is {}, original {} (change due to enforcing sim_timestep size of {})".format(actual_tick_rate, self.config.tick_rate,self.config.sim_timestep))

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

    def add_object(self, obj: GObject):
        body = obj.body
        body.last_change = self.clock.get_time()
        body.velocity_func = self.velocity_callback 
        body.position_func = self.position_callback
        self.space.add(obj.get_body(), obj.get_shapes())

    def remove_object(self,obj):
        self.space.remove(obj.get_shapes())
        self.space.remove(obj.get_body())

    def update(self):
        for _ in range(self.steps_per_update):
            self.space.step(self.sim_timestep)
