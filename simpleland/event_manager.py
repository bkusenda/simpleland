from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (SLBody, SLCircle, SLClock, SLVector, SLSpace,
                               SLLine, SLObject, SLPolygon, SLBase)
from .utils import gen_id
from .object_manager import SLObjectManager


def build_event_from_dict(data_dict):
    cls = globals()[data_dict['_type']]
    event = cls(**data_dict['data'])
    return event

class SLEvent(SLBase):

    def __init__(self, id=None):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id

    def get_id(self):
        return self.id

class SLPeriodicEvent(SLBase):

    def __init__(self,
                func, 
                id=None, 
                execution_interval=None, 
                data={}):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.execution_interval = execution_interval
        self.last_run = None
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self,game_time, om:SLObjectManager):
        new_events = []
        remove_event = None
        if self.last_run is None or self.last_run + self.execution_interval <= game_time:
            new_events, remove_event = self.func(self,self.data,om)
            self.last_run = game_time

        return [], False


class SLSoundEvent(SLBase):

    def __init__(self,
                func, 
                id=None, 
                exection_time=None, 
                sound_id = None,
                data={}):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.exection_time = exection_time
        self.data=data
        self.sound_id = sound_id

    def get_id(self):
        return self.id


class SLCollisionEvent(SLBase):

    def __init__(self,
                func, 
                shapes,
                id=None, 
                data={}):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.shapes = shapes
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self,om:SLObjectManager):
        return self.func(self,self.data,om)

class SLMechanicalEvent(SLEvent):

    @classmethod
    def build_from_dict(cls,dict_data):
        return cls(obj_id = dict_data['obj_id'],
            direction = dict_data['direction'],
            orientation_diff = dict_data['orientation_diff'],
            id = dict_data['id'])

    def __init__(self, obj_id: str,
                 direction: SLVector ,
                 orientation_diff: float = 0.0,
                 id=None):
        super(SLMechanicalEvent,self).__init__(id)
        self.obj_id = obj_id
        self.direction = direction
        self.orientation_diff = orientation_diff

class SLAdminEvent(SLEvent):

    def __init__(self, value, id=None):
        super(SLAdminEvent, self).__init__(id)
        self.value = value

class SLViewEvent(SLEvent):

    def __init__(self, obj_id: str,
                 distance_diff: float = 0,
                 center_diff: SLVector = None,
                 orientation_diff: float = 0.0, 
                 id=None):
        super(SLViewEvent, self).__init__(id)
        self.obj_id = obj_id
        self.distance_diff = distance_diff
        self.center_diff =  SLVector.zero() if center_diff is None else center_diff
        self.orientation_diff = orientation_diff

class SLEventManager:
    """
    Contains references to all game events
    """

    def __init__(self,config=None):
        self.config = {} if config is None else config

        self.events: Dict[str, SLEvent] = {}

    def add_event(self, e: SLEvent):
        self.events[e.get_id()] = e

    def add_events(self, events: List[SLEvent]):
        for e in events:
            self.add_event(e)

    def get_events(self):
        return list(self.events.values())

    def get_event_by_id(self, id):
        return self.events[id]

    def remove_event_by_id(self, id):
        del self.events[id]

    def clear(self):
        self.events: Dict[str, SLEvent] = {}

    def get_snapshot(self):
        events = self.get_events()
        results = {}
        for e in events:
            results[e.get_id()]= e.get_snapshot()
        return results

    def load_snapshot(self,data):
        for k,e_data in data.items():
            if k in self.events:
                self.events[k].load_snapshot(e_data)
            else:
                self.events[k] = build_event_from_dict(e_data)