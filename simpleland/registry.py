from .config import ContentConfig, ServerConfig, GameConfig, ClientConfig, PhysicsConfig, RendererConfig, GameDef

import importlib.util
from .contentbundles import space_ship1
from .content import Content
from typing import Dict, Any
import pprint

# Init Registries
content_classes = {}
game_def_registry = {}


def load_game_def(game_id)->GameDef:
    game_def = game_def_registry.get(game_id)()
    return game_def

def load_game_content(game_def:GameDef) -> Content:
    return content_classes.get(game_def.content_id)(game_def.content_config)

# ****************************************
# REGISTER CONTENT BELOW
# ****************************************

# Content
content_classes['space_ship1'] = space_ship1.GameContent



# Game
game_def_registry['space_ship1'] = space_ship1.space_ship1_game_def


