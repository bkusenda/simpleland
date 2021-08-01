import math
from simpleland.contentbundles.survival_config import CONTENT_ID
from simpleland.contentbundles.survival_behaviors import FleeAnimals, FollowAnimals, PlayingTag
from simpleland import physics_engine
import random
from collections import defaultdict
from typing import Dict, Any, Tuple

from ..camera import Camera
from ..event import (AdminCommandEvent, DelayedEvent, Event, InputEvent, ObjectEvent,ViewEvent,
                     PeriodicEvent, PositionChangeEvent, SoundEvent)
from ..object import GObject

from ..player import Player
from ..renderer import Renderer
from ..utils import gen_id, getsize, getsizewl

from ..asset_bundle import AssetBundle
from ..common import COLLISION_TYPE
import numpy as np
from ..clock import clock
from typing import List,Dict,Any
from ..event import InputEvent, Event, DelayedEvent
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
from .survival_controllers import FoodCollectController,ObjectCollisionController, PlayerSpawnController, TagController,InfectionController
from .survival_objects import *
from .survival_utils import int_map_to_onehot_map,ints_to_multi_hot
import time

############################
# COLLISION HANDLING
############################
def default_collision_callback(obj1: PhysicalObject, obj2: PhysicalObject):
    return obj1.collision_with(obj2)

class GameContent(SurvivalContent):

    def __init__(self, config):
        super().__init__(config)
        self.asset_bundle = load_asset_bundle(self.config['asset_bundle'])
        self.active_controllers:List[str] = self.config['active_controllers']
        self.map_config = self.config['maps'][self.config['start_map']]
        # TODO, load from game config
        self.default_camera_distance = config['default_camera_distance']
        self.tile_size = self.config['tile_size']

        # Effect Vector Lookup
        self.effect_int_map = {config_id:value.get('obs_id',i) for i, (config_id, value) in enumerate(self.config['effects'].items())}
        self.max_effect_id = len(self.effect_int_map)
        self.effect_vec_map = int_map_to_onehot_map(self.effect_int_map)

        self.tag_list = self.config['tag_list']
        self.max_tags = 10 #Static for now to keep observation space same between configuration, #len(self.tag_list)
        self.tag_int_map = { tag:i for i,tag in enumerate(self.tag_list)}

        # Object Vector Lookup
        self.obj_int_map = {config_id:value.get('obs_id',i) for i, (config_id, value) in enumerate(self.config['objects'].items())}
        self.max_obs_id = len(self.obj_int_map)
        self.obj_vec_map = int_map_to_onehot_map(self.obj_int_map)   
        self.vision_radius = 2 # Vision info should be moved to objects, possibly predifined

        self.player_count = 0
        self.keymap = [23, 19, 4, 1, 5, 6, 18,0, 26,3, 24]

        self.loaded = False
        self.gamemap = GameMap(
            path = self.config.get("game_config_root"),
            map_config=self.map_config,
            tile_size = self.tile_size,
            seed = self.config.get("map_seed",123))
        
        
        # self._default_speed_factor_multiplier = self.config['default_speed_factor_multiplier']
        self._speed_factor_multiplier = self.config['speed_factor_multiplier']
        
        self._ticks_per_step = None
        self.call_counter = 0

        # All loadable classes should be registered
        self.classes = [Action,
            Effect, Human, Monster, Inventory,
            Food,Tool, Animal, Tree, Rock, 
            Liquid, PhysicalObject, TagTool,Camera,
            TagController, 
            PlayerSpawnController,
            ObjectCollisionController,
            FoodCollectController,InfectionController]

        for cls in self.classes:
            gamectx.register_base_class(cls)
        self.obj_class_map= {cls.__name__: cls for cls  in self.classes}
        self.controllers:Dict[str,StateController] = {}

        self.behavior_classes = [FleeAnimals,FollowAnimals,PlayingTag]
        self.bevavior_class_map:Dict[str,Behavior] = {cls.__name__: cls for cls  in self.behavior_classes}

        # Memory Debugging
        self.debug_memory = False
        self.console_report_freq_sec = 4
        self.console_report_last = 0
        self.max_size = {}

    def create_tags_vec(self,tags):
        return ints_to_multi_hot([self.tag_int_map[tag] for tag in tags], self.max_tags)

    def get_game_config(self):
        return self.config

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
        return self.config['effects'].get(config_id,{}).get('model',{})

    def get_object_sprites(self,config_id):
        return self.config['objects'].get(config_id,{}).get('model',{})
    
    def get_object_sounds(self,config_id):
        return self.config['objects'].get(config_id,{}).get('sounds',{})

    def get_available_location(self,max_tries = 200):
        point= None
        tries = 0
        while point is None or tries > max_tries:
            coord = self.gamemap.random_coords(num=1)[0]
            objs = gamectx.physics_engine.space.get_objs_at(coord)
            if len(objs) == 0:
                point = coord_to_vec(coord)
        return point

    # Factory Methods
    def create_behavior(self,name,*args,**kwargs):
        return self.bevavior_class_map[name](*args,**kwargs)

    def create_controller(self,cid):
        info = self.config['controllers'].get(cid)
        if info is None:
            raise Exception(f"{cid} not in game_config['controllers']")
        cls = get_base_cls_by_name(info['class'])
        controller:StateController = cls(cid=cid,config=info['config'])
        return controller

    def create_object_from_config_id(self,config_id):
        info = self.config['objects'].get(config_id)
        if info is None:
            raise Exception(f"{config_id} not defined in game_config['objects']")
        cls = get_base_cls_by_name(info['class'])
        obj:PhysicalObject = cls(config_id=config_id,config=info['config'])
        return obj

    def get_config_from_config_id(self,config_id):
        return self.config['objects'].get(config_id).get('config')

    def ticks_per_step(self):
        if self._ticks_per_step is not None:
            return self._ticks_per_step
        """
        Step size in ticks
        """
        tick_rate = gamectx.tick_rate
        if not tick_rate or tick_rate == 0:
            tick_rate = 1
        self._ticks_per_step = max(tick_rate * self._speed_factor_multiplier,1)
        return self._ticks_per_step

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

    def get_observation(self, obj: GObject):
        return obj.get_observation()

    def get_step_info(self, player: Player, include_state_observation=True) -> Tuple[np.ndarray, float, bool, Dict[str, Any], bool]:
        observation = None
        done = False
        reward = 0
        info = {}
        if player is not None:
            if not player.get_data_value("allow_obs", False):
                return None, None, None, None, True

            obj_id = player.get_object_id()
            obj: AnimateObject = gamectx.object_manager.get_by_id(obj_id)
            if obj is None:
                return None, reward, done, info, True
            if include_state_observation:
                observation = self.get_observation(obj)
            else:
                observation =  None
            done = player.get_data_value("reset_required", False)
            if done:
                player.set_data_value("allow_obs", False)
            reward = obj.reward
            obj.reward = 0
        else:
            info['msg'] = "no player found"
        return observation, reward, done, info, False

    # **********************************
    # NEW PLAYER
    # **********************************
    def new_player(self, client_id, player_id=None, player_type=0, is_human=False) -> Player:
        if player_id is None:
            player_id = gen_id()
        player = gamectx.player_manager.get_player(player_id)
        if player is None:
            cam_distance = self.default_camera_distance
            player = Player(
                client_id=client_id,
                uid=player_id,
                camera=Camera(distance=cam_distance,view_type=1),
                player_type=player_type,
                is_human = is_human)
            gamectx.add_player(player)
            for controller_id in self.active_controllers:
                self.get_controller_by_id(controller_id).join(player)
            # self.get_controller_by_id("pspawn").spawn_player(player,reset=True)


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


    def process_admin_command_event(self,admin_event:AdminCommandEvent):
        print("Admin Ccmmand Event")
        print(admin_event.value)
        events = []
        return events
                

    def process_input_event(self, input_event:InputEvent):
        events= []
        player = gamectx.player_manager.get_player(input_event.player_id)
        if player is None:
            return []
        if not player.get_data_value("allow_input",False):
            return []
        # keydown = input_event.input_data['pressed']
        keydown = input_event.input_data['keydown']
        # keyup = set(input_event.input_data['keyup'])

        # TODO: only check for admin client events if player is human
        mode = player.get_data_value("INPUT_MODE","PLAY")
        
        
        if mode == "CONSOLE":
            return events



        # Client Events
        if 27 in keydown:
            logging.info("QUITTING")
            if mode == "PLAY":
                gamectx.change_game_state("STOPPED")
            else:
                player.set_data_value("INPUT_MODE","PLAY")
            return events
        if 31 in keydown:
            logging.info("Zoom Out")
            events.append(ViewEvent(player.get_id(), 50, Vector2(0,0)))
            
        if 32 in keydown:
            logging.info("Zoom in")
            events.append(ViewEvent(player.get_id(), -50, Vector2(0,0)))

        if 80 in keydown:
            self._speed_factor_multiplier += 0.1
            self._ticks_per_step = None

        if 81 in keydown:
            self._speed_factor_multiplier -= 0.1
            self._ticks_per_step = None

        if 13 in keydown:
            logging.info("MAP")
            player.set_data_value("INPUT_MODE","MAP")

        if 99 in keydown:
            logging.info("CONSOLE")
            player.set_data_value("INPUT_MODE","CONSOLE")
            
        # If client, dont' process any other events
        if gamectx.config.client_only_mode:
            return events

        obj:AnimateObject = gamectx.object_manager.get_by_id(player.get_object_id())

        if obj is None or not obj.enabled:
            return events
        
        elif player.get_data_value("reset_required",False):
            print("Episode is over. Reset required")
            return events

        player = gamectx.player_manager.get_player(input_event.player_id)
        
        if player is None or not player.get_data_value("allow_input",False) or player.get_data_value("reset_required",False):
            return events

        if mode == "PLAY":
            obj.assign_input_event(input_event)     

        return events

    def update(self):
        objs = list(gamectx.object_manager.get_objects().values())
        for o in objs:
            if not o.enabled or o.sleeping:
                continue
            o.update()
        self.update_controllers()


        if self.debug_memory:
            cur_tick = clock.get_exact_time()
            sz = getsize(gamectx.object_manager)  
            if sz > self.max_size.get("om",(0,0))[0]:
                self.max_size['om'] = (sz,cur_tick)

            sz = getsize(gamectx.event_manager)  
            if sz > self.max_size.get("em",(0,0))[0]:
                self.max_size['em'] = (sz,cur_tick)

            sz = getsize(gamectx.physics_engine)  
            if sz > self.max_size.get("ph",(0,0))[0]:
                self.max_size['ph'] = (sz,cur_tick)

            sz = getsize(self.gamemap)  
            if sz > self.max_size.get("map",(0,0))[0]:
                self.max_size['map'] = (sz,cur_tick)

            sz = getsize(self)  
            if sz > self.max_size.get("cnt",(0,0))[0]:
                self.max_size['cnt'] = (sz,cur_tick)


            sz = len(gamectx.object_manager.objects)
            if sz > self.max_size.get("ob_count",(0,0))[0]:
                self.max_size['ob_count'] = (sz,cur_tick)


            if (time.time() - self.console_report_last) > self.console_report_freq_sec:

                logging.info("--")
                for k,v in self.max_size.items():
                    logging.info(f"{k}:".ljust(10)+ f"at:{v[1]}".rjust(15) +f"v:{v[0]}".rjust(15))
                self.console_report_last = time.time()

    def post_process_frame(self, player: Player, renderer: Renderer):
        if player is not None and player.player_type == 0:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))
            lines.append("INPUT_MODE:{}".format(player.get_data_value("INPUT_MODE", 0)))
            lines.append("CONSOLE_COMMAND: {}".format(player.get_data_value("CONSOLE_TEXT", "")))
            lines.append("Game Speed Factor: {}".format(self.ticks_per_step()))

            obj:AnimateObject = gamectx.object_manager.get_by_id(player.get_object_id())
            obj_health = 0
            #TODO: instead render as part of hud via infobox
            if obj is not None:
                obj_health = obj.health
                lines.append(f"Total Reward: {obj.total_reward}")

                lines.append(f"Inventory: {obj.get_inventory().as_string()}")
                lines.append(f"Craft Menu: {obj.get_craftmenu().as_string()}")

                # TODO: make HUD optional/ configurable
                bar_height = round(renderer.resolution[1] /40)
                bar_width_max = round(renderer.resolution[0] /6)
                bar_padding = round(renderer.resolution[1] /200)

                tlheight = renderer.resolution[1] - bar_height - bar_padding
                bar_width = round(obj.stamina/obj.stamina_max * bar_width_max)

                # Stamina
                renderer.draw_rectangle(bar_padding,tlheight, bar_width,bar_height, color=(0,0,200))

                # Energy
                tlheight = tlheight - bar_height - bar_padding
                bar_width = round(obj.energy/obj.energy_max * bar_width_max)
                renderer.draw_rectangle(bar_padding,tlheight, bar_width,bar_height, color=(200,200,0))

                # Health
                tlheight = tlheight - bar_height - bar_padding
                bar_width = round(obj.health/obj.health_max * bar_width_max)
                renderer.draw_rectangle(bar_padding,tlheight, bar_width,bar_height, color=(200,0,0))

                renderer.draw_rectangle(bar_width_max + bar_padding,tlheight, bar_padding/2,renderer.resolution[1] - tlheight - bar_padding, color=(200,200,200))
                


            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)
                if obj_health <= 0:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)