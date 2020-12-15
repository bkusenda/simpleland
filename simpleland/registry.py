from .config import ContentConfig, ServerConfig, GameConfig, ClientConfig, PhysicsConfig, RendererConfig, GameDef

import importlib.util
from .contentbundles import space_ship1
from .content import Content
from typing import Dict, Any
import pprint

# Init Registries
content_classes = {}
game_registry = {}


def load_game_def(game_id)->GameDef:
    game_def = game_registry.get(game_id)()
    return game_def

def get_game_content(game_def:GameDef) -> Content:
    return content_classes.get(game_def.content_id)(game_def.content_config)

# ****************************************
# REGISTER CONTENT BELOW
# ****************************************

# Content
content_classes['space_ship1'] = space_ship1.GameContent


def build_game_space_ship1():
    env = GameDef(
        content_id = "space_ship1",
        content_config={'num_feelers':8})
    #additional config goes here
    return env

# Game
game_registry['space_ship1'] = build_game_space_ship1


