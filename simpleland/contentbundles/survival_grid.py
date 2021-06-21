import math
from simpleland.contentbundles.survival_behaviors import FleeAnimals, FollowAnimals, PlayingTag
from simpleland import physics_engine
import random
from collections import defaultdict
from typing import Dict, Any, Tuple

from ..camera import Camera
from ..event import (DelayedEvent, Event, InputEvent, ObjectEvent,
                     PeriodicEvent, PositionChangeEvent, SoundEvent, ViewEvent)
from ..object import GObject

from ..player import Player
from ..renderer import Renderer
from ..utils import gen_id

from ..asset_bundle import AssetBundle
from ..common import COLLISION_TYPE
import numpy as np
from ..clock import clock
from typing import List,Dict,Any
from ..event import InputEvent, Event, ViewEvent, DelayedEvent
from .. import gamectx
from ..common import  Vector2, get_base_cls_by_name
import pygame
from ..clock import clock
from gym import spaces
import sys
import math

import pkg_resources
import json
import os
from .survival_assets import load_asset_bundle
from .survival_map import GameMap
from .survival_controllers import PlayerSpawnController, TagController
from .survival_objects import *
from .survival_utils import int_map_to_onehot_map,ints_to_multi_hot


############################
# COLLISION HANDLING
############################
def default_collision_callback(obj1: PhysicalObject, obj2: PhysicalObject):
    if ('animate' in obj1.get_types() and obj2.type == "liquid"):
        return obj2.on_collision_with_animate(obj1)
    elif ('liquid' in obj1.get_types() and 'animate' in obj2.get_types()):
        return obj1.on_collision_with_animate(obj2)
    elif 'animate' in obj1.get_types()  and obj2.collision_type >0:
        obj1.on_collection_default(obj2)
        return obj2.collision_type
    
    return obj1.collision_type >0 and obj1.collision_type == obj2.collision_type




def read_json_file(path):
    try:
        full_path = pkg_resources.resource_filename(__name__,path)
        with open(full_path,'r') as f:
            return json.load(f)
    except Exception as e:
        return {}


def read_game_config(sub_dir, game_config):
    game_config = read_json_file(os.path.join(sub_dir,game_config))
    game_config['asset_bundle'] = read_json_file(
            os.path.join(sub_dir,game_config['asset_bundle']))
    for id, obj_data in game_config['controllers'].items():
        if "config" not in obj_data:
            obj_data['config'] = read_json_file(os.path.join(sub_dir,obj_data.get('config',f"{id}_config.json")))
    for id, obj_data in game_config['objects'].items():
        obj_data['config'] = read_json_file(os.path.join(sub_dir,obj_data.get('config',f"{id}_config.json")))
        obj_data['sounds'] = read_json_file(os.path.join(sub_dir,obj_data.get('sounds',f"{id}_sounds.json")))
        obj_data['model'] = read_json_file(os.path.join(sub_dir,obj_data.get('model',f"{id}_model.json")))
    for id, data in game_config['effects'].items():
        data['config'] = read_json_file(os.path.join(sub_dir,data.get('config',f"{id}_config.json")))
        data['sounds'] = read_json_file(os.path.join(sub_dir,data.get('sounds',f"{id}_sounds.json")))
        data['model'] = read_json_file(os.path.join(sub_dir,data.get('model',f"{id}_model.json")))
    return game_config


class GameContent(SurvivalContent):

    def __init__(self, config):
        super().__init__(config)
        self.config_path = 'survival_grid'
        self.game_config = read_game_config(self.config_path,'game_config.json')
        self.asset_bundle = load_asset_bundle(self.game_config['asset_bundle'])
        self.active_controllers:List[str] = self.game_config['active_controllers']
        self.map_config = self.game_config['maps'][self.game_config['start_map']]
        # TODO, load from game config
        self.default_camera_zoom = config['default_camera_zoom']
        self.tile_size = self.game_config['tile_size']

        # Effect Vector Lookup
        self.effect_int_map = {config_id:value.get('obs_id',i) for i, (config_id, value) in enumerate(self.game_config['effects'].items())}
        self.max_effect_id = len(self.effect_int_map)
        self.effect_vec_map = int_map_to_onehot_map(self.effect_int_map)

        self.tag_list = self.game_config['tag_list']
        self.max_tags = 3 #len(self.tag_list)
        self.tag_int_map = { tag:i for i,tag in enumerate(self.tag_list)}

        # Object Vector Lookup
        self.obj_int_map = {config_id:value.get('obs_id',i) for i, (config_id, value) in enumerate(self.game_config['objects'].items())}
        self.max_obs_id = len(self.obj_int_map)
        self.obj_vec_map = int_map_to_onehot_map(self.obj_int_map)   
        self.vision_radius = 2 # Vision info should be moved to objects, possibly predifined

        self.player_count = 0
        self.keymap = [23, 19, 4, 1, 5, 6, 18,0, 26,3, 24]

        self.loaded = False
        self.gamemap = GameMap(
            path = self.config_path,
            map_config=self.map_config)
        self._speed_factor = None
        self.call_counter = 0

        # All loadable classes should be registered
        self.classes = [
            Effect, Human, Monster, Inventory,
            Food,Tool, Animal, Tree, Rock, 
            Liquid, PhysicalObject, TagController, PlayerSpawnController, TagTool]

        for cls in self.classes:
            gamectx.register_base_class(cls)
        self.obj_class_map= {cls.__name__: cls for cls  in self.classes}
        self.controllers:Dict[str,StateController] = {}

        self.behavior_classes = [FleeAnimals,FollowAnimals,PlayingTag]
        self.bevavior_class_map:Dict[str,Behavior] = {cls.__name__: cls for cls  in self.behavior_classes}

    def create_tags_vec(self,tags):
        return ints_to_multi_hot([self.tag_int_map[tag] for tag in tags], self.max_tags)

    def get_game_config(self):
        return self.game_config

    def load_controllers(self):
        self.controllers = {}
        for cid in self.active_controllers:
            self.controllers[cid] = self.create_controller(cid)

    def reset_controllers(self):
        for cid in self.active_controllers:
            self.controllers[cid].reset()

    def update_controllers(self):
        for cid in self.active_controllers:
            self.controllers[cid].update()

    def get_controller_by_id(self, cid):
        return self.controllers.get(cid)

    def get_effect_sprites(self,config_id):
        return self.game_config['effects'].get(config_id,{}).get('model',{})

    def get_object_sprites(self,config_id):
        return self.game_config['objects'].get(config_id,{}).get('model',{})
    
    def get_object_sounds(self,config_id):
        return self.game_config['objects'].get(config_id,{}).get('sounds',{})

    # Factory Methods
    def create_behavior(self,name,*args,**kwargs):
        return self.bevavior_class_map[name](*args,**kwargs)

    def create_controller(self,cid):
        info = self.game_config['controllers'].get(cid)
        if info is None:
            raise Exception(f"{cid} not in game_config['controllers']")
        cls = get_base_cls_by_name(info['class'])
        controller:StateController = cls(cid=cid,config=info['config'])
        return controller

    def create_object_from_config_id(self,config_id):
        info = self.game_config['objects'].get(config_id)
        if info is None:
            raise Exception(f"{config_id} not defined in game_config['objects']")
        cls = get_base_cls_by_name(info['class'])
        obj:PhysicalObject = cls(config_id=config_id,config=info['config'])
        return obj

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

    def request_reset(self):
        for player in gamectx.player_manager.players_map.values():
            player.set_data_value("reset_required", True)

    def reset_required(self):
        for player in gamectx.player_manager.players_map.values():
            if not player.get_data_value("reset_required", True):
                return False
        return True

    # **********************************
    # GAME LOAD
    # **********************************
    def load(self, is_client_only=False):
        self.loaded = False
        if not is_client_only:
            self.gamemap.initialize((0,0))
            self.load_controllers()

        gamectx.physics_engine.set_collision_callback(
            default_collision_callback,
            COLLISION_TYPE['default'],
            COLLISION_TYPE['default'])
        self.loaded = True

    def reset(self):
        if not self.loaded:
            self.load()

        gamectx.remove_all_events()
        self.reset_controllers()


    #####################
    # RL AGENT METHODS
    #####################
    # TODO: get from player to object
    def get_observation_space(self):
        x_dim = (self.vision_radius * 2 + 1)
        y_dim = x_dim
        chans = self.max_obs_id + self.max_tags
        return spaces.Box(low=0, high=1, shape=(x_dim, y_dim, chans))

    # TODO: get from player to object
    def get_action_space(self):
        return spaces.Discrete(len(self.keymap))

    # TODO: get from player to object
    def get_observation(self, obj: GObject):
        return obj.get_observation()

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
            if obj is None:
                return None, reward, done, info
            observation = self.get_observation(obj)
            done = player.get_data_value("reset_required", False)
            if done:
                player.set_data_value("allow_obs", False)
            reward = obj.reward
            obj.reward = 0
        else:
            info['msg'] = "no player found"
        return observation, reward, done, info

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
        return player


    ########################
    # GET INPUT
    ########################

    def process_position_change_event(self,e:PositionChangeEvent):
        if not e.is_player_obj:
            return            
        
        old_scoord = self.gamemap.get_sector_coord_from_pos(e.old_pos)
        new_scoord = self.gamemap.get_sector_coord_from_pos(e.new_pos)
        if old_scoord != new_scoord:
            self.gamemap.load_sectors_near_coord(new_scoord)
                

    def process_input_event(self, input_event:InputEvent):
        events= []
        player = gamectx.player_manager.get_player(input_event.player_id)
        if player is None:
            print("PLAYER IS NON")
            return []
        if not player.get_data_value("allow_input",False):
            return []
        keypressed = set(input_event.input_data['pressed'])
        keydown = set(input_event.input_data['keydown'])
        # keyup = set(input_event.input_data['keyup'])

        obj:AnimateObject = gamectx.object_manager.get_by_id(player.get_object_id())

        # Client Events
        if 27 in keydown:
            print("QUITTING")
            gamectx.change_game_state("STOPPED")
            return events

        # If client, dont' process any other events
        if gamectx.config.client_only_mode:
            return events

        if obj is None or not obj.enabled:
            return events
        
        elif player.get_data_value("reset_required",False):
            print("Episode is over. Reset required")
            return events

        player = gamectx.player_manager.get_player(input_event.player_id)
        
        if player is None or not player.get_data_value("allow_input",False) or player.get_data_value("reset_required",False):
            return events

        obj:AnimateObject = gamectx.object_manager.get_by_id(player.get_object_id())

        if obj is not None and obj.get_action().get('blocking',True):
            return events

        # Object Movement
        actions_set = set()
        direction = Vector2(0,0)
        angle_update = None
        if 23 in keypressed:
            # W UP
            direction = Vector2(0, -1)
            angle_update = 180
            actions_set.add("WALK")

        if 19 in keypressed:
            # S DOWN
            direction = Vector2(0, 1)
            angle_update = 0
            actions_set.add("WALK")

        if 4 in keypressed:
            # D RIGHT
            direction = Vector2(1, 0)
            angle_update = 270
            actions_set.add("WALK")
            
        if 1 in keypressed:
            # A LEFT
            direction = Vector2(-1, 0)
            angle_update = 90
            actions_set.add("WALK")

        # TODO: Establish action presidence
        if 5 in keypressed:
            actions_set.add("GRAB")

        elif 6 in keypressed:
            actions_set.add("DROP")

        elif 18 in keypressed:
            actions_set.add("USE")

        elif 26 in keydown:
            actions_set.add("PREV_ITEM")

        elif 3 in keydown:
            actions_set.add("NEXT_ITEM")

        elif 2 in keydown:
            actions_set.add("NEXT_CRAFT_TYPE")

        elif 22 in keydown:
            actions_set.add("PREV_CRAFT_TYPE")
        
        elif 17 in keydown:
            actions_set.add("CRAFT")

        elif 33 in keypressed:
            actions_set.add("JUMP")

        elif  7 in keypressed:
            actions_set.add("PUSH")

        elif 0 in keypressed:
            actions_set.add("NA")

        if "GRAB" in actions_set:
            obj.grab()
        elif "DROP" in actions_set:
            obj.drop()
        elif "USE" in actions_set:
            obj.use()
        elif "NEXT_ITEM" in actions_set:
            obj.select_item()
        elif "PREV_ITEM" in actions_set:
            obj.select_item(prev=True)
        elif "CRAFT" in actions_set:
            obj.craft()
        elif "NEXT_CRAFT_TYPE" in actions_set:
            obj.select_craft_type()
        elif "PREV_CRAFT_TYPE" in actions_set:
            obj.select_craft_type(prev=True)
        elif "PUSH" in actions_set:
            obj.push()
        elif "JUMP" in actions_set:
            obj.jump()
        elif "WALK" in actions_set:
            # obj.walk(direction,angle_update)
            events.append(ObjectEvent(
                obj.get_id(),
                "walk",
                direction,
                angle_update))

        return events

    def update(self):
        objs = list(gamectx.object_manager.get_objects().values())
        for o in objs:
            if not o.enabled or o.sleeping:
                continue
            o.update()
        self.update_controllers()

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

                lines.append(f"H:{obj_health}, E:{obj_energy}, S:{obj_stamina}")
                lines.append(f"Inventory: {obj.inventory().as_string()}")
                lines.append(f"Craft Menu: {obj.craftmenu().as_string()}")

            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)
                if obj_health <= 0:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)