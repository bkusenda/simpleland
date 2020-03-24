from .game import Game
from .player import Player
from .renderer import Renderer

class Content:

    def __init__(self, config):
        self.config = config
    
    def get_asset_bundle(self):
        raise NotImplementedError()

    def load(self, game: Game):
        raise NotImplementedError()

    # Make callback
    def new_player(self, game: Game, player_id=None, player_type=None) -> Player:
        raise NotImplementedError()

    def post_process_frame(self, render_time, game: Game, player: Player, renderer: Renderer):
        raise NotImplementedError()
