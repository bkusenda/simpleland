import math
from simpleland import physics_engine
import random
from typing import Dict, Any, Tuple

import pymunk
from pymunk import contact_point_set
from pymunk.vec2d import Vec2d
from ..camera import Camera
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
from ..common import  Vector
import pygame
from ..clock import clock
from gym import spaces
import sys
import math
from .survival_assets import *
from .survival_utils import *

############################
# COLLISION HANDLING
############################

def process_food_collision(player_obj: AnimateObject, food_obj:Food):

    food_energy = food_obj.energy
    player_obj.energy +=food_energy

    #TODO: replace
    player_obj.reward +=1
    
    food_counter = gamectx.data.get('food_counter', 0)
    gamectx.data['food_counter'] = food_counter - 1

    gamectx.remove_object(food_obj)

    sound_event = SoundEvent(
        sound_id="bleep")
    gamectx.add_event(sound_event)
    return False

def process_water_collision(player_obj:AnimateObject, obj):
    player_obj.health =  0
    return False

def default_collision_callback(obj1: PhysicalObject, obj2: PhysicalObject):
    if obj1.type == "human" and obj2.type == "food":
        return process_food_collision(obj1, obj2)
    elif ('animal' in obj1.get_types() and obj2.type == "water") or ('water' in obj1.get_types() and 'animal' in obj2.get_types()):
        return process_water_collision(obj1, obj2)
    elif 'animal' in obj1.get_types()  and obj2.collision_type >0:
        obj1.default_action()
        return obj2.collision_type
    
    return obj1.collision_type >0 and obj1.collision_type == obj2.collision_type

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
        self.default_camera_zoom = config['default_camera_zoom']
        self.food_energy = config['food_energy']
        self.food_count = config['food_count']
        self.tile_size = config['tile_size']
        
        self.characters = {}

        self.item_types = ['tree', 'food', 'rock', 'player', 'wood']
        self.item_map = get_item_map(self.item_types)
        self.default_v = np.zeros(len(self.item_types)+1)
        self.default_v[len(self.item_types)] = 1

        self.item_type_count = len(self.item_types)
        self.vision_distance = 2

        self.player_count = 0
        self.keymap = [23, 19, 4, 1, 5, 6, 18,0]

        self.spawn_locations = []
        self.food_locations = []
        self.loaded = False
        self.tilemap = TileMap()
        self._speed_factor = None
        self.call_counter = 0



    def speed_factor(self):
        if self._speed_factor is not None:
            return self._speed_factor
        
        """
        Step size in ticks
        """
        tick_rate = gamectx.tick_rate
        if not tick_rate or tick_rate == 0:
            tick_rate = 1
        self._speed_factor = max(tick_rate * 1/6,1)
        return self._speed_factor

    def get_asset_bundle(self):
        return self.asset_bundle

    def get_class_by_type_name(self,name):
        if name == "Human":
            return Human
        elif name == "Monster":
            return Monster
        elif name == "Food":
            return Food
        elif name == "Deer":
            return Deer
        elif name == "Tree":
            return Tree
        elif name == "Rock":
            return Rock
        elif name == "Wood":
            return Wood
        else:
            return GObject

    def reset_required(self):
        for player in gamectx.player_manager.players_map.values():
            if not player.get_data_value("reset_required", True):
                return False
        return True


    #####################
    # RL AGENT METHODS
    #####################

    def reset(self):
        if not self.loaded:
            self.load()
        gamectx.remove_all_events()

        def food_event_callback(event: PeriodicEvent, data: Dict[str, Any]):
            self.spawn_food(limit=1)
            return [], True

        new_food_event = PeriodicEvent(
            food_event_callback, 
            execution_step_interval=random.randint(10, 16) * self.speed_factor())
        gamectx.add_event(new_food_event)

        self.spawn_food()
        self.spawn_players()

    # TODO: get from player to object
    def get_observation_space(self):
        x_dim = (self.vision_distance * 2 + 1)
        y_dim = x_dim
        chans = len(self.item_types) + 1
        return spaces.Box(low=0, high=1, shape=(x_dim, y_dim, chans))

    # TODO: get from player to object
    def get_action_space(self):
        return spaces.Discrete(len(self.keymap))

    # TODO: get from player to object
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
            obj: AnimateObject = gamectx.object_manager.get_by_id(obj_id)
            observation = self.get_observation(obj)
            done = player.get_data_value("reset_required", False)
            if done:
                player.set_data_value("allow_obs", False)

            info['lives_used'] = player.get_data_value("lives_used")
            energy = obj.energy
            info['energy'] = energy

            # Claim food rewards
            food_reward_count = obj.reward
            obj.reward = 0
            reward = food_reward_count

            if done:
                reward = -5
        else:
            info['msg'] = "no player found"
        return observation, reward, done, info
    

    def reset_player(self,player:Player):
        player.set_data_value("lives_used", 0)
        player.set_data_value("food_reward_count", 0)
        player.set_data_value("reset_required", False)
        player.set_data_value("allow_obs", True)
        player.events = []


    # **********************************
    # NEW PLAYER
    # **********************************
    def new_player(self, client_id, player_id=None, player_type=0, is_human=False) -> Player:
        if player_id is None:
            player_id = gen_id()
        player = gamectx.player_manager.get_player(player_id)
        if player is None:
            cam_distance = self.default_camera_zoom
            player = Player(
                client_id=client_id,
                uid=player_id,
                camera=Camera(distance=cam_distance,view_type=1),
                player_type=player_type,
                is_human = is_human)
            gamectx.add_player(player)
        self.spawn_player(player,reset=True)        
        return player


    #########################
    # Loading/Spawning
    #########################
    def spawn_player(self,player:Player, reset=False,loc_idx=0):
        if player.get_object_id() is not None:
            character = gamectx.object_manager.get_by_id(player.get_object_id())
        else:
            character= Human(config=self.config['human_config'] ,player=player)
            self.characters[player.get_id()] = character
        if reset:
            self.reset_player(player)

        character.spawn(coord_to_vec(self.spawn_locations[loc_idx % len(self.spawn_locations)]))
        return character


    def spawn_players(self,reset=True):
        for loc_idx,player in enumerate(gamectx.player_manager.players_map.values()):
            self.spawn_player(player,reset,loc_idx)

    def spawn_food(self, limit=None):
        # Spawn food
        spawn_count = 0
        for i, coord in enumerate(self.food_locations):
            if len(gamectx.physics_engine.space.get_objs_at(coord)) == 0:
                Food().spawn(coord_to_vec(coord))
                spawn_count += 1
                if limit is not None and spawn_count >= limit:
                    return
        

    # **********************************
    # GAME LOAD
    # **********************************
    def load(self, is_client_only=False):
        self.loaded = False
        if not is_client_only:
            WorldMap(map_layers)

        gamectx.physics_engine.set_collision_callback(
            default_collision_callback,
            COLLISION_TYPE['default'],
            COLLISION_TYPE['default'])
        self.loaded = True

    ########################
    # GET INPUT
    ########################

    def is_valid_input_event(self, input_event:InputEvent):
        # TODO: Switch to filter multiple input events
        
        player = gamectx.player_manager.get_player(input_event.player_id)
        
        if player is None or not player.get_data_value("allow_input",False) or player.get_data_value("reset_required",False):
            return False

        obj:Human = gamectx.object_manager.get_by_id(player.get_object_id())

        if obj is not None and obj.get_action().get('blocking',True):
            return False
        return True

    def process_input_event(self, input_event:InputEvent):
        events= []


        player = gamectx.player_manager.get_player(input_event.player_id)
        if player is None:
            print("PLAYER IS NON")
            return []
        if not player.get_data_value("allow_input",False):
            return []
        keys = set(input_event.input_data['inputs'])

        obj:Human = gamectx.object_manager.get_by_id(player.get_object_id())

        if 27 in keys:
            print("QUITTING")
            gamectx.change_game_state("STOPPED")
            return events

        if obj is None or not obj.enabled:
            return events
        
        elif player.get_data_value("reset_required",False):
            print("Episode is over. Reset required")
            return events


        # Object Movement
        actions_set = set()
        direction = Vector.zero()
        angle_update = None
        if 23 in keys:
            direction = Vector(0, -1)
            angle_update = math.pi
            actions_set.add("MOVE")

        if 19 in keys:
            direction = Vector(0, 1)
            angle_update = 0
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

        if  7 in keys:
            actions_set.add("PUSH")

        if 0 in keys:
            actions_set.add("NA")

        if 31 in keys:
            events.append(ViewEvent(player.get_id(), 100))

        if "GRAB" in actions_set:
            obj.grab()
        elif "DROP" in actions_set:
            obj.drop()
        elif "ATTACK" in actions_set:
            obj.attack()
        elif "PUSH" in actions_set:
            obj.push()
        elif "MOVE" in actions_set:
            obj.walk(direction,angle_update)

        return events

    def update(self):
        for k, o in gamectx.object_manager.get_objects().items():
            if o is None or o.is_deleted or not o.enabled:
                continue
            if o.is_enabled():
                o.update()

    def prepare_ac(self):
        for k, o in gamectx.object_manager.get_objects().items():
            if o is None or o.is_deleted or not o.enabled:
                continue
            if o.is_enabled():
                o.update()


    def post_process_frame(self, player: Player, renderer: Renderer):
        if player is not None and player.player_type == 0:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))

            obj:AnimateObject = gamectx.object_manager.get_by_id(player.get_object_id())
            obj_health = 0
            if obj is not None:
                obj_energy = obj.energy
                obj_health = obj.health
                obj_stamina = obj.stamina
                inv = obj.inventory
                inventory_st = " ".join([f"{k}:{v}" for k,v in inv.items()])
                lines.append(f"H:{obj_health}, E:{obj_energy}, S:{obj_stamina}")
                lines.append(f"Inventory: {inventory_st}")
   

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
