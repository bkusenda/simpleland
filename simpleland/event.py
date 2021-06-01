
from typing import Any, Dict, List
from .utils import gen_id
from .common import Base, Vector
from .clock import clock

def build_event_from_dict(data_dict):
    cls = globals()[data_dict['_type']]
    event = cls(**data_dict['data'])
    return event

class Event(Base):

    def __init__(self, 
                id=None,
                creation_time = None,
                is_client_event=False,
                is_server_event=True):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.creation_time = creation_time or clock.get_tick_counter()
        self.is_client_event = is_client_event
        self.is_server_event = is_server_event

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

        super().__init__(id,**kwargs)
        self.execution_step_interval = execution_step_interval
        self.last_run = None if run_immediately else clock.get_tick_counter()
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self):
        game_step = clock.get_tick_counter()
        new_events = []
        remove_event = None
        if self.last_run is None or self.last_run + self.execution_step_interval <= game_step:
            new_events, remove_event = self.func(self,self.data)
            self.last_run = game_step

        return [], False

class DelayedEvent(Event):

    def __init__(self,
                func, 
                execution_step, 
                id=None,
                data={},
                is_client_event=False,
                **kwargs):

        super().__init__(id,is_client_event=is_client_event,**kwargs)
        self.execution_step = execution_step + clock.get_tick_counter()
        self.data=data
        self.func = func

    def get_id(self):
        return self.id

    def run(self):
        game_step = clock.get_tick_counter()

        new_events = []
        if  self.execution_step <= game_step:
            new_events = self.func(self,self.data)
            return new_events, True
        return new_events, False


class RemoveObjectEvent(Event):

    def __init__(self,
                object_id,
                id=None,
                data={},
                is_client_event=True,
                **kwargs):

        super().__init__(id,is_client_event=is_client_event,**kwargs)
        self.data=data
        self.object_id = object_id

    def get_id(self):
        return self.id


class SoundEvent(Event):

    def __init__(self,
                id=None, 
                sound_id = None,
                is_client_event=True,
                position = None,
                **kwargs):
        super().__init__(id,
            is_client_event=is_client_event,
            **kwargs)
        self.sound_id = sound_id
        self.position = position

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
        super().__init__(id,**kwargs)
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
        super().__init__(id,**kwargs)
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
        super().__init__(id,**kwargs)
        self.obj_id = obj_id
        self.position_update = position_update
        self.angle_update = angle_update

class AdminEvent(Event):

    def __init__(self, value, id=None, **kwargs):
        super().__init__(id,**kwargs)
        self.value = value

class ViewEvent(Event):

    def __init__(self, player_id: str,
                 distance_diff: float = 0,
                 center_diff: Vector = None,
                 orientation_diff: float = 0.0, 
                 id=None,
                 **kwargs):
        super().__init__(id, **kwargs)
        self.player_id = player_id
        self.distance_diff = distance_diff
        self.center_diff =  Vector.zero() if center_diff is None else center_diff
        self.orientation_diff = orientation_diff