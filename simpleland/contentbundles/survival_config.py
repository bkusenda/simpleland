
from ..config import GameDef


TILE_SIZE = 16

############
# Game Defs #
#############


def game_def(content_overrides={}):

    content_config = {
        'default_camera_zoom': TILE_SIZE*10,
        "tile_size": TILE_SIZE,
        "food_energy":10,
        "food_count": 1,
        "player_config": {
            "health_start": 100,
            "health_gen": 5,
            "health_max": 100,
            "health_gen_period": 10,
            "stamina_max": 100,
            "stamina_gen": 40,
            "stamina_gen_period": 1,
            "energy_start": 100,
            "energy_max": 100,
            "energy_decay_period": 50,
            "energy_decay": 1,
            "low_energy_health_penalty": 10,
            "strength": 1,
            "inventory_size": 1,
            "walk_speed": 3.75,
            "attack_speed": 0.75,
            "vision_radius": 4
        },
        "monster_config": {
            "health_start": 100,
            "health_gen": 1,
            "health_max": 100,
            "health_gen_period": 10,
            "stamina_max": 100,
            "stamina_gen": 20,
            "stamina_gen_period": 1,
            "energy_start": 100,
            "energy_max": 100,
            "energy_decay_period": 0,
            "energy_decay": 0,
            "low_energy_health_penalty": 0,
            "strength": 1,
            "inventory_size": 1,
            "walk_speed": .2,
            "attack_speed": .2,
            "vision_radius": 4
        }
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