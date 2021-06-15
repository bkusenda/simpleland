from abc import abstractclassmethod, abstractmethod
from typing import Dict, List, Any
from ..common import Base
from ..clock import clock
from ..content import Content

class SurvivalContent(Content):

    @abstractmethod
    def get_game_config(self)->Dict[str,Any]:
        pass

    @abstractmethod
    def get_effect_sprites(self,config_id):
        pass

    @abstractmethod
    def get_object_sprites(self,config_id):
        pass

    @abstractmethod
    def get_object_sounds(self,config_id):
        pass

    @abstractmethod
    def speed_factor(self):
        pass

    @abstractmethod
    def get_controller_by_id(self,cid):
        pass

    @abstractmethod
    def create_object_from_config_id(self,config_id):
        pass

    @abstractmethod
    def create_behavior(self,name):
        pass


class StateController(Base):

    def __init__(self,cid="",config={},*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.cid = cid
        self.config = config

    def reset(self):
        pass

    def update(self):
        pass

class Behavior:

    def __init__(self):
        pass

    def on_update(self,obj):
        pass

    def receive_message(self,sender,message_name,**kwargs):
        pass
