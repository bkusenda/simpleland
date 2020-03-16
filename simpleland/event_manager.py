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

    def __init__(self, 
                id=None,
                creation_time=None,
                is_client_event=False,
                is_realtime_event=True):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.is_client_event = is_client_event
        self.is_realtime_event = is_realtime_event

    def get_id(self):
        return self.id

class SLPeriodicEvent(SLEvent):

    def __init__(self,
                func, 
                id=None, 
                execution_interval=None, 
                data={},
                **kwargs):

        super(SLPeriodicEvent,self).__init__(id,**kwargs)
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

class SLDelayedEvent(SLEvent):

    def __init__(self,
                func, 
                execution_time, 
                id=None,
                data={},
                **kwargs):

        super(SLDelayedEvent,self).__init__(id,**kwargs)
        self.execution_time = execution_time
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self,game_time, om:SLObjectManager):
        new_events = []
        if  self.execution_time <= game_time:
            new_events = self.func(self,self.data,om)
            return new_events, True
        return new_events, False


class SLSoundEvent(SLEvent):

    def __init__(self,
                id=None, 
                creation_time=None, 
                sound_id = None,
                is_client_event=True,
                is_realtime_event=False,
                **kwargs):
        super(SLSoundEvent,self).__init__(id,
            is_client_event=is_client_event,
            is_realtime_event=is_realtime_event,
            **kwargs)
        self.creation_time = creation_time
        self.sound_id = sound_id

    def get_id(self):
        return self.id

class SLInputEvent(SLEvent):

    @classmethod
    def build_from_dict(cls,dict_data):
        return cls(
            player_id = dict_data['player_id'],
            input_id = dict_data['input_id'],
            id = dict_data['id'])

    def __init__(self, 
                player_id: str,
                input_id: int ,
                id=None):
        super(SLInputEvent,self).__init__(id)
        self.player_id = player_id
        self.input_id = input_id

class SLMechanicalEvent(SLEvent):

    @classmethod
    def build_from_dict(cls,dict_data):
        return cls(obj_id = dict_data['obj_id'],
            direction = dict_data['direction'],
            orientation_diff = dict_data['orientation_diff'],
            id = dict_data['id'],
            kwargs = dict_data)

    def __init__(self, obj_id: str,
                 direction: SLVector ,
                 orientation_diff: float = 0.0,
                 id=None,
                 **kwargs):
        super(SLMechanicalEvent,self).__init__(id,**kwargs)
        self.obj_id = obj_id
        self.direction = direction
        self.orientation_diff = orientation_diff

class SLAdminEvent(SLEvent):

    def __init__(self, value, id=None, **kwargs):
        super(SLAdminEvent, self).__init__(id,**kwargs)
        self.value = value

class SLViewEvent(SLEvent):

    def __init__(self, obj_id: str,
                 distance_diff: float = 0,
                 center_diff: SLVector = None,
                 orientation_diff: float = 0.0, 
                 id=None,
                 **kwargs):
        super(SLViewEvent, self).__init__(id, **kwargs)
        self.obj_id = obj_id
        self.distance_diff = distance_diff
        self.center_diff =  SLVector.zero() if center_diff is None else center_diff
        self.orientation_diff = orientation_diff

class SLEventManager:
    """
    Contains references to all game events
    """

    def __init__(self):

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
        events = list(self.get_events())
        results = []
        for e in events:
            results.append(e.get_snapshot())
        return results

    def get_snapshot_for_client(self,timestamp):
        events = list(self.get_events())
        results = []
        for e in events:
            if e.is_client_event and e.creation_time >= timestamp: 
                results.append(e.get_snapshot())
        return results

    def load_snapshot(self,data):
        for e_data in data:
            k = e_data['data']['id']
            if k in self.events:
                self.events[k].load_snapshot(e_data)
            else:
                self.events[k] = build_event_from_dict(e_data)