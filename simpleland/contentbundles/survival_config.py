
from ..config import GameDef


TILE_SIZE = 16

############
# Game Defs #
#############


def game_def(content_overrides={}):

    content_config = {
        'space_size': TILE_SIZE*10,
        "space_border": 20*TILE_SIZE,
        "tile_size": TILE_SIZE,
        "food_energy":10,
        "player_config": {
            "health_start": 100,
            "health_gen": 5,
            "health_max": 100,
            "health_gen_period": 10,
            "stamina_max": 100,
            "stamina_gen": 2,
            "stamina_gen_period": 1,
            "energy_start": 100,
            "energy_max": 100,
            "energy_decay_period": 5,
            "energy_decay": 10,
            "low_energy_health_penalty": 10,
            "strength": 1,
            "inventory_size": 1
        },
        "actions": {
            "rest": {
                "duration": 1,
                "energy_cost": 0,
                "stamina_cost": 0
            },
            "walk": {
                "duration": 4,
                "energy_cost": 1,
                "stamina_cost": 0
            },
            "run": {
                "duration": 2,
                "energy_cost": 3,
                "stamina_cost": 10
            },
            "attack": {
                "duration": 4,
                "energy_cost": 12,
                "stamina_cost": 20
            },
            "pickup": {
                "duration": 6,
                "energy_cost": 2,
                "stamina_cost": 2
            },
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