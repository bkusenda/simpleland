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
from .input_callbacks import input_event_callback
from ..common import COLLISION_TYPE
import numpy as np
from ..config import GameDef, PhysicsConfig



test_map = (
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
#############
# Game Defs #
#############
def game_def():
    game_def = GameDef(
        content_id = "space1",
        content_config={
            'space_size':800,
            'player_start_energy':35,
            'player_energy_decay_ticks':1,
            'food_energy':5,
            'food_count':1,
            'asteroid_count':0,
            'num_feelers':8,
            'feeler_length':200,
            "space_border" : 200,
            "block_size":80
            })
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

def reset_sensor_data(obj: GObject):
    sensor_lookup = obj.get_data_value("sensor_lookup")
    obj.set_data_value("sensor_types", [0 for i in range(len(sensor_lookup))])
    obj.set_data_value("sensor_dists", [None for i in range(len(sensor_lookup))])

def get_random_pos():
    return Vector(
        random.random() * gamectx.content.config['space_size'],
        random.random() * gamectx.content.config['space_size'])


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



def add_block(position, type="wall", shape_color=(100, 100, 100)):
    o = GObject(Body())
    o.set_data_value("type", type)
    o.set_data_value("image",type)
    o.set_position(position=position)
    o.set_last_change(gamectx.clock.get_time())
    o.shape_color = shape_color

    ShapeFactory.attach_rectangle(o,width=80,height=80)
    gamectx.add_object(o)



def add_asteroid():
    o = GObject(Body(mass=50, moment=0), depth=0)
    o.set_position(position=get_random_pos())
    o.set_data_value("energy", 100)
    o.set_data_value("type", "asteroid")
    o.set_data_value("image", "asteroid2")
    o.set_last_change(gamectx.clock.get_time())

    o.get_body().angle = random.random() * 360
    # ShapeFactory.attach_rectangle(o, 2, 2)
    #ShapeFactory.attach_poly(o, size=10,num_sides=40)
    ShapeFactory.attach_circle(o, 100)

    gamectx.add_object(o)


def add_player_ship(player:Player):
    player_object = GObject(Body(mass=2, moment=0))
    player_object.set_data_value("rotation_multiplier", 1)
    player_object.set_data_value("velocity_multiplier", 1)
    player_object.set_data_value("is_kinematic", False)


    player_object.set_data_value("type", "player")
    player_object.set_data_value("image", "1")
    player_object.set_data_value("player_id", player.get_id())
    ShapeFactory.attach_circle(player_object, radius=40)

    # ShapeFactory.attach_line_array(player_object,
    #                                length=gamectx.content.feeler_length,
    #                                num=gamectx.content.num_feelers,
    #                                thickness=1,
    #                                collision_type=COLLISION_TYPE['sensor'])
    player.attach_object(player_object)
    gamectx.add_object(player_object)
    # TODO, filter non sensor objects
    sensor_lookup = {shape.get_id(): i for i, shape in enumerate([s for s in player_object.get_shapes() if s.collision_type == COLLISION_TYPE["sensor"]])}
    player_object.set_data_value('sensor_lookup', sensor_lookup)
    reset_sensor_data(player_object)
    return player_object


def process_food_collision(player_obj,food_obj):
    food_energy = food_obj.get_data_value('energy')
    player_energy = player_obj.get_data_value('energy')
    player_obj.set_data_value("energy",
                              player_energy + food_energy)
    food_count = player_obj.get_data_value('food_count', 0)
    player_obj.set_data_value("food_count",
                              food_count + 1)
    player_obj.set_last_change(gamectx.clock.get_time())
    food_counter = gamectx.data.get('food_counter', 0)
    gamectx.data['food_counter'] = food_counter - 1
    gamectx.remove_object(food_obj)
    sound_event = SoundEvent(
        creation_time=gamectx.clock.get_time(),
        sound_id="bleep2")

    # respawn food
    def food_event_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
        add_food(food_obj.get_position())
        return []
    new_food_event = DelayedEvent(food_event_callback, execution_step=6)
    gamectx.event_manager.add_event(new_food_event)
    gamectx.event_manager.add_event(sound_event)
    return False


def process_sensor_collision(sensor_info, obj_info):
    s = sensor_info['shape']
    sensor_pos: Vector = sensor_info['obj'].get_position()
    obj_pos: Vector = obj_info['obj'].get_position()
    distance = sensor_pos.get_distance(obj_pos)
    sensor_lookup = sensor_info['obj'].get_data_value('sensor_lookup')
    idx = sensor_lookup[s.get_id()]

    # Set sensor dists
    sensor_dists = sensor_info['obj'].get_data_value('sensor_dists')
    if sensor_dists[idx] is None or distance < sensor_dists[idx]:
        sensor_dists[idx] = distance
    else:
        return False
    sensor_info['obj'].set_data_value('sensor_dists', sensor_dists)

    sensor_types = sensor_info['obj'].get_data_value('sensor_types')
    objtype = obj_info['obj'].get_data_value('type')
    if objtype == "food":
        sensor_types[idx] = 1
    else:
        sensor_types[idx] = 2
    sensor_info['obj'].set_data_value('sensor_types', sensor_types)
    return False

def process_lava_collision(player_obj,lava_obj):
    player_obj.set_data_value("energy",0)
    return False


# TODO, move to standard event callback


def default_collision_callback(obj1:GObject,obj2:GObject):

    if obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "food":
        return process_food_collision(obj1, obj2)
    elif obj1.get_data_value('type') == "player" and obj2.get_data_value('type') == "lava":
        return process_lava_collision(obj1, obj2)

    return True


def sensor_collision_callback(obj1:GObject,obj2:GObject):
    print("Sensor collision")


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
        self.num_feelers = config['num_feelers']
        self.feeler_length = config['feeler_length']

        self.spawn_locations = []

    def _initialize(self):
        gamectx.remove_all_objects()
        gamectx.remove_all_events()
        gamectx.reset_data()

    def get_asset_bundle(self):
        return self.asset_bundle

    def get_observation(self, obj: GObject):
        vals = obj.get_data_value('sensor_types') + obj.get_data_value('sensor_dists')
        b = obj.get_body()
        velocity: Vec2d = b.velocity
        angular_velocity = b.angular_velocity
        vals = [10000 if val is None else val for val in vals] + [velocity.x, velocity.y, angular_velocity]
        return np.array(vals)

    def get_observation_space(self):
        from gym.spaces import Box
        num = self.num_feelers * 2 + 3
        return Box(low=-float("inf"), high=float("inf"), shape=(num,))

    def get_step_info(self, player: Player) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        observation = None
        done = False
        reward = 0
        info = {}
        if player is not None:
            obj_id = player.get_object_id()
            obj = gamectx.object_manager.get_latest_by_id(obj_id)
            observation = self.get_observation(obj)

            if obj is not None:
                energy = obj.get_data_value("energy")
                info['energy'] = energy
                if energy <= 0:
                    done = True
                elif energy <= 5:
                    reward = 1
                else:
                    reward = 1
            else:
                info['msg'] = "no player obj"
                done = True

            if done:
                reward = 1
        else:
            info['msg'] = "no player found"
        return observation, reward, done, info

    def new_player(self,  player_id=None, player_type=0) -> Player:
        # Create Player
        if player_id is None:
            player_id = gen_id()
        player = gamectx.player_manager.get_player(player_id)
        if player is None:
            cam_distance = self.space_size + self.space_border
            if player_type == 10:
                cam_distance = self.space_size + self.space_border
            player = Player(
                uid=player_id,
                camera=Camera(distance=cam_distance),
                player_type=player_type)
            gamectx.add_player(player)

        if player_type == 10:
            return player

        player_object = gamectx.object_manager.get_latest_by_id(player.get_object_id())
        if player_object is None:
            add_player_ship(player)
            player_object = gamectx.object_manager.get_latest_by_id(player.get_object_id())
        
        self.spawn_player(player_object)

        def event_callback(event: PeriodicEvent, data: Dict[str, Any], om: GObjectManager):
            obj = om.get_latest_by_id(data['obj_id'])
            if obj is None or obj.is_deleted:
                return [], True
            new_energy = max(obj.get_data_value("energy") - 1, 0)
            obj.set_data_value('energy', new_energy)
            obj.set_last_change(gamectx.clock.get_time())
            return [], False

        decay_event = PeriodicEvent(
            event_callback,
            execution_step_interval=self.player_energy_decay_ticks,
            data={'obj_id': player_object.get_id()})

        gamectx.event_manager.add_event(decay_event)
        return player

    def spawn_player(self,player_object:GObject):
        loc = random.choice(self.spawn_locations)
        player_object.set_position(position=coord_to_vec(loc))
        player_object.set_data_value("energy", gamectx.content.player_start_energy)



    # **********************************
    # GAME LOAD
    # **********************************

    def load(self):
        self._initialize()

        lines = test_map.split("\n")
        items=[]
        self.spawn_locations=[]
        for ridx,line in enumerate(lines):
            for cidx,ch in enumerate(line):
                if ch == 'b':
                    add_block(coord_to_vec((cidx,ridx)))
                elif ch == 'x':
                    add_block(coord_to_vec((cidx,ridx)),type="lava",shape_color=(200,100,100))
                elif ch == 'f':
                    add_food(coord_to_vec((cidx,ridx)))
                elif ch == 's':
                    self.spawn_locations.append((cidx,ridx))

                    #items.append(('food',(ridx,cidx)))
        

        # # # Create some Asteroids
        # # for i in range(self.asteroid_count):
        # #     add_asteroid()

        # # Add food
        # for i in range(self.food_count):
        #     add_food()

        gamectx.physics_engine.set_collision_callback(
            default_collision_callback,
            COLLISION_TYPE['default'],
            COLLISION_TYPE['default'])

        gamectx.physics_engine.set_collision_callback(
            sensor_collision_callback,
            COLLISION_TYPE['sensor'],
            COLLISION_TYPE['default'])

        def pre_physics_callback():
            new_events = []
            for k, p in gamectx.player_manager.players_map.items():
                if p.get_object_id() is None:
                    continue

                o = gamectx.object_manager.get_latest_by_id(p.get_object_id())

               
                if o is None or o.is_deleted or not o.enabled:
                    continue
                reset_sensor_data(o)
                if o.get_data_value("energy") <= 0:
                    
                    lives_used = p.get_data_value("lives_used", 0)
                    p.set_data_value("lives_used", lives_used+1)
                    o.disable()
                    

                    # Delete and create event
                    def event_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
                        o.enable()
                        self.spawn_player(o)
                        return []

                    new_ship_event = DelayedEvent(
                        func=event_callback,
                        execution_step=1,
                        data={'player_id': p.get_id()})

                    new_events.append(new_ship_event)

            return new_events

        gamectx.set_pre_physics_callback(pre_physics_callback)
        gamectx.set_input_event_callback(input_event_callback)

    def post_process_frame(self, render_time, player: Player, renderer: Renderer):
        if player is not None and player.player_type == 0:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))

            obj = gamectx.object_manager.get_by_id(player.get_object_id(), render_time)
            if obj is not None:
                lines.append("Current Energy: {}".format(obj.get_data_value("energy", 0)))
                lines.append("Current Velocity: {}".format(obj.get_body()._get_velocity()))
                lines.append("Current Angular Vel: {}".format(obj.get_body()._get_angular_velocity()))
                lines.append("Observation: {}".format(self.get_observation(obj)[:8]))

            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)

                if obj is None:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)
