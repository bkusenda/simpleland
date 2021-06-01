from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d, Body
from .common import (Circle,  Line,
                     Polygon, Vector,  COLLISION_TYPE)
from .object import GObject
# from .player import Player
from .utils import gen_id
from .config import PhysicsConfig
import math
from .clock import clock

def get_default_velocity_callback(config):
    def limit_velocity(b, gravity, damping, dt):
        max_velocity = config.default_max_velocity
        if b.velocity.length < config.default_min_velocity:
            b.velocity = Vector(0.0,0.0)
        # if abs(b.angular_velocity) < 0.05:
        #     b.angular_velocity = 0 
        pymunk.Body.update_velocity(b, gravity, damping, dt)
        l = b.velocity.length
        scale = 1
        if l > max_velocity:
            scale = max_velocity / l
        b.velocity = b.velocity * scale
    return limit_velocity

def get_default_position_callback(config):
    def position_callback(body:Body, dt):
        init_p = body.position
        pymunk.Body.update_position(body,dt)
        new_p = body.position
        if init_p != new_p:
            body.last_change = clock.get_time()
    return position_callback

class GridSpace:


    def __init__(self):
        self.coord_to_obj= {}
        self.obj_to_coord = {}
        self.tracked_objs ={}
        # NOT USED
        self.sectors = {}

    def get_sector_id(self,coord):
        return coord[0] // 20, coord[1] // 20

    def get_objs_at(self,coord):
        return self.coord_to_obj.get(coord,[])

    def move_obj_to(self,coord,obj:GObject):
        obj_id = obj.get_id()
        self.remove_obj(obj_id)
        obj_ids = self.coord_to_obj.get(coord,[])
        obj_ids.append(obj_id)
        self.coord_to_obj[coord] = obj_ids
        self.obj_to_coord[obj_id] = coord
        self.tracked_objs[obj_id] = obj

    def remove_obj(self,obj_id):
        last_coord = self.obj_to_coord.get(obj_id)
        ids = self.coord_to_obj.get(last_coord,[])
        if last_coord is None:
            return
        
        if len(ids) <=1:
            del self.coord_to_obj[last_coord]
        else:
            try:
                ids.remove(obj_id)
                self.coord_to_obj[last_coord] = ids
            except:
                pass
        del self.obj_to_coord[obj_id]
        del self.tracked_objs[obj_id]

    def get_obj_by_id(self,obj_id):
        return self.tracked_objs.get(obj_id)

    def debug_draw(self,*args,**kwargs):
        raise NotImplementedError("debug_draw Not supported for this space type")


class GridPhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self,config:PhysicsConfig):
        self.config = config
        self.tile_size = self.config.tile_size
        self.space = GridSpace()
        self.position_updates = {}
        self.collision_callbacks ={}

    def vec_to_coord(self,v):
        
        return (round(v.x / self.tile_size),round(v.y / self.tile_size))#(round(v.x / self.tile_size),round(v.y / self.tile_size))

    def coord_to_vec(self,coord):
        return Vector(coord[0] * self.tile_size, coord[1] * self.tile_size)

    def set_collision_callback(self, 
            callback, 
            collision_type_a=COLLISION_TYPE['default'], 
            collision_type_b=COLLISION_TYPE['default']):

        self.collision_callbacks[(collision_type_a,collision_type_b)] = callback
        self.collision_callbacks[(collision_type_b,collision_type_a)] = callback


    def add_object(self, obj: GObject):
        obj.last_change = clock.get_time()
        obj.set_update_position_callback(self.update_obj_position)
        self.update_obj_position(obj,obj.get_position(),skip_collision_check=True)

    def update_obj_position(self,obj:GObject,new_pos,skip_collision_check=False,callback=None):
        if skip_collision_check:
            coord =self.vec_to_coord(new_pos)
            self.space.move_obj_to(coord,obj)
            obj.position = new_pos
            if callback is not None:
                callback(True)
        else:
            self.position_updates[obj.get_id()] = (obj,new_pos,callback)


    def remove_object(self,obj):
        self.space.remove_obj(obj.get_id())

    def update(self):
        obj:GObject

        for obj,new_pos,callback in self.position_updates.values():
            if not obj.enabled:
                continue
            new_pos = Vector(round(new_pos.x),round(new_pos.y))
            coord =self.vec_to_coord(new_pos)
            coll_objs_ids = self.space.get_objs_at(coord)
            collision_effect = False
            for obj_id_2 in coll_objs_ids:
                if obj_id_2 != obj.get_id():
                    obj2:GObject = self.space.get_obj_by_id(obj_id_2)
                    if not obj2.enabled:
                        continue
                    collition_types1 = [shape.collision_type for shape in obj.get_shapes()]
                    collition_types2 = [shape.collision_type for shape in obj2.get_shapes()]
                    for col_type1 in collition_types1:
                        for col_type2 in collition_types2:                            
                            cb = self.collision_callbacks.get((col_type1,col_type2))
                            if cb is not None and cb(obj,obj2):
                                collision_effect = True
                    
            if not collision_effect:
                self.space.move_obj_to(coord,obj)
                obj.position = new_pos
                if callback:
                    callback(True)

        self.position_updates = {}



class PymunkPhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self,config:PhysicsConfig):
        self.config = config
        self.space = Space(threaded=True)
        self.space.threads = 2
        self.space.idle_speed_threshold = 0.01
        self.space.sleep_time_threshold = 0.5
        self.space.damping = self.config.space_dampening
        self.space.collision_slop = 0.9
        self.sim_timestep = self.config.sim_timestep

        dt = 0 if self.config.tick_rate == 0 else 1.0/self.config.tick_rate
        self.steps_per_update = math.ceil(dt/self.sim_timestep)
        actual_tick_rate = 0 if self.steps_per_update == 0 else 1/ (self.steps_per_update * self.sim_timestep)
        print("Actual Physics Tick Rate is {}, original {} (change due to enforcing sim_timestep size of {})".format(actual_tick_rate, self.config.tick_rate,self.config.sim_timestep))

        # Called at each step when velocity is updated
        self.velocity_callback = get_default_velocity_callback(self.config)
        
        # Called at each step when position is updated
        self.position_callback= get_default_position_callback(self.config)

    def set_collision_callback(self, callback, collision_type_a=COLLISION_TYPE['default'], collision_type_b=COLLISION_TYPE['default']):
        h = self.space.add_collision_handler(collision_type_a, collision_type_b)
        def callerfun(arbiter, space, data):
            return callback(arbiter,space,data)
        # h.begin = begin
        h.pre_solve = callerfun

    def add_object(self, obj: GObject):
        body = obj.body
        body.last_change = clock.get_time()
        # body.velocity_func = self.velocity_callback 
        body.position_func = self.position_callback
        self.space.add(obj.get_body(), obj.get_shapes())

    def remove_object(self,obj):
        pass
        # self.space.remove(obj.get_shapes())
        # self.space.remove(obj.get_body())

    def update(self):
        for _ in range(self.steps_per_update):
             self.space.step(self.sim_timestep)