import math
from simpleland import physics_engine
import random
from typing import Dict, Any, Tuple

from ..camera import Camera
from ..event import (DelayedEvent, Event, InputEvent,
                     PeriodicEvent, PositionChangeEvent, SoundEvent, ViewEvent)
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
from ..common import  Vector2, get_base_cls_by_name
import pygame
from ..clock import clock
from gym import spaces
import sys
import math
from .survival_assets import *
from .survival_utils import *
import pkg_resources
import json
import os

############################
# COLLISION HANDLING
############################
def default_collision_callback(obj1: PhysicalObject, obj2: PhysicalObject):
    if ('animate' in obj1.get_types() and obj2.type == "liquid"):
        return obj2.on_collision_with_animate(obj1)
    elif ('liquid' in obj1.get_types() and 'animate' in obj2.get_types()):
        return obj1.on_collision_with_animate(obj2)
    elif 'animate' in obj1.get_types()  and obj2.collision_type >0:
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


class GameContent(Content):

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

        self.item_types = ['tree', 'food', 'rock', 'player', 'wood']
        self.item_map = get_item_map(self.item_types)
        self.default_v = np.zeros(len(self.item_types)+1)
        self.default_v[len(self.item_types)] = 1

        self.item_type_count = len(self.item_types)
        self.vision_distance = 2

        self.player_count = 0
        self.keymap = [23, 19, 4, 1, 5, 6, 18,0, 26,3, 24]

        self.spawn_locations = []
        self.food_locations = []
        self.loaded = False
        self.gamemap = GameMap(
            path = self.config_path,
            map_config=self.map_config)
        self._speed_factor = None
        self.call_counter = 0
        self.spawn_points = {}

        # All loadable classes should be registered
        self.classes = [
            Effect, Human, Monster, Inventory,
            Food,Tool, Animal, Tree, Rock, 
            Liquid, PhysicalObject, TagController]

        for cls in self.classes:
            gamectx.register_base_class(cls)

        self.obj_class_map= {cls.__name__: cls for cls  in self.classes}
        self.controllers:Dict[str,StateController] = {}

    def load_controllers(self):
        self.controllers = {}
        for config_id in self.active_controllers:
            self.controllers[config_id] = self.create_controller_from_config_id(config_id)

    def reset_controllers(self):
        for config_id in self.active_controllers:
            self.controllers[config_id].reset()

    def update_controllers(self):
        for config_id in self.active_controllers:
            self.controllers[config_id].update()

    def add_spawn_point(self,config_id, pos):
        pos_list = self.get_spawn_points(config_id)
        pos_list.append(pos)
        self.spawn_points[config_id] = pos_list

    def get_spawn_points(self,config_id):
        return self.spawn_points.get(config_id,[])

    def get_effect_sprites(self,config_id):
        return self.game_config['effects'].get(config_id,{}).get('model',{})

    def get_object_sprites(self,config_id):
        return self.game_config['objects'].get(config_id,{}).get('model',{})
    
    def get_object_sounds(self,config_id):
        return self.game_config['objects'].get(config_id,{}).get('sounds',{})

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
        self.spawn_players()
        self.reset_controllers()


    #####################
    # RL AGENT METHODS
    #####################
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
        if obj is None or not obj.is_enabled():
            return None
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
                    if obj_seen is None:
                        print("ERROR cannot find object {}".format(obj_seen))
                    else:   
                        row_results.append(gamectx.content.item_map.get(obj_seen.type))
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
            if obj is None:
                return None, reward, done, info
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
    def spawn_objects(self):
        #TOOD: make configurable
        config_id = 'monster1'
        objs = gamectx.object_manager.get_objects_by_config_id(config_id)
        spawn_points = self.get_spawn_points(config_id)
        if len(objs) < 1 and len(spawn_points)>0:
            object_config = gamectx.content.game_config['objects'][config_id]['config']
            Monster(config_id = config_id, config=object_config).spawn(spawn_points[0])


    def spawn_player(self,player:Player, reset=False):
        if player.get_object_id() is not None:
            player_object = gamectx.object_manager.get_by_id(player.get_object_id())
        else:
            # TODO: get playertype from game mode + client config

            player_config = self.game_config['player_types']['1']
            config_id = player_config['config_id']
            spawn_points = self.get_spawn_points(config_id)
            player.set_data_value("spawn_point",spawn_points[0])
            player_object:PhysicalObject = self.create_object_from_config_id(config_id)
            player_object.set_player(player)

        if reset:
            self.reset_player(player)

        spawn_point = player.get_data_value("spawn_point")

        player_object.spawn(spawn_point)
        return player_object

    def spawn_players(self,reset=True):
        for player in gamectx.player_manager.players_map.values():
            self.spawn_player(player,reset)

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
            direction = Vector2(0, -1)
            angle_update = math.pi
            actions_set.add("WALK")

        if 19 in keypressed:
            direction = Vector2(0, 1)
            angle_update = 0
            actions_set.add("WALK")

        if 4 in keypressed:
            direction = Vector2(1, 0)
            angle_update = -math.pi/2
            actions_set.add("WALK")
            
        if 1 in keypressed:
            direction = Vector2(-1, 0)
            angle_update = math.pi/2
            actions_set.add("WALK")

        # TODO: Establish action presidence
        if 5 in keypressed:
            actions_set.add("GRAB")

        if 6 in keypressed:
            actions_set.add("DROP")

        if 18 in keypressed:
            actions_set.add("USE")

        if 26 in keydown:
            actions_set.add("PREV_ITEM")

        if 3 in keydown:
            actions_set.add("NEXT_ITEM")

        if 2 in keydown:
            actions_set.add("NEXT_CRAFT_TYPE")

        if 22 in keydown:
            actions_set.add("PREV_CRAFT_TYPE")
        
        if 17 in keydown:
            actions_set.add("CRAFT")

        if 33 in keypressed:
            actions_set.add("JUMP")

        if  7 in keypressed:
            actions_set.add("PUSH")

        if 0 in keypressed:
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
            obj.walk(direction,angle_update)

        return events

    def update(self):
        objs = list(gamectx.object_manager.get_objects().values())
        for o in objs:
            if o is None or o.is_deleted or not o.enabled:
                continue
            if o.is_enabled():
                o.update()
        self.spawn_objects()
        self.update_controllers()


    def create_controller_from_config_id(self,config_id):
        info = gamectx.content.game_config['controllers'].get(config_id)
        if info is None:
            raise Exception(f"{config_id} not defined in game_config['objects']")
        cls = get_base_cls_by_name(info['class'])
        controller:StateController = cls(config_id=config_id,config=info['config'])
        return controller

    def create_object_from_config_id(self,config_id):
        info = gamectx.content.game_config['objects'].get(config_id)
        if info is None:
            raise Exception(f"{config_id} not defined in game_config['objects']")
        cls = get_base_cls_by_name(info['class'])
        obj:PhysicalObject = cls(config_id=config_id,config=info['config'])
        return obj

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