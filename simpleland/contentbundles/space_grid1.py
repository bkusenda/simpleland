from simpleland import physics_engine
import random
from typing import Dict, Any, Tuple

import pymunk
from pymunk import contact_point_set
from pymunk.vec2d import Vec2d

from ..common import (SimClock, Body, Camera, Circle, Clock, Line,
                      Polygon, Shape, Space, Vector,
                      TimeLoggingContainer)
from ..event import (DelayedEvent, Event,
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
from .input_callbacks_grid1 import input_event_callback
from ..common import COLLISION_TYPE
import numpy as np
from ..config import GameDef, PhysicsConfig



test_map_b1 = (
    f"xxxxxxxxxxxxxxxxxxxxxxxx\n"
    f"x                 bbbbbx\n"
    f"x                  s  bx\n"
    f"x     f               bx\n"
    f"x                     bx\n"
    f"x    b                bx\n"
    f"x    bbb               x\n"
    f"x f            f       x\n"
    f"x            xxx  f    x\n"
    f"x       f              x\n"
    f"x                      x\n"
    f"x          b           x\n"
    f"x       f  b           x\n"
    f"x       bbbbb          x\n"
    f"x          b    f      x\n"
    f"x                      x\n"
    f"xb                     x\n"
    f"xb                     x\n"
    f"xbs                    x\n"
    f"xbbb                   x\n"
    f"xxxxxxxxxxxxxxxxxxxxxxxx\n"
)


test_map_b2 = (
    f"xxxxxxxxxxxxxxxxx\n"
    f"x  f   f   bbbbbx\n"
    f"x           s  bx\n"
    f"x     f   f    bx\n"
    f"x  f           bx\n"
    f"xbs     f       x\n"
    f"xbbb        f   x\n"
    f"xxxxxxxxxxxxxxxxx\n"
)

test_map = (
    f"bbbbbbbbbbbbbbbbb\n"
    f"b  f   f   bbbbbb\n"
    f"b           s  bb\n"
    f"b     f   f    bb\n"
    f"b  f           bb\n"
    f"bbs     f       b\n"
    f"bbbb        f   b\n"
    f"bbbbbbbbbbbbbbbbb\n"
)


test_map = (
    f"bbbbbbbbbbbbbbbbb\n"
    f"b  f   f   bbbbbb\n"
    f"b           s  bb\n"
    f"b     x   f    bb\n"
    f"b  f           bb\n"
    f"b     f   f    bb\n"
    f"b  f           bb\n"
    f"b     f   f    bb\n"
    f"b  f           bb\n"
    f"b     f   f    bb\n"
    f"b  f           bb\n"
    f"b     f   f    bb\n"
    f"b  f           bb\n"
    f"bbs     f       b\n"
    f"bbbb        f   b\n"
    f"bbbbbbbbbbbbbbbbb\n"
)





# test_map = (
#     f"bbbbbbbbbbbbbbbbb\n"
#     f"b x             b\n"
#     f"b s         f  xb\n"
#     f"bbbbbbbbbbbbbbbbb\n"
# )

# test_map = (
#     f"s   f\n"
# )
############
# Game Defs #
#############
def game_def(content_overrides = {}):

    content_config={
        'space_size':800,
        'player_start_energy':20,
        'player_energy_decay_ticks':1,
        'food_energy':5,
        'food_count':1,
        'asteroid_count':0,
        "space_border" : 200,
        "block_size":80
        }
    content_config.update(content_overrides)

    game_def = GameDef(
        content_id = "space_grid1",
        content_config = content_config
    )
    game_def.physics_config.grid_size = 80
    game_def.physics_config.engine = "grid"
    game_def.game_config.wait_for_user_input=True
    return game_def

def load_asset_bundle():
    image_assets = {}
    image_assets['1'] = 'assets/redfighter0006.png'
    image_assets['1_thrust'] = 'assets/redfighter0006_thrust.png'

    image_assets['2'] = 'assets/ship2.png'
    image_assets['energy1'] = 'assets/energy1.png'
    image_assets['asteroid2'] = 'assets/asteroid1.png'
    image_assets['lava'] = 'assets/lava1.png'

    sound_assets = {}
    sound_assets['bleep2'] = 'assets/sounds/bleep2.wav'
    return AssetBundle(image_assets=image_assets, sound_assets=sound_assets)


def vec_to_coord(v):
    block_size = gamectx.content.config['block_size']
    return (int(v.x / block_size),int(v.y / block_size))

def coord_to_vec(coord):
    block_size = gamectx.content.config['block_size']
    return Vector(float(coord[0] * block_size),float(coord[1] * block_size))

def add_food(position):
    o = GObject(Body())
    o.set_data_value("energy", gamectx.content.config['food_energy'])
    o.set_data_value("type", "food")
    o.set_data_value("image", "energy1")
    o.set_position(position=position)
    o.set_last_change(gamectx.clock.get_time())

    ShapeFactory.attach_circle(o, radius=50)
    gamectx.add_object(o)
    gamectx.data['food_counter'] = gamectx.data.get('food_counter', 0) + 1

def add_block(position, type="block", shape_color=(100, 100, 100)):
    o = GObject(Body())
    o.set_data_value("type", type)
    o.set_data_value("image",type)
    o.set_position(position=position)
    o.set_last_change(gamectx.clock.get_time())
    o.shape_color = shape_color
    ShapeFactory.attach_rectangle(o,width=80,height=80)
    gamectx.add_object(o)

def add_player_ship(player:Player,position:Vector):
    player_object = GObject(Body(mass=2, moment=0))
    player_object.set_data_value("rotation_multiplier", 1)
    player_object.set_data_value("velocity_multiplier", 1)

    player_object.set_data_value("type", "player")
    player_object.set_data_value("image", "1")
    player_object.set_data_value("player_id", player.get_id())
    player_object.set_position(position=position)
    ShapeFactory.attach_circle(player_object, radius=40)

    player.attach_object(player_object)
    gamectx.add_object(player_object)
    return player_object

def energy_decay_callback(event: PeriodicEvent, data: Dict[str, Any], om: GObjectManager):
    obj = om.get_latest_by_id(data['obj_id'])
    if obj is None or obj.is_deleted:
        return [], True

    new_energy = max(obj.get_data_value("energy") - 1, 0)
    obj.set_data_value('energy', new_energy)
    obj.set_last_change(gamectx.clock.get_time())
    return [], False

def spawn_player(player:Player, reset = False):
    player_object = gamectx.object_manager.get_latest_by_id(player.get_object_id())
    loc = random.choice(gamectx.content.spawn_locations)
    position = coord_to_vec(loc)
    if player_object is None:
        add_player_ship(player,position=position)
        player_object = gamectx.object_manager.get_latest_by_id(player.get_object_id())
    else:
        player_object.update_position(position=position)

    player_object.set_data_value("energy",  gamectx.content.player_start_energy)
    player.set_data_value("allow_input",False)
    if reset:
        player.set_data_value("lives_used",0)
        player.set_data_value("food_reward_count",0)
        player.set_data_value("episode_over",False)
        player.events = []
        player_object.enable()
        decay_event = PeriodicEvent(
            energy_decay_callback,
            execution_step_interval=gamectx.content.player_energy_decay_ticks,
            data={'obj_id': player_object.get_id()})
        gamectx.event_manager.add_event(decay_event)
            
    return player_object


def process_food_collision(player_obj:GObject,food_obj):
    food_energy = food_obj.get_data_value('energy')
    player_energy = player_obj.get_data_value('energy')
    player_obj.set_data_value("energy",
                              player_energy + food_energy)
    food_reward_count = player_obj.get_data_value('food_reward_count', 0)
    food_reward_count +=1
    player_obj.set_data_value("food_reward_count",food_reward_count)
    player_obj.set_last_change(gamectx.clock.get_time())
    food_counter = gamectx.data.get('food_counter', 0)
    gamectx.data['food_counter'] = food_counter - 1
    gamectx.remove_object(food_obj)
    # player_id = player_obj.get_data_value("player_id")
    # player = gamectx.player_manager.get_player(player_id)
    # player_obj.disable()
    # player.set_data_value("episode_over",True)



    # respawn food
    # def food_event_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
    #     # if gamectx.physics_engine.space.food_obj.get_position()
    #     obj_ids = gamectx.physics_engine.space.get_objs_at(gamectx.physics_engine.vec_to_coord(food_obj.get_position()))
    #     # if len(obj_ids)>0:
    #     #     return [DelayedEvent(food_event_callback, execution_step=random.randint(10,16))]
    #     # else:
    #     add_food(food_obj.get_position())
    #     return []
    # new_food_event = DelayedEvent(food_event_callback, execution_step=random.randint(10,16))
    # gamectx.event_manager.add_event(new_food_event)

    sound_event = SoundEvent(
        creation_time=gamectx.clock.get_time(),
        sound_id="bleep2")
    gamectx.event_manager.add_event(sound_event)
    return False


def process_lava_collision(player_obj,lava_obj):
    player_obj.set_data_value("energy",0)
    return False


def default_collision_callback(obj1:GObject,obj2:GObject):
    if obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "food":
        return process_food_collision(obj1, obj2)
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "lava":
        return process_lava_collision(obj1, obj2)
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "block":
        return True
    return False

##########################
#pre_event_callback
##########################
def post_physics_callback():
    new_events = []
    for k, p in gamectx.player_manager.players_map.items():
        if p.get_object_id() is None:
            continue

        o = gamectx.object_manager.get_latest_by_id(p.get_object_id())
        

        if o is None or o.is_deleted or not o.enabled:
            continue

        if o.get_data_value("energy") <= 0:
            p.set_data_value("allow_input",False)
            
            lives_used = p.get_data_value("lives_used", 0)
            lives_used+=1
            p.set_data_value("lives_used", lives_used)
            o.disable()
            # if lives_used<=3:
            #     def respawn_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
            #         o.enable()
            #         spawn_player(p)
            #         return []
            #     respawn_event = DelayedEvent(
            #         func=respawn_callback,
            #         execution_step=0,
            #         data={'player_id': p.get_id()})
            #     new_events.append(respawn_event)
            # else:
            p.set_data_value("episode_over",True)
        else:
            p.set_data_value("allow_input",True)
    

    return new_events


def pre_physics_callback():
    
    return []

item_types = ['lava','food','block','player']
item_map = {}
for i,k in enumerate(item_types):
    v = np.zeros(len(item_types)+1)
    v[i] =1
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
        self.player_start_energy = config['player_start_energy']
        self.player_energy_decay_ticks = config['player_energy_decay_ticks']
        self.food_energy = config['food_energy']
        self.food_count = config['food_count']
        self.asteroid_count = config['asteroid_count']
        
        self.player_count=0
        self.keymap = [23,19,4,1]


        self.spawn_locations = []
        self.food_locations = []
        self.loaded = False

    def get_asset_bundle(self):
        return self.asset_bundle
    
    def reset(self):
        if not self.loaded:
            self.load()
        #gamectx.remove_all_objects()
        gamectx.remove_all_events()
        
        def food_event_callback(event: PeriodicEvent, data: Dict[str, Any], om: GObjectManager):
            self.spawn_food(limit=1)
            return [],True
        new_food_event = PeriodicEvent(food_event_callback, execution_step_interval=random.randint(10,16))
        gamectx.event_manager.add_event(new_food_event)

        self.spawn_food()
        self.spawn_players()


    def spawn_players(self):
        for player in gamectx.player_manager.players_map.values():
            spawn_player(player,reset=True)

    def spawn_food(self,limit = None):
        # Spawn food
        spawn_count = 0
        for i, coord in enumerate(self.food_locations):
            if len(gamectx.physics_engine.space.get_objs_at(coord))==0:
                add_food(coord_to_vec(coord))
                spawn_count+=1
                if limit is not None and spawn_count >= limit:
                    return

    
    def get_observation_space(self):
        from gym import spaces
        x_dim = (vision_distance * 2 + 1)
        y_dim = x_dim
        chans = len(item_types) +1
        return spaces.Box(low=0, high=1, shape=(x_dim,y_dim,chans))

    def get_action_space(self):
        from gym import spaces
        return spaces.Discrete(len(self.keymap))

    def get_observation(self, obj: GObject):
        obj_coord = gamectx.physics_engine.vec_to_coord(obj.get_position())
        xvis = vision_distance
        yvis = vision_distance
        col_min =  obj_coord[0] - xvis
        col_max =  obj_coord[0] + xvis
        row_min =  obj_coord[1] - yvis
        row_max =  obj_coord[1] + yvis
        results = []
        for r in range(row_max, row_min-1,-1):
            row_results = []
            for c in range(col_min,col_max+1):
                obj_ids = gamectx.physics_engine.space.get_objs_at((c,r))
                if len(obj_ids)>0:
                    obj_id = obj_ids[0]
                    obj_seen = gamectx.object_manager.get_latest_by_id(obj_id)
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
            obj_id = player.get_object_id()
            obj = gamectx.object_manager.get_latest_by_id(obj_id)
            observation = self.get_observation(obj)
            done = player.get_data_value("episode_over",False)
            info['lives_used'] = player.get_data_value("lives_used")
            energy = obj.get_data_value("energy")
            info['energy'] = energy

            # Claim food rewards
            food_reward_count = obj.get_data_value("food_reward_count",0)
            obj.set_data_value("food_reward_count",0)
            reward = food_reward_count
            # if energy == 0:
            #     reward += -1
            if done:
                reward = -5                
        else:
            info['msg'] = "no player found"
        return observation, reward, done, info


    # **********************************
    # GAME LOAD
    # **********************************
    def load(self):

        lines = test_map.split("\n")

        self.spawn_locations=[]
        for ridx,line in enumerate(lines):
            for cidx,ch in enumerate(line):
                coord = (cidx,ridx)
                if ch == 'b':
                    add_block(coord_to_vec(coord))
                elif ch == 'x':
                    add_block(coord_to_vec(coord),type="lava",shape_color=(200,100,100))
                elif ch == 'f':
                    self.food_locations.append(coord)
                elif ch == 's':
                    self.spawn_locations.append(coord)
                
        gamectx.physics_engine.set_collision_callback(
            default_collision_callback,
            COLLISION_TYPE['default'],
            COLLISION_TYPE['default'])

        gamectx.set_pre_physics_callback(pre_physics_callback)
        gamectx.set_input_event_callback(input_event_callback)
        gamectx.set_post_physics_callback(post_physics_callback)
        self.loaded=True


    # **********************************
    # NEW PLAYER
    # **********************************
    def new_player(self, client_id, player_id=None, player_type=0) -> Player:
        if self.player_count > len(self.spawn_locations):
            raise Exception("Players cannot exceed spawn locations")
        # Create Player
        if player_id is None:
            player_id = gen_id()
        player = gamectx.player_manager.get_player(player_id)
        if player is None:
            cam_distance = self.space_size + self.space_border
            if player_type == 10:
                cam_distance = self.space_size + self.space_border
            player = Player(
                client_id = client_id,
                uid=player_id,
                camera=Camera(distance=cam_distance),
                player_type=player_type)
            
            gamectx.add_player(player)
        player.set_data_value("view_type",1)
        if player_type == 10:
            return player
        player_object = spawn_player(player,reset=True)
        return player


    # **********************************
    # Additional Rendering
    # **********************************
    def post_process_frame(self, render_time, player: Player, renderer: Renderer):
        if player is not None and player.player_type == 0:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))

            obj = gamectx.object_manager.get_by_id(player.get_object_id(), render_time)
            obj_energy = 0
            if obj is not None:
                obj_energy = obj.get_data_value("energy", "NA")
                lines.append("Current Energy: {}".format(obj_energy))
                lines.append("Current Velocity: {}".format(obj.get_body()._get_velocity()))
                lines.append("Current Angular Vel: {}".format(obj.get_body()._get_angular_velocity()))
                lines.append("Observation: {}".format(self.get_observation(obj)[:8]))

            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)
                if obj_energy == 0:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)
