from simpleland.event import InputEvent
from simpleland.object import GObject
from .player import Player
from .asset_bundle import AssetBundle
from abc import abstractmethod


class Content:

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def get_asset_bundle(self)->AssetBundle:
        """
        gets asset bundle - used for rendering and sounds
        """
        raise NotImplementedError()

    @abstractmethod
    def load(self):
        """
        loads the game content, called when game is started
        """
        raise NotImplementedError()

    @abstractmethod
    def reset(self):
        raise NotImplementedError()

    @abstractmethod
    def get_observation(self,ob:GObject):
        raise NotImplementedError()

    @abstractmethod
    def get_observation_space(self):
        raise NotImplementedError()

    @abstractmethod
    def get_action_space(self):
        raise NotImplementedError()

    @abstractmethod
    def get_step_reward(self,player:Player):
        """
        get reward for agent
        """
        raise NotImplementedError()

    @abstractmethod
    def process_input_event(self,event:InputEvent):
        raise NotImplementedError()

    @abstractmethod
    def new_player(self,  player_id=None, player_type = None) -> Player:
        """
        creates a new player, called when client connects to server
        """
        raise NotImplementedError()

    @abstractmethod
    def post_process_frame(self, render_time,  player: Player, renderer):
        """
        Additional rendering. TODO: make primary rendering override instead
        """
        raise NotImplementedError()

    @abstractmethod
    def pre_event_processing(self):
        raise NotImplementedError()

    @abstractmethod
    def pre_physics_processing(self):
        raise NotImplementedError()

    @abstractmethod
    def post_physics_processing(self):
        raise NotImplementedError()

    