
from ..config import GameDef


TILE_SIZE = 16

#############
# Game Defs #
#############

def game_def(content_overrides={}):

    content_config = {
        'default_camera_zoom': TILE_SIZE*10,
        "tile_size": TILE_SIZE,
        "food_energy":10
    }

    content_config.update(content_overrides)

    game_def = GameDef(
        content_id="survival_grid",
        content_config=content_config
    )
    game_def.physics_config.tile_size = TILE_SIZE
    game_def.physics_config.engine = "grid"
    game_def.game_config.wait_for_user_input = False
    return game_def