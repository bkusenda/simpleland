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
from ..itemfactory import ItemFactory, ShapeFactory
from ..object import GObject
from ..object_manager import GObjectManager
from ..player import Player
from ..renderer import Renderer
from ..utils import gen_id
from ..content import Content

from ..asset_bundle import AssetBundle
from ..common import COLLISION_TYPE
import numpy as np
from ..config import GameDef, PhysicsConfig
from ..clock import clock
from typing import List,Dict,Any
from ..event import InputEvent, Event, AdminEvent,ViewEvent, DelayedEvent
from .. import gamectx
from ..common import Body, Vector
import pygame
from ..clock import clock

import sys
import math


map_layer_1 = (
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n" 
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n" 
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n" 
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n"
    # f"gggggggggggggggggggggggggggggg\n" 
    # f"gggggggggggggggggggggggggggggg\n" 
    f"\n" 

)
# s

map_layer_2 = (
    
    f"bbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
    f"b                         b\n"
    f"b                         b\n"
    f"b          ffffffff       b\n" 
    f"b            t            b\n"
    f"b         s     f  s      b\n"
    f"b                         b\n"
    f"bbbbbbbbbbbbbbbbbbbbbbbbbb\n"

)


map_layers = [map_layer_1,map_layer_2]

TILE_SIZE = 16

############
# Game Defs #
#############


def game_def(content_overrides={}):

    content_config = {
        'space_size': TILE_SIZE*10,
        'player_start_energy': 20,
        'food_energy': 5,
        'food_count': 1,
        "space_border": 20*TILE_SIZE,
        "tile_size": TILE_SIZE,
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
            "energy_decay": 2,
            "low_energy_health_penalty": 20,
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



def get_view_position_fn(obj: GObject):
    action_data = obj.get_data_value("action")
    cur_tick = clock.get_tick_counter()
    if action_data:        
        if action_data['start_tick'] + action_data['ticks'] >= cur_tick:
            if action_data['type'] == 'walk':
                idx = cur_tick - action_data['start_tick']
                view_position = action_data['step_size'] * idx * action_data['direction'] + action_data['start_position']
                return view_position

    return obj.get_position()


def get_image_id_fn(obj: GObject, angle):
    if obj.get_data_value("type") == "player":
        angle_num = obj.body.angle/math.pi
        direction = "down"
        if angle_num < 0.25 and angle_num >= -0.25:
            direction = "up"
        elif angle_num > 0.25 and angle_num <= 0.75:
            direction = "left"
        elif angle_num < -0.25 and angle_num >= -0.75:
            direction = "right"
        elif abs(angle_num) >= 0.75:
            direction = "down"

        action_data = obj.get_data_value("action")
        cur_tick = clock.get_tick_counter()
        sprites_list = gamectx.content.player_idle_sprites
        sprite_idx= None
        if action_data is not None:
            if action_data['start_tick'] + action_data['ticks'] > cur_tick:
                if action_data['type'] == 'walk':
                    sprites_list = gamectx.content.player_walk_sprites
                    action_idx = (cur_tick - action_data['start_tick'])
                    sprite_idx = int((action_idx/action_data['ticks']) * len(sprites_list[direction]))
                elif action_data['type'] == 'attack':
                    sprites_list = gamectx.content.player_attack_sprites
                    action_idx = (cur_tick - action_data['start_tick'])
                    sprite_idx = int((action_idx/action_data['ticks']) * len(sprites_list[direction]))
        
        if sprite_idx is None:
            sprite_idx = int(cur_tick//gamectx.content.speed_factor()) % len(sprites_list[direction])
        return sprites_list[direction][sprite_idx]
    else:
        return obj.image_id_default


def load_asset_bundle():
    image_assets = {}
    image_assets['1'] = ('assets/redfighter0006.png', None)
    image_assets['1_thrust'] = ('assets/redfighter0006_thrust.png', None)

    image_assets['2'] = ('assets/ship2.png', None)
    image_assets['energy1'] = ('assets/energy1.png', None)
    image_assets['lava'] = ('assets/lava1.png', None)

    image_assets['player_idle_down_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "1")
    image_assets['player_idle_down_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "2")
    image_assets['player_idle_down_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "3")
    image_assets['player_idle_down_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "4")
    image_assets['player_idle_down_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "5")
    image_assets['player_idle_down_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "6")

    image_assets['player_idle_up_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "1")
    image_assets['player_idle_up_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "2")
    image_assets['player_idle_up_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "3")
    image_assets['player_idle_up_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "4")
    image_assets['player_idle_up_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "5")
    image_assets['player_idle_up_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "6")

    image_assets['player_idle_right_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "1")
    image_assets['player_idle_right_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "2")
    image_assets['player_idle_right_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "3")
    image_assets['player_idle_right_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "4")
    image_assets['player_idle_right_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "5")
    image_assets['player_idle_right_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "6")

    image_assets['player_idle_left_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "1")
    image_assets['player_idle_left_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "2")
    image_assets['player_idle_left_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "3")
    image_assets['player_idle_left_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "4")
    image_assets['player_idle_left_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "5")
    image_assets['player_idle_left_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "6")

    image_assets['player_walk_down_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "1")
    image_assets['player_walk_down_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "2")
    image_assets['player_walk_down_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "3")
    image_assets['player_walk_down_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "4")
    image_assets['player_walk_down_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "5")
    image_assets['player_walk_down_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "6")

    image_assets['player_walk_up_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "1")
    image_assets['player_walk_up_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "2")
    image_assets['player_walk_up_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "3")
    image_assets['player_walk_up_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "4")
    image_assets['player_walk_up_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "5")
    image_assets['player_walk_up_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "6")

    image_assets['player_walk_right_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "1")
    image_assets['player_walk_right_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "2")
    image_assets['player_walk_right_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "3")
    image_assets['player_walk_right_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "4")
    image_assets['player_walk_right_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "5")
    image_assets['player_walk_right_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "6")

    image_assets['player_walk_left_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "1")
    image_assets['player_walk_left_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "2")
    image_assets['player_walk_left_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "3")
    image_assets['player_walk_left_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "4")
    image_assets['player_walk_left_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "5")
    image_assets['player_walk_left_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "6")

    #attack
    image_assets['player_atk_down_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "1")
    image_assets['player_atk_down_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "2")
    image_assets['player_atk_down_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "3")
    image_assets['player_atk_down_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "4")
    image_assets['player_atk_down_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "5")
    image_assets['player_atk_down_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "6")

    image_assets['player_atk_up_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "1")
    image_assets['player_atk_up_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "2")
    image_assets['player_atk_up_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "3")
    image_assets['player_atk_up_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "4")
    image_assets['player_atk_up_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "5")
    image_assets['player_atk_up_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "6")

    image_assets['player_atk_right_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "1")
    image_assets['player_atk_right_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "2")
    image_assets['player_atk_right_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "3")
    image_assets['player_atk_right_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "4")
    image_assets['player_atk_right_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "5")
    image_assets['player_atk_right_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "6")

    image_assets['player_atk_left_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "1")
    image_assets['player_atk_left_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "2")
    image_assets['player_atk_left_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "3")
    image_assets['player_atk_left_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "4")
    image_assets['player_atk_left_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "5")
    image_assets['player_atk_left_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "6")

    image_assets['grass1'] = ('assets/tinyadventurepack/Other/Misc/Grass.png', None)
    image_assets['grass2'] = ('assets/tinyadventurepack/Other/Misc/Grass2.png', None)
    image_assets['grass3'] = ('assets/tinyadventurepack/Other/Misc/Grass3.png', None)
    image_assets['tree'] = ('assets/tinyadventurepack/Other/Misc/Tree/Tree.png', None)
    image_assets['tree_trunk'] = ('assets/tinyadventurepack/Other/Misc/Tree/Tree_trunk.png', None)
    image_assets['tree_top'] = ('assets/tinyadventurepack/Other/Misc/Tree/Tree_top.png', None)
    image_assets['food'] = ('assets/tinyadventurepack/Other/Red_orb.png', None)

    image_assets['rock'] = ('assets/tinyadventurepack/Other/Misc/Rock.png', None)

    sound_assets = {}
    sound_assets['bleep2'] = 'assets/sounds/bleep2.wav'


    return AssetBundle(
        image_assets=image_assets, 
        sound_assets=sound_assets,
        get_image_id_fn=get_image_id_fn,
        get_view_position_fn=get_view_position_fn)


def vec_to_coord(v):
    tile_size = gamectx.content.config['tile_size']
    return (int(v.x / tile_size), int(v.y / tile_size))


def coord_to_vec(coord):
    tile_size = gamectx.content.config['tile_size']
    return Vector(float(coord[0] * tile_size), float(coord[1] * tile_size))

class Food(GObject):

    def __init__(self,position):
        super().__init__(Body())  
        self.set_data_value("energy", gamectx.content.config['food_energy'])
        self.set_data_value("type", "food")
        self.set_image_id("food")
        self.set_position(position=position)
        self.set_last_change(clock.get_time())
        ShapeFactory.attach_circle(self, radius=TILE_SIZE/6)
        gamectx.add_object(self)
        gamectx.data['food_counter'] = gamectx.data.get('food_counter', 0) + 1


class Character(GObject):

    def __init__(self,player: Player):
        super().__init__(Body(mass=2, moment=0))  
        self.set_data_value("rotation_multiplier", 1)
        self.set_data_value("velocity_multiplier", 1)
        self.set_data_value("type", "player")
        self.set_image_id("player_idle_down_1")
        self.set_data_value("player_id", player.get_id())
        # self.set_position(position=Vector(0,0))
        self.disable()
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)
        player.attach_object(self)
        gamectx.add_object(self)
        player.set_data_value("lives_used", 0)
        player.set_data_value("food_reward_count", 0)
        player.set_data_value("reset_required", False)
        player.set_data_value("allow_obs", True)
        player.events = []

    def get_player(self):
        return gamectx.player_manager.get_player(self.get_data_value("player_id"))

    def spawn(self,position, reset=False):
        self.update_position(position=position)
        self.set_data_value("energy",  gamectx.content.config['player_config']['energy_start'])
        self.set_data_value("health", gamectx.content.config['player_config']['health_start'])
        self.set_data_value("stamina", gamectx.content.config['player_config']['stamina_max'])
        self.set_data_value("next_energy_decay", 0)
        self.set_data_value("next_health_gen", 0)
        player = self.get_player()
        player.set_data_value("allow_input", False)
        self.enable()


class Tree(GObject):

    def __init__(self,position, shape_color=(100, 130, 100)):
        super().__init__(Body())
        self.set_data_value("type", "tree")
        self.set_data_value("health", 100)
        self.set_position(position)
        self.set_visiblity(False)
        self.set_last_change(clock.get_time())
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)
        gamectx.add_object(self)

        trunk =self.add_tree_trunk()
        self.set_data_value("trunk_id", trunk.get_id())
        top =self.add_tree_top()
        self.set_data_value("top_id", top.get_id())        

    def add_tree_trunk(self):
        o = GObject(Body(),depth=1)
        o.set_data_value("type", "part")
        o.set_image_id(f"tree_trunk")
        o.set_position(position=self.get_position())
        o.set_last_change(clock.get_time())
        ShapeFactory.attach_rectangle(o, width=TILE_SIZE, height=TILE_SIZE)
        gamectx.add_object(o)
        return o

    def add_tree_top(self):
        o = GObject(Body(),depth=3)
        o.set_data_value("type", "part")
        o.set_image_id(f"tree_top")
        o.set_image_offset(Vector(0,-TILE_SIZE*1.5))
        o.set_last_change(clock.get_time())
        o.set_position(position=self.get_position())
        
        ShapeFactory.attach_rectangle(o, width=TILE_SIZE*2, height=TILE_SIZE*2)
        gamectx.add_object(o)
        return o



def add_rock(position, type="rock", shape_color=(100, 100, 100)):
    o = GObject(Body())
    o.set_data_value("type", type)
    o.set_image_id(type)
    o.set_position(position=position)
    o.set_last_change(clock.get_time())
    o.set_shape_color(shape_color)
    ShapeFactory.attach_rectangle(o, width=TILE_SIZE, height=TILE_SIZE)
    gamectx.add_object(o)

def add_grass(position, shape_color=(100, 130, 100)):
    o = GObject(Body(),depth=0)
    o.set_data_value("type", "grass")
    o.set_image_id(f"grass{random.randint(1,3)}")
    o.set_position(position=position)
    o.set_last_change(clock.get_time())
    o.set_shape_color(shape_color)
    ShapeFactory.attach_rectangle(o, width=TILE_SIZE*2, height=TILE_SIZE*2)
    gamectx.add_object(o)


    # o = GObject(Body(),depth=1)
    # o.set_data_value("type", "tree")
    # o.set_image_id(f"tree")
    # o.set_position(position=position)
    # o.set_last_change(clock.get_time())
    # o.set_shape_color(shape_color)
    
    # ShapeFactory.attach_rectangle(o, width=TILE_SIZE*2, height=TILE_SIZE*2)
    # gamectx.add_object(o)

def process_food_collision(player_obj: GObject, food_obj):

    food_energy = food_obj.get_data_value('energy')
    player_energy = player_obj.get_data_value('energy')
    player_obj.set_data_value("energy",
                              player_energy + food_energy)
    # print(f"YAYA FOOD! {player_energy} => {player_energy + food_energy}")
    food_reward_count = player_obj.get_data_value('food_reward_count', 0)
    food_reward_count += 1
    player_obj.set_data_value("food_reward_count", food_reward_count)
    player_obj.set_last_change(clock.get_time())
    food_counter = gamectx.data.get('food_counter', 0)
    gamectx.data['food_counter'] = food_counter - 1

    gamectx.remove_object(food_obj)

    sound_event = SoundEvent(
        sound_id="bleep2")
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

item_types = ['lava', 'food', 'rock', 'player']
item_map = {}
for i, k in enumerate(item_types):
    v = np.zeros(len(item_types)+1)
    v[i] = 1
    item_map[k] = v
default_v = np.zeros(len(item_types)+1)
default_v[len(item_types)] = 1

item_type_count = len(item_types)
vision_distance = 2


class GameContent(Content):

    def __init__(self, config):
        super().__init__(config)
        self.asset_bundle = load_asset_bundle()
        self.space_size = config['space_size']
        self.space_border = config['space_border']
        self.food_energy = config['food_energy']
        self.food_count = config['food_count']
        self.characters = {}

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
        print("Resetting")
        if not self.loaded:
            self.load()
        # gamectx.remove_all_objects()
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


    def spawn_player(self,player):
        print(f"SPWN {player.get_id()}")
        print(f"objid: {player.get_object_id()}")
        if player.get_object_id() is not None:
            character = gamectx.object_manager.get_by_id(player.get_object_id())
        else:
            character= Character(player)
            self.characters[player.get_id()] = character
        
        character.spawn(self.get_new_character_location())
        return character

    def spawn_players(self):
        for player in gamectx.player_manager.players_map.values():
            self.spawn_player(player)

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
        from gym import spaces
        x_dim = (vision_distance * 2 + 1)
        y_dim = x_dim
        chans = len(item_types) + 1
        return spaces.Box(low=0, high=1, shape=(x_dim, y_dim, chans))

    def get_action_space(self):
        from gym import spaces
        return spaces.Discrete(len(self.keymap))

    def get_observation(self, obj: GObject):
        obj_coord = gamectx.physics_engine.vec_to_coord(obj.get_position())
        xvis = vision_distance
        yvis = vision_distance
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
                    row_results.append(item_map.get(obj_seen.get_data_value('type')))
                else:
                    row_results.append(default_v)
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
                        add_rock(coord_to_vec(coord))
                    elif ch == 'x':
                        add_rock(coord_to_vec(coord), type="lava", shape_color=(200, 100, 100))
                    elif ch == 'f':
                        self.food_locations.append(coord)
                    elif ch == 's':
                        self.spawn_locations.append(coord)
                    elif ch == 'g':
                        add_grass(coord_to_vec(coord))
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

    def process_input_event(self, event:InputEvent):
        return input_event_callback(event)


    # **********************************
    # NEW PLAYER
    # **********************************
    def new_player(self, client_id, player_id=None, player_type=0) -> Player:
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
                player_type=player_type)

            gamectx.add_player(player)
        player.set_data_value("view_type", 1)
        if player_type == 10:
            return player
        # print("HERE")
        self.spawn_player(player)
        
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
                # Energy Decay
                if cur_time > o.get_data_value("next_energy_decay", 0):
                    energy = max(0, o.get_data_value("energy") - self.config['player_config']['energy_decay'])
                    o.set_data_value('energy', energy)
                    if energy <= 0:
                        health = o.get_data_value("health") - self.config['player_config']['low_energy_health_penalty']
                        o.set_data_value('health', health)
                    o.set_data_value("next_energy_decay", cur_time + (self.config['player_config']['energy_decay_period'] * self.speed_factor()))

                # Health regen
                if cur_time > o.get_data_value("next_health_gen", 0):
                    health = min(self.config['player_config']['health_max'], o.get_data_value("health") + self.config['player_config']['health_gen'])
                    o.set_data_value('health', health)
                    o.set_data_value("next_health_gen", cur_time + (self.config['player_config']['health_gen_period'] * self.speed_factor()))

                # Stamina regen
                if cur_time > o.get_data_value("next_stamina_gen", 0):
                    stamina = min(self.config['player_config']['stamina_max'], o.get_data_value("stamina") + self.config['player_config']['stamina_gen'])
                    o.set_data_value('stamina', stamina)
                    o.set_data_value("next_stamina_gen", cur_time + (self.config['player_config']['stamina_gen_period'] * self.speed_factor()))

                # Check for death
                if o.get_data_value("health") <= 0:
                    p.set_data_value("allow_input", False)
                    lives_used = p.get_data_value("lives_used", 0)
                    lives_used += 1
                    p.set_data_value("lives_used", lives_used)
                    o.disable()
                    p.set_data_value("reset_required", True)
                else:
                    p.set_data_value("allow_input", True)

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


def input_event_callback(input_event: InputEvent) -> List[Event]:

    player = gamectx.player_manager.get_player(input_event.player_id)
    if not player.get_data_value("allow_input",False):
        return []
    if player is None:
        return []
    if player.get_data_value("view_type") == 0:
        return input_event_callback_fpv(input_event,player)
    else:
        return input_event_callback_3rd(input_event,player)


def input_event_callback_3rd(input_event:InputEvent, player) -> List[Event]:
    
    events= []
    tile_size = gamectx.physics_engine.config.tile_size
    keys = set(input_event.input_data['inputs'])
    cur_tick = clock.get_tick_counter()

    obj = gamectx.object_manager.get_by_id(player.get_object_id())
    if obj is None:
        return events
    
    if not obj.enabled:
        return []
    elif player.get_data_value("reset_required",False):
        print("Episode is over. Reset required")
        return events

    velocity_multiplier = obj.get_data_value('velocity_multiplier')

    # Queued action prevents movement until complete. Trigger at a certain time and releases action lock later but 
    # cur_tick = clock.get_tick_counter()
    if cur_tick < obj.get_data_value("action_completion_time",0):
        return []

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
        def grab_event_fn(event: DelayedEvent, data: Dict[str, Any]):
            print("HNI")
            print(obj)

            obj.set_last_change(cur_tick)
            # new_pos = tile_size * direction + obj.get_position()
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            direction= Vector(0,1).rotated(obj.body.angle)
            print(direction)

            target_pos= obj.get_position() + (direction * tile_size)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
                target_obj = gamectx.object_manager.get_by_id(oid)
                if target_obj.get_data_value("type") =="rock":
                    gamectx.remove_object(target_obj)
            
            obj.set_data_value("action",
                {
                    'type':'grab',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                })
            return []

        event = DelayedEvent(grab_event_fn, 
            execution_step=0, 
            data={})
        events.append(event)

    elif "DROP" in actions_set:
        def event_fn(event: DelayedEvent, data: Dict[str, Any]):

            obj.set_last_change(cur_tick)
            # new_pos = tile_size * direction + obj.get_position()
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            direction= Vector(0,1).rotated(obj.body.angle)
            print(direction)

            target_pos= obj.get_position() + (direction * tile_size)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            oids = gamectx.physics_engine.space.get_objs_at(target_coord)

            if len(oids)==0 or (len(oids)==1 and gamectx.object_manager.get_by_id(oids[0]).get_data_value("type") == 'grass'):
                add_rock(target_pos)
                
            obj.set_data_value("action",
                {
                    'type':'drop',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                })
            return []

        event = DelayedEvent(event_fn, 
            execution_step=0, 
            data={})
        events.append(event)

    elif "ATTACK" in actions_set:
        def event_fn(event: DelayedEvent, data: Dict[str, Any]):
            obj = gamectx.object_manager.get_by_id(data.get("obj_id"))


            obj.set_last_change(cur_tick)
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            direction= Vector(0,1).rotated(obj.body.angle)
            print(direction)

            target_pos= obj.get_position() + (direction * tile_size)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
                obj2 = gamectx.object_manager.get_by_id(oid)
                if obj2.get_data_value("type") == "tree":
                    new_health = obj2.get_data_value("health") -10
                    print(new_health)
                    obj2.set_data_value("health", new_health)
                    if new_health < 30:
                        gamectx.remove_object_by_id(obj2.get_data_value("top_id"))
            
            obj.set_data_value("action",
                {
                    'type':'attack',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                })
            return []
        event = DelayedEvent(event_fn, 
            execution_step=0, 
            data={'obj_id':obj.get_id()})
        events.append(event)
    elif "MOVE" in actions_set:
        def move_event_fn(event: DelayedEvent, data: Dict[str, Any]):
            direction = data['direction']
            angle_update = data['angle_update']
            body:Body = obj.get_body()

            direction = direction * velocity_multiplier
            obj.set_last_change(cur_tick)


            if angle_update is not None and body.angle != angle_update:
                ticks_in_action = 1 * gamectx.content.speed_factor()
                action_complete_time = cur_tick + ticks_in_action
                obj.set_data_value("action_completion_time",action_complete_time/2)
                body.angle = angle_update
                return []

            ticks_in_action = 1 * gamectx.content.speed_factor()
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            new_pos = tile_size * direction + obj.get_position()
            obj.set_data_value("action",
                {
                    'type':'walk',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                    'start_position': body.position,
                    'direction': direction
                })

            obj.update_position(new_pos)

            return []

        event = DelayedEvent(move_event_fn, 
            execution_step=0, 
            data={'direction':direction,'angle_update':angle_update})
        events.append(event)

    return events


def input_event_callback_fpv(input_event: InputEvent, player) -> List[Event]:

    events= []
    tile_size = gamectx.physics_engine.config.tile_size
    keys = set(input_event.input_data['inputs'])

    obj = gamectx.object_manager.get_by_id(player.get_object_id())
    if obj is None:
        return events
    gamectx.content.get_observation(obj)

    rotation_multiplier = obj.get_data_value('rotation_multiplier')
    velocity_multiplier = obj.get_data_value('velocity_multiplier')

    obj_orientation_diff = 0
    if 1 in keys:
        obj_orientation_diff = math.pi/2

    if 4 in keys:
        obj_orientation_diff = -math.pi/2

    # Object Movement
    direction:Vector = Vector.zero()

    if 23 in keys:
        direction = Vector(0, 1)

    if 19 in keys:
        direction = Vector(0, -1)

    if 31 in keys:
        events.append(ViewEvent(player.get_id(), 100))

    if 10 in keys:
        print("Adding admin_event ...TODO!!")

    def move_event_fn(event: DelayedEvent, data: Dict[str, Any]):
        direction = data['direction']
        orientation_diff = obj_orientation_diff * rotation_multiplier
        direction = direction * velocity_multiplier
        obj.set_last_change(clock.get_time())
        body:Body = obj.get_body()
        angle = body.angle
        direction = direction.rotated(angle)
        new_pos = tile_size * direction + body.position
        obj.update_position(new_pos)
        body.angle = angle + orientation_diff
        return []

    movement_event = False
    if movement_event:

        event = DelayedEvent(move_event_fn, execution_step=0, data={'direction':direction})
        events.append(event)

    return events
