from .game import Game
from .player import Player
from .renderer import Renderer
from .asset_bundle import AssetBundle
from abc import abstractmethod
class Content:

    def __init__(self, config):
        self.config = config
        self.data={}
    
    @abstractmethod
    def get_asset_bundle(self)->AssetBundle:
        """
        gets asset bundle - used for rendering and sounds
        """
        raise NotImplementedError()

    @abstractmethod
    def load(self, game: Game):
        """
        loads the game content, called when game is started
        """
        raise NotImplementedError()

    @abstractmethod
    def get_step_reward(self,player:Player,game:Game):
        """
        get reward for agent
        """
        raise NotImplementedError()

    # Make callback
    @abstractmethod
    def new_player(self, game: Game, player_id=None, player_type = None) -> Player:
        """
        creates a new player, called when client connects to server
        """
        raise NotImplementedError()

    @abstractmethod
    def post_process_frame(self, render_time, game: Game, player: Player, renderer: Renderer):
        """
        Additional rendering. TODO: make primary rendering override instead
        """
        raise NotImplementedError()
