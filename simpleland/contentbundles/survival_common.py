from abc import abstractclassmethod, abstractmethod
from typing import Dict, List, Any
from ..common import Base
from ..clock import clock
from ..content import Content


class SurvivalContent(Content):

    @abstractmethod
    def get_game_config(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_effect_sprites(self, config_id):
        pass

    @abstractmethod
    def get_object_sprites(self, config_id):
        pass

    @abstractmethod
    def get_object_sounds(self, config_id):
        pass

    @abstractmethod
    def speed_factor(self):
        pass

    @abstractmethod
    def get_controller_by_id(self, cid):
        pass

    @abstractmethod
    def create_object_from_config_id(self, config_id):
        pass

    @abstractmethod
    def create_behavior(self, name):
        pass

class Effect(Base):

    def __init__(self, config_id="", ticks=1, step_size=1, angle_step_size=0):
        self.config_id = config_id
        self.ticks = ticks
        self.step_size = step_size
        self.start_tick = clock.get_tick_counter()
        self.angle_step_size = angle_step_size


class Action(Base):

    def __init__(self, type="UNKNOWN", ticks=1, step_size=1,start_tick=None,blocking=True,continuous=False,start_position = None):
        self.type = type
        self.ticks = ticks
        self.step_size = step_size
        self.start_tick = start_tick or clock.get_tick_counter()
        self.continuous = continuous
        self.blocking = blocking
        self.start_position = start_position

        self.expired = False

    def is_expired(self):
        if self.expired:
             return True
        else:
            self.expired = self.continuous is False and ((clock.get_tick_counter() - self.start_tick) > self.ticks )
            return self.expired



class Trigger:

    def __init__(self, id, func):
        self.id = id
        self.func = func


class StateController(Base):

    def __init__(self, cid="", config={}, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cid = cid
        self.config = config

    def reset(self):
        pass

    def update(self):
        pass


class Behavior:

    def __init__(self):
        pass

    def on_update(self, obj):
        pass

    def receive_message(self, sender, message_name, **kwargs):
        pass
