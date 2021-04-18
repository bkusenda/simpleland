from .config import  GameDef

from .contentbundles import space_grid1, space_phy1,space_phy2, survival_grid
from .content import Content

# Init Registries
content_classes = {}
game_def_registry = {}


def load_game_def(game_id,content_overrides={})->GameDef:

    game_def = game_def_registry.get(game_id)(content_overrides)
    return game_def

def load_game_content(game_def:GameDef) -> Content:
    return content_classes.get(game_def.content_id)(game_def.content_config)

# ****************************************
# REGISTER CONTENT BELOW
# ****************************************

# TODO: scan for game_defs and load from entrypoint in game_def
# Content
content_classes['space_grid1'] = space_grid1.GameContent
content_classes['space_phy1'] = space_phy1.GameContent
content_classes['space_phy2'] = space_phy2.GameContent
content_classes['survival_grid'] = survival_grid.GameContent

# Game
game_def_registry['space_grid1'] = space_grid1.game_def
game_def_registry['survival_grid'] = survival_grid.game_def
game_def_registry['space_phy1'] = space_phy1.game_def
game_def_registry['space_phy2'] = space_phy2.game_def