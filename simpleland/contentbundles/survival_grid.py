import math
from simpleland import physics_engine
import random
from typing import Dict, Any, Tuple

import pymunk
from pymunk import contact_point_set
from pymunk.vec2d import Vec2d

from ..common import (Body, Camera, Circle,  Line,
                      Polygon, Shape, Space, Vector,
                      TimeLoggingContainer)
from ..event import (DelayedEvent, Event, InputEvent,
                     PeriodicEvent, SoundEvent, ViewEvent)
from .. import gamectx
from ..object import GObject

from ..player import Player
from ..renderer import Renderer
from ..utils import gen_id
from ..content import Content

from ..asset_bundle import AssetBundle
from ..common import COLLISION_TYPE
import numpy as np
from ..clock import clock
from typing import List,Dict,Any
from ..event import InputEvent, Event, ViewEvent, DelayedEvent
from .. import gamectx
from ..common import Body, Vector
import pygame
from ..clock import clock
from gym import spaces
import sys
import math
from .survival_assets import *
from .survival_utils import *
from .survival_config import TILE_SIZE


def process_food_collision(player_obj: GObject, food_obj):

    food_energy = food_obj.get_data_value('energy')
    player_energy = player_obj.get_data_value('energy')
    player_obj.set_data_value("energy",
                              player_energy + food_energy)
    food_reward_count = player_obj.get_data_value('food_reward_count', 0)
    food_reward_count += 1
    player_obj.set_data_value("food_reward_count", food_reward_count)
    food_counter = gamectx.data.get('food_counter', 0)
    gamectx.data['food_counter'] = food_counter - 1

    gamectx.remove_object(food_obj)

    sound_event = SoundEvent(
        sound_id="bleep")
    gamectx.add_event(sound_event)
    return False

def process_lava_collision(player_obj, lava_obj):
    player_obj.set_data_value("health", 0)
    return False

def default_collision_callback(obj1: GObject, obj2: GObject):
    if obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "food":
        return process_food_collision(obj1, obj2)
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "lava":
        return process_lava_collision(obj1, obj2)
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "rock":
        obj1.set_data_value("action", None)
        return True
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "player":
        obj1.set_data_value("action", None)
        return True
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "tree":
        obj1.set_data_value("action", None)
        return True
    return False

def get_item_map(item_types):
    item_map = {}
    for i, k in enumerate(item_types):
        v = np.zeros(len(item_types)+1)
        v[i] = 1
        item_map[k] = v
    return item_map

class GameContent(Content):

    def __init__(self, config):
        super().__init__(config)
        self.asset_bundle = load_asset_bundle()
        self.space_size = config['space_size']
        self.space_border = config['space_border']
        self.food_energy = config['food_energy']
        self.food_count = config['food_count']
        self.characters = {}

        self.item_types = ['tree', 'food', 'rock', 'player']
        self.item_map = get_item_map(self.item_types)
        self.default_v = np.zeros(len(self.item_types)+1)
        self.default_v[len(self.item_types)] = 1

        self.item_type_count = len(self.item_types)
        self.vision_distance = 2

        self.player_count = 0
        self.keymap = [23, 19, 4, 1]

        self.spawn_locations = []
        self.food_locations = []
        self.loaded = False

        self.player_idle_sprites = {
            'down': ['player_idle_down_1', 'player_idle_down_2', 'player_idle_down_3', 'player_idle_down_4', 'player_idle_down_5', 'player_idle_down_6'],
            'up': ['player_idle_up_1', 'player_idle_up_2', 'player_idle_up_3', 'player_idle_up_4', 'player_idle_up_5', 'player_idle_up_6'],
            'left': ['player_idle_left_1', 'player_idle_left_2', 'player_idle_left_3', 'player_idle_left_4', 'player_idle_left_5', 'player_idle_left_6'],
            'right': ['player_idle_right_1', 'player_idle_right_2', 'player_idle_right_3', 'player_idle_right_4', 'player_idle_right_5', 'player_idle_right_6']}
        self.player_walk_sprites = {
            'down': ['player_walk_down_1', 'player_walk_down_2', 'player_walk_down_3', 'player_walk_down_4', 'player_walk_down_5', 'player_walk_down_6'],
            'up': ['player_walk_up_1', 'player_walk_up_2', 'player_walk_up_3', 'player_walk_up_4', 'player_walk_up_5', 'player_walk_up_6'],
            'left': ['player_walk_left_1', 'player_walk_left_2', 'player_walk_left_3', 'player_walk_left_4', 'player_walk_left_5', 'player_walk_left_6'],
            'right': ['player_walk_right_1', 'player_walk_right_2', 'player_walk_right_3', 'player_walk_right_4', 'player_walk_right_5', 'player_walk_right_6']}
        self.player_attack_sprites = {
            'down': ['player_atk_down_1', 'player_atk_down_2', 'player_atk_down_3', 'player_atk_down_4', 'player_atk_down_5', 'player_atk_down_6'],
            'up': ['player_atk_up_1', 'player_atk_up_2', 'player_atk_up_3', 'player_atk_up_4', 'player_atk_up_5', 'player_atk_up_6'],
            'left': ['player_atk_left_1', 'player_atk_left_2', 'player_atk_left_3', 'player_atk_left_4', 'player_atk_left_5', 'player_atk_left_6'],
            'right': ['player_atk_right_1', 'player_atk_right_2', 'player_atk_right_3', 'player_atk_right_4', 'player_atk_right_5', 'player_atk_right_6']}


    def speed_factor(self):
        return max(gamectx.speed_factor() * 1/6, 1)

    def get_asset_bundle(self):
        return self.asset_bundle

    def reset(self):
        if not self.loaded:
            self.load()
        gamectx.remove_all_events()

        def food_event_callback(event: PeriodicEvent, data: Dict[str, Any]):
            self.spawn_food(limit=1)
            return [], True
        new_food_event = PeriodicEvent(food_event_callback, execution_step_interval=random.randint(10, 16) * self.speed_factor())
        gamectx.add_event(new_food_event)

        self.spawn_food()
        self.spawn_players()

    def reset_required(self):
        for player in gamectx.player_manager.players_map.values():
            if not player.get_data_value("reset_required", True):
                return False
        return True

    def get_new_character_location(self):
        loc = random.choice(gamectx.content.spawn_locations)
        return coord_to_vec(loc)


    def spawn_player(self,player, reset=False):
        if player.get_object_id() is not None:
            character = gamectx.object_manager.get_by_id(player.get_object_id())
            if reset:
                character.reset()
        else:
            character= Character(player)
            self.characters[player.get_id()] = character
        
        character.spawn(self.get_new_character_location())
        return character


    def spawn_players(self,reset=True):
        for player in gamectx.player_manager.players_map.values():
            self.spawn_player(player,reset)

    def spawn_food(self, limit=None):
        # Spawn food
        spawn_count = 0
        for i, coord in enumerate(self.food_locations):
            if len(gamectx.physics_engine.space.get_objs_at(coord)) == 0:
                Food(coord_to_vec(coord))
                spawn_count += 1
                if limit is not None and spawn_count >= limit:
                    return

    def get_observation_space(self):
        x_dim = (self.vision_distance * 2 + 1)
        y_dim = x_dim
        chans = len(self.item_types) + 1
        return spaces.Box(low=0, high=1, shape=(x_dim, y_dim, chans))

    def get_action_space(self):
        return spaces.Discrete(len(self.keymap))

    def get_observation(self, obj: GObject):
        obj_coord = gamectx.physics_engine.vec_to_coord(obj.get_position())
        xvis = self.vision_distance
        yvis = self.vision_distance
        col_min = obj_coord[0] - xvis
        col_max = obj_coord[0] + xvis
        row_min = obj_coord[1] - yvis
        row_max = obj_coord[1] + yvis
        results = []
        for r in range(row_max, row_min-1, -1):
            row_results = []
            for c in range(col_min, col_max+1):
                obj_ids = gamectx.physics_engine.space.get_objs_at((c, r))
                if len(obj_ids) > 0:
                    obj_id = obj_ids[0]
                    obj_seen = gamectx.object_manager.get_by_id(obj_id)
                    row_results.append(self.item_map.get(obj_seen.get_data_value('type')))
                else:
                    row_results.append(self.default_v)
            results.append(row_results)
        return np.array(results)

    def get_step_info(self, player: Player) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        observation = None
        done = False
        reward = 0
        info = {}
        if player is not None:
            if not player.get_data_value("allow_obs", False):
                return None, None, None, None

            obj_id = player.get_object_id()
            obj = gamectx.object_manager.get_by_id(obj_id)
            observation = self.get_observation(obj)
            done = player.get_data_value("reset_required", False)
            if done:
                player.set_data_value("allow_obs", False)

            info['lives_used'] = player.get_data_value("lives_used")
            energy = obj.get_data_value("energy")
            info['energy'] = energy

            # Claim food rewards
            food_reward_count = obj.get_data_value("food_reward_count", 0)
            obj.set_data_value("food_reward_count", 0)
            reward = food_reward_count
            # if energy == 0:
            #     reward += -1
            if done:
                reward = -5
        else:
            info['msg'] = "no player found"
        return observation, reward, done, info


    def load_map(self):
        for i, layer in enumerate(map_layers):
            lines = layer.split("\n")

            self.spawn_locations = []
            for ridx, line in enumerate(reversed(lines)):
                for cidx, ch in enumerate(line):
                    coord = (cidx, ridx)
                    if ch == 'b':
                        Rock(coord_to_vec(coord))
                    elif ch == 'f':
                        self.food_locations.append(coord)
                    elif ch == 's':
                        self.spawn_locations.append(coord)
                    elif ch == 'g':
                        Grass(coord_to_vec(coord))
                    elif ch == 't':
                        Tree(coord_to_vec(coord))

    # **********************************
    # GAME LOAD
    # **********************************
    def load(self):
        self.loaded = False
        self.load_map()

        gamectx.physics_engine.set_collision_callback(
            default_collision_callback,
            COLLISION_TYPE['default'],
            COLLISION_TYPE['default'])

        self.loaded = True

    def process_input_event(self, input_event:InputEvent):
        events= []
        player = gamectx.player_manager.get_player(input_event.player_id)
        if not player.get_data_value("allow_input",False):
            return []
        if player is None:
            return []

        keys = set(input_event.input_data['inputs'])

        obj:Character = gamectx.object_manager.get_by_id(player.get_object_id())
        if obj is None:
            return events
        
        if not obj.enabled:
            return []
        elif player.get_data_value("reset_required",False):
            print("Episode is over. Reset required")
            return events


        if 27 in keys:
            print("QUITTING")
            gamectx.change_game_state("STOPPED")
            return events

        # Queued action prevents movement until complete. Trigger at a certain time and releases action lock later but 
        if  clock.get_tick_counter() < obj.get_data_value("action_completion_time",0):
            return events

        # Object Movement
        actions_set = set()
        direction = Vector.zero()
        angle_update = None
        if 23 in keys:
            direction = Vector(0, 1)
            angle_update = 0
            actions_set.add("MOVE")

        if 19 in keys:
            direction = Vector(0, -1)
            angle_update = math.pi
            actions_set.add("MOVE")

        if 4 in keys:
            direction = Vector(1, 0)
            angle_update = -math.pi/2
            actions_set.add("MOVE")
            
        if 1 in keys:
            direction = Vector(-1, 0)
            angle_update = math.pi/2
            actions_set.add("MOVE")

        if 5 in keys:
            actions_set.add("GRAB")

        if 6 in keys:
            actions_set.add("DROP")

        if 18 in keys:
            actions_set.add("ATTACK")

        if 31 in keys:
            events.append(ViewEvent(player.get_id(), 100))

        if 10 in keys:
            print("Adding admin_event ...TODO!!")

        if "GRAB" in actions_set:
            obj.grab()
        elif "DROP" in actions_set:
            obj.drop()
        elif "ATTACK" in actions_set:
            obj.attack()
        elif "MOVE" in actions_set:
            obj.move(direction,angle_update)

        return events

    # **********************************
    # NEW PLAYER
    # **********************************
    def new_player(self, client_id, player_id=None, player_type=0, is_human=False) -> Player:
        if self.player_count > len(self.spawn_locations):
            raise Exception("Number of players cannot exceed spawn locations")
        # Create Player
        if player_id is None:
            player_id = gen_id()
        player = gamectx.player_manager.get_player(player_id)
        if player is None:
            cam_distance = self.space_size
            if player_type == 10:
                cam_distance = TILE_SIZE*6
            player = Player(
                client_id=client_id,
                uid=player_id,
                camera=Camera(distance=cam_distance),
                player_type=player_type,
                is_human = is_human)

            gamectx.add_player(player)
        player.set_data_value("view_type", 1)
        if player_type == 10:
            return player
        self.spawn_player(player,reset=True)
        
        return player

    def pre_event_processing(self):
        return []

    def pre_physics_processing(self):
        return []

    def post_physics_processing(self):
        new_events = []
        cur_time = clock.get_time()
        for k, p in gamectx.player_manager.players_map.items():
            if p.get_object_id() is None:
                continue

            o = gamectx.object_manager.get_by_id(p.get_object_id())

            if o is None or o.is_deleted or not o.enabled:
                continue

            if o.enabled:
                o.update()

        return new_events


    def post_process_frame(self, render_time, player: Player, renderer: Renderer):
        if player is not None and player.player_type == 0:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))

            obj = gamectx.object_manager.get_by_id(player.get_object_id())
            obj_health = 0
            if obj is not None:
                obj_energy = obj.get_data_value("energy", "NA")
                obj_health = obj.get_data_value("health", "NA")
                obj_stamina = obj.get_data_value("stamina", "NA")

                lines.append(f"H:{obj_health}, E:{obj_energy}, S:{obj_stamina}")
                lines.append("Current Velocity: {}".format(obj.get_body()._get_velocity()))


            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)
                if obj_health <= 0:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)



# def input_event_callback_fpv(input_event: InputEvent, player) -> List[Event]:

#     events= []
#     tile_size = gamectx.physics_engine.config.tile_size
#     keys = set(input_event.input_data['inputs'])

#     obj = gamectx.object_manager.get_by_id(player.get_object_id())
#     if obj is None:
#         return events
#     gamectx.content.get_observation(obj)

#     rotation_multiplier = obj.get_data_value('rotation_multiplier')
#     velocity_multiplier = obj.get_data_value('velocity_multiplier')

#     obj_orientation_diff = 0
#     if 1 in keys:
#         obj_orientation_diff = math.pi/2

#     if 4 in keys:
#         obj_orientation_diff = -math.pi/2

#     # Object Movement
#     direction:Vector = Vector.zero()

#     if 23 in keys:
#         direction = Vector(0, 1)

#     if 19 in keys:
#         direction = Vector(0, -1)

#     if 31 in keys:
#         events.append(ViewEvent(player.get_id(), 100))

#     if 10 in keys:
#         print("Adding admin_event ...TODO!!")

#     def move_event_fn(event: DelayedEvent, data: Dict[str, Any]):
#         direction = data['direction']
#         orientation_diff = obj_orientation_diff * rotation_multiplier
#         direction = direction * velocity_multiplier
#         body:Body = obj.get_body()
#         angle = body.angle
#         direction = direction.rotated(angle)
#         new_pos = tile_size * direction + body.position
#         obj.update_position(new_pos)
#         body.angle = angle + orientation_diff
#         return []

#     movement_event = False
#     if movement_event:

#         event = DelayedEvent(move_event_fn, execution_step=0, data={'direction':direction})
#         events.append(event)

#     return events
