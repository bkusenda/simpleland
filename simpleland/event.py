
from typing import Any, Dict, List

from .utils import gen_id
from .object import GObject
from .object_manager import GObjectManager
from .common import Base, Vector
from simpleland import gamectx

def build_event_from_dict(data_dict):
    cls = globals()[data_dict['_type']]
    event = cls(**data_dict['data'])
    return event

class Event(Base):

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

class PeriodicEvent(Event):

    def __init__(self,
                func, 
                id=None, 
                execution_step_interval=None, 
                run_immediately = False,
                data={},
                **kwargs):

        super(PeriodicEvent,self).__init__(id,**kwargs)
        self.execution_step_interval = execution_step_interval
        self.last_run = None if run_immediately else gamectx.clock.get_tick_counter()
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self, om:GObjectManager):
        game_step = gamectx.clock.get_tick_counter()
        new_events = []
        remove_event = None
        if self.last_run is None or self.last_run + self.execution_step_interval <= game_step:
            new_events, remove_event = self.func(self,self.data,om)
            self.last_run = game_step

        return [], False

class DelayedEvent(Event):

    def __init__(self,
                func, 
                execution_step, 
                id=None,
                data={},
                **kwargs):

        super(DelayedEvent,self).__init__(id,**kwargs)
        self.execution_step = execution_step + gamectx.clock.get_tick_counter()
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self, om:GObjectManager):
        game_step = gamectx.clock.get_tick_counter()
        new_events = []
        if  self.execution_step <= game_step:
            new_events = self.func(self,self.data,om)
            return new_events, True
        return new_events, False


class SoundEvent(Event):

    def __init__(self,
                id=None, 
                creation_time=None, 
                sound_id = None,
                is_client_event=True,
                is_realtime_event=False,
                **kwargs):
        super(SoundEvent,self).__init__(id,
            is_client_event=is_client_event,
            is_realtime_event=is_realtime_event,
            **kwargs)
        self.creation_time = creation_time
        self.sound_id = sound_id

    def get_id(self):
        return self.id

class InputEvent(Event):

    @classmethod
    def build_from_dict(cls,dict_data, **kwargs):
        return cls(
            player_id = dict_data['player_id'],
            input_data = dict_data['input_data'],
            id = dict_data['id'],
            **kwargs)

    def __init__(self, 
                player_id: str,
                input_data: Dict[str,Any] ,
                id=None,
                **kwargs):
        super(InputEvent,self).__init__(id,**kwargs)
        self.player_id = player_id
        self.input_data = input_data

    def __repr__(self):
        return str(self.input_data)

class MechanicalEvent(Event):

    @classmethod
    def build_from_dict(cls,dict_data):
        return cls(obj_id = dict_data['obj_id'],
            direction = dict_data['direction'],
            orientation_diff = dict_data['orientation_diff'],
            id = dict_data['id'],
            kwargs = dict_data)

    def __init__(self, obj_id: str,
                 direction: Vector ,
                 orientation_diff: float = 0.0,
                 id=None,
                 **kwargs):
        super(MechanicalEvent,self).__init__(id,**kwargs)
        self.obj_id = obj_id
        self.direction = direction
        self.orientation_diff = orientation_diff

class PositioningUpdateEvent(Event):

    @classmethod
    def build_from_dict(cls,dict_data):
        return cls(obj_id = dict_data['obj_id'],
            position_update = dict_data['position_update'],
            angle_update = dict_data['angle_update'],
            id = dict_data['id'],
            kwargs = dict_data)

    def __init__(self, obj_id: str,
                 position_update: Vector ,
                 angle_update: float = 0.0,
                 id=None,
                 **kwargs):
        super(PositioningUpdateEvent,self).__init__(id,**kwargs)
        self.obj_id = obj_id
        self.position_update = position_update
        self.angle_update = angle_update

class AdminEvent(Event):

    def __init__(self, value, id=None, **kwargs):
        super(AdminEvent, self).__init__(id,**kwargs)
        self.value = value

class ViewEvent(Event):

    def __init__(self, player_id: str,
                 distance_diff: float = 0,
                 center_diff: Vector = None,
                 orientation_diff: float = 0.0, 
                 id=None,
                 **kwargs):
        super(ViewEvent, self).__init__(id, **kwargs)
        self.player_id = player_id
        self.distance_diff = distance_diff
        self.center_diff =  Vector.zero() if center_diff is None else center_diff
        self.orientation_diff = orientation_diff