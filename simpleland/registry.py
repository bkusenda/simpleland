from .config import ContentConfig, ServerConfig, GameConfig, ClientConfig, PhysicsConfig, RendererConfig, GameDef

import importlib.util
from .environments import g1, g2
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
content_classes['g1'] = g1.GameContent
content_classes['g2'] = g2.GameContent


def build_game_g1():
    env = GameDef(
        content_id = "g1",
        content_config={})
    #additional config goes here
    return env

def build_game_g2():
    env = GameDef(
        content_id = "g2",
        content_config={})
    #additional config goes here
    return env

# Game
game_registry['g1'] = build_game_g1
game_registry['g2'] = build_game_g2


