from ..asset_bundle import AssetBundle
import math
import random

from typing import List
from .. import gamectx
from ..clock import clock
from ..common import (Vector)


from ..itemfactory import ShapeFactory
from ..object import GObject

from ..player import Player
from ..event import (DelayedEvent)
from .survival_config import TILE_SIZE
from .survival_utils import coord_to_vec
import numpy as np
from gym import spaces
import os
import pkg_resources
from ..event import SoundEvent
import hashlib


def rand_int_from_coord(x,y,seed=123):
    v =  (x + y * seed ) % 12783723
    h = hashlib.sha1()
    h.update(str.encode(f"{v}"))
    return int(h.hexdigest(),16) % 172837

def get_tile_image_id(x,y,seed):
    v = rand_int_from_coord(x,y,seed) % 3 + 1
    return f"grass{v}"


class TileMap:

    def __init__(self,seed = 123):
        self.seed = seed

    def get_layers(self):
        return range(2)
        
    def get_by_loc(self,x,y, layer_id):
        if layer_id == 0:
            return get_tile_image_id(x,y,self.seed)
        
        loc_id = rand_int_from_coord(x,y,self.seed)
        if x ==0 and y==0:
            return "baby_tree"
        if x ==2 and y==3:
            return "baby_tree"
        return None
    

class TileMapLoader:

    def __init__(self):
        self.tilemap = None
    
    def get_tilemap(self,name):
        if self.tilemap is None:
            self.tilemap = gamectx.content.tilemap
        return self.tilemap

def load_asset_bundle(asset_bundle):

    return AssetBundle(
        image_assets=asset_bundle['images'],
        sound_assets=asset_bundle['sounds'],
        music_assets=asset_bundle['music'],
        tilemaploader = TileMapLoader())


def angle_to_direction(angle):
    angle_num = angle/math.pi
    direction = "down"
    if angle_num < 0.25 and angle_num >= -0.25:
        direction = "down"
    elif angle_num > 0.25 and angle_num <= 0.75:
        direction = "left"
    elif angle_num < -0.25 and angle_num >= -0.75:
        direction = "right"
    elif abs(angle_num) >= 0.75:
        direction = "up"
    return direction


type_tree={
    'physical_object': None,
    'plant': 'physical_object',
    'tree': 'plant',
    'bush':'plant',
    'monster': 'animal',
    'human': 'animal',
    'deer': 'animal',
    'rock': 'physical_object',
}

def get_types(cur_type):
    all_types = set()
    done = False
    while not done:
        all_types.add(cur_type)
        new_type = type_tree.get(cur_type)
        if new_type is None:
            break
        else:
            cur_type = new_type
    return all_types

class PhysicalObject(GObject):


    def __init__(self,config_id="",config={}, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.config = config
        self.type = "physical_object"
        self._types = None
        self.image_id_default = None
        self.health = 50
        self.created_tick = 0
        self.animated = True
        self.breakable = True
        self.pushable = True
        self.collision_type = 1
        self.collectable = False
        
        self.__sprites = None
        self.__sounds = None

        # Can it be placed in inventory?
        self.default_action_type = "idle"
        self._action = {}
        self.config_id = config_id

        self.default_action()
        self.disable()
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)

        

    def get_sprites(self):
        if self.__sprites is None:
            model = gamectx.content.get_object_sprites(self.config_id)
            if "body" in model:
                self.__sprites =  gamectx.content.get_object_sprites(self.config_id)['body']
            else:
                self.__sprites = model.get("default",{})
        return self.__sprites

    def play_sound(self,name):
        if self.__sounds is None:
            self.__sounds = gamectx.content.get_object_sounds(self.config_id)
        sound_id = self.__sounds.get(name)
        if sound_id is not None:
            gamectx.add_event(SoundEvent(sound_id=sound_id,position=self.get_view_position()))

    def spawn(self,position):
        gamectx.content.add_object(self)

        self._action = {
            'type': 'spawn',
            'ticks':1,
            'step_size':1,
            'start_tick': clock.get_tick_counter(),
            'blocking':True
        }
        self.health = 50
        self.created_tick = clock.get_tick_counter()
        self.enable()
        self.set_position(position=position)
        self.play_sound("spawn")

    def get_types(self):
        if self._types is None:
            self._types = get_types(self.type)
        return self._types

    def get_action(self):
        cur_tick = clock.get_tick_counter()
        if not self._action.get('continuous',False)  and (cur_tick - self._action.get('start_tick',0) > self._action.get('ticks',1)):
            self.default_action()
        return self._action

    def default_action(self):
        ticks_in_action = 3 * gamectx.content.speed_factor()
        self._action = {
            'type': 'idle',
            'ticks':ticks_in_action,
            'step_size':TILE_SIZE/ticks_in_action,
            'start_tick': clock.get_tick_counter(),
            'blocking':False,
            'continuous':True

        }

    def get_image_id(self, angle=0):
        action = self.get_action()
        sprites = self.get_sprites().get(action['type'])
        if sprites is None:
            sprites = self.get_sprites().get(self.default_action_type)
        if sprites is None:
            return self.image_id_default

        direction = angle_to_direction(self.angle)

        cur_tick = clock.get_tick_counter()
        # TODO: Need to account for game speed
        action_idx = (cur_tick - action['start_tick'])
        total_sprite_images = len(sprites[direction])
        sprite_idx = int((action_idx/action['ticks']) * total_sprite_images)  % total_sprite_images
        return sprites[direction][sprite_idx]

    def get_view_position(self):
        cur_tick = clock.get_tick_counter()
        action = self.get_action()
        if action.get('start_position') is not None:
            idx = cur_tick - action['start_tick']
            # if idx > 0:
            direction = (self.position - action['start_position']).normalized()
            view_position = action['step_size'] * idx * direction + action['start_position']
            return view_position
        return self.get_position()

    def move(self, direction, new_angle, move_speed = 1):
        
        direction = direction * 1
        if new_angle is not None and self.angle != new_angle:
            ticks_in_action = gamectx.content.speed_factor()/move_speed
            self.angle = new_angle
            return []
        ticks_in_action = move_speed * gamectx.content.speed_factor()

        new_pos = TILE_SIZE * direction + self.get_position()
        self._action = \
            {
                'type': 'move',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
                'start_position': self.position,
                'blocking':True
            }

        self.update_position(new_pos)
        self.play_sound("move")



    def receive_damage(self, attacker_obj, damage):
        self.health -= damage
        self.play_sound("receive_damage")


    def receive_push(self,pusher_obj,power, direction):
        if not self.pushable or not self.collision_type:
            return
        self.move(direction,None)
        self.play_sound("receive_push")

    def destroy(self):
        if self.breakable:
            gamectx.content.remove_object(self)


class AnimateObject(PhysicalObject):


    def __init__(self,player:Player= None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "animate"
        self.player_id=None
        if player is not None:
            self.set_player(player)

        self.rotation_multiplier = 1
        self.velocity_multiplier = 1
        self.walk_speed = 1/3

        self.attack_strength = 1
        self.energy = 100
        self.stamina = 100

        self.next_energy_decay = 0
        self.next_health_gen = 0
        self.next_stamina_gen = 0
        self.attack_speed = .3

        self.reward = 0

        # Visual Range in x and y direction
        self.vision_radius =  self.config.get('vision_radius',2)

        # TODO:
        self.inventory = {}
        self.inventory_capacity = 1
        self.inventory_slots = 1
        self.selected_item = None


    def spawn(self,position:Vector):
        super().spawn(position)
        self.energy = self.config.get('energy_start',100)
        self.health = self.config.get('health_start',100)
        self.stamina = self.config.get('stamina_max',100)
        self.attack_speed = self.config.get('attack_speed',0.3)
        self.walk_speed = self.config.get('walk_speed',0.3)
        self.next_energy_decay = 0
        self.next_health_gen = 0
        self.next_stamina_gen =0

    # TODO: not in use
    def get_observation_space(self):
        x_dim = (gamectx.content.vision_distance * 2 + 1)
        y_dim = x_dim
        chans = len(gamectx.content.item_types) + 1
        return spaces.Box(low=0, high=1, shape=(x_dim, y_dim, chans))

    # TODO: not in use
    def get_observation(self):
        obj_coord = gamectx.physics_engine.vec_to_coord(self.get_position())
        vrad = self.vision_radius
        
        col_min = obj_coord[0] - vrad
        col_max = obj_coord[0] + vrad
        row_min = obj_coord[1] - vrad
        row_max = obj_coord[1] + vrad
        results = []
        for r in range(row_max, row_min-1, -1):
            row_results = []
            for c in range(col_min, col_max+1):
                obj_ids = gamectx.physics_engine.space.get_objs_at((c, r))
                if len(obj_ids) > 0:
                    obj_id = obj_ids[0]
                    obj_seen = gamectx.object_manager.get_by_id(obj_id)
                    row_results.append(gamectx.content.item_map.get(obj_seen.get_data_value('type')))
                else:
                    row_results.append(gamectx.content.default_v)
            results.append(row_results)
        return np.array(results)

    def set_player(self,player:Player):
        self.player_id = player.get_id()
        if player is not None:
            player.attach_object(self)

    def get_player(self)->Player:
        if self.player_id is None:
            return None
        else:
            return gamectx.player_manager.get_player(self.player_id)

    def get_visible_objects(self) -> List[PhysicalObject]:
        obj_coord = gamectx.physics_engine.vec_to_coord(self.get_position())

        col_min = obj_coord[0] - self.vision_radius
        col_max = obj_coord[0] + self.vision_radius
        row_min = obj_coord[1] - self.vision_radius
        row_max = obj_coord[1] + self.vision_radius
        obj_list = []
        for r in range(row_max, row_min-1, -1):
            for c in range(col_min, col_max+1):
                obj_ids = gamectx.physics_engine.space.get_objs_at((c, r))
                for obj_id in obj_ids:
                    obj_seen = gamectx.object_manager.get_by_id(obj_id)
                    if obj_seen.is_visible() and obj_seen.is_enabled():
                        obj_list.append(obj_seen)

        return obj_list

    def get_item_amount(self, name):
        return self.inventory.get(name,0)

    def modify_inventory(self, name, count):
        self.inventory[name] = self.get_item_amount(name) + count

    def receive_push(self,*args,**kwargs):
        super().receive_push(*args,**kwargs)
        self.stunned()

    def consume_food(self,food_obj:PhysicalObject):
        self.energy += food_obj.energy
        food_obj.destroy()
        self.play_sound("eat")

    def walk(self, direction, new_angle):
        walk_speed = self.walk_speed
        if self.stamina <= 0:
            walk_speed = walk_speed/2
        else:
            self.stamina -= 0

        direction = direction * self.velocity_multiplier
        self.angle = new_angle
            
        ticks_in_action = gamectx.content.speed_factor()/walk_speed
        new_pos = TILE_SIZE * direction + self.get_position()
        self._action = \
            {
                'type': 'walk',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
                'start_position': self.position,
                'blocking':True
            }     

        self.update_position(new_pos, callback = lambda suc: self.play_sound('walk') if suc else None )

    def grab(self):

        ticks_in_action = int(gamectx.content.speed_factor())

        direction = Vector(0, 1).rotated(self.angle).normalized()

        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        grab_successful = False
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            target_obj:PhysicalObject = gamectx.object_manager.get_by_id(oid)
            if target_obj.collectable:
                gamectx.remove_object(target_obj)
                self.modify_inventory(target_obj.type, 1)
                grab_successful = True
        if grab_successful:
            self.play_sound("grab")

        self._action = \
            {
                'type': 'grab',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action
            }
        

    def stunned(self):
        ticks_in_action = int(gamectx.content.speed_factor())  * 10 
        self._action = \
            {
                'type': 'stunned',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }
        self.play_sound("stunned")

    def drop(self):
        ticks_in_action = int(gamectx.content.speed_factor())

        direction = Vector(0, 1).rotated(self.angle)

        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        oids = gamectx.physics_engine.space.get_objs_at(target_coord)

        if len(oids) == 0 or (len(oids) == 1 and gamectx.object_manager.get_by_id(oids[0]).type == 'grass'):
            if self.get_item_amount("rock") > 0:
                Rock().spawn(target_pos)
                self.modify_inventory("rock", -1)

        self._action = \
            {
                'type': 'drop',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }
        self.play_sound("drop")
        

    def attack(self):
        attack_speed = self.attack_speed

        if self.stamina <= 0:
            attack_speed = attack_speed/2
        else:
            self.stamina -= 15

        ticks_in_action = round(gamectx.content.speed_factor()/attack_speed)
        direction = Vector(0, 1).rotated(self.angle)
        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)

        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            obj2: PhysicalObject = gamectx.object_manager.get_by_id(oid)
            if obj2.collision_type > 0:
                obj2.receive_damage(self, self.attack_strength)

        gamectx.add_event(SoundEvent(sound_id="hit1"))

        self._action =\
            {
                'type': 'attack',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }
        self.play_sound("attack")

    def push(self):
        attack_speed = self.attack_speed

        if self.stamina <= 0:
            attack_speed = attack_speed/2
        else:
            self.stamina -= 15

        ticks_in_action = round(gamectx.content.speed_factor()/attack_speed)
        direction = Vector(0, 1).rotated(self.angle)
        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)

        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            obj2: PhysicalObject = gamectx.object_manager.get_by_id(oid)
            obj2.receive_push(self, self.attack_strength,direction)

        self._action =\
            {
                'type': 'push',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }
        self.play_sound("push")

    def update(self):

        cur_time = clock.get_time()
        self.set_last_change(cur_time)
        if cur_time > self.next_energy_decay:
            self.energy = max(0, self.energy - self.config.get('energy_decay',0))
            if self.energy <= 0:
                self.health -=  self.config.get('low_energy_health_penalty',0)
                
            self.next_energy_decay =  cur_time + (self.config.get('energy_decay_period',0) * gamectx.content.speed_factor())

        # Health regen
        if cur_time > self.next_health_gen:
            self.health = min(self.config.get('health_max',100), self.health + self.config.get('health_gen',0))
            self.next_health_gen = cur_time + (self.config.get('health_gen_period',0) * gamectx.content.speed_factor())

        # Stamina regen
        if cur_time > self.next_stamina_gen and self.stamina < self.config.get('stamina_max',50):
            self.stamina = min(self.config.get('stamina_max',10), self.stamina + self.config.get('stamina_gen',5))
            gen_delay = (self.config.get('stamina_gen_period',0) * gamectx.content.speed_factor())
            self.next_stamina_gen = cur_time + gen_delay

        if self.breakable and self.health <= 0:
            self.destroy()
        

    def destroy(self):
        if self.get_player() is not None:
            self.disable()
        else:
            super().destroy()
        self.play_sound("destroy")


class Human(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "human"
        self.set_image_id("player_idle_down_1")
        self.next_energy_decay = 10
        self.next_health_gen = 0
        self.attack_strength = 10
        self.health =  40
        self.config_id = "human1"
      

    def update(self):
        super().update()

        p = self.get_player()

        # Check for death
        if self.health <= 0:
            lives_used = p.get_data_value("lives_used", 0)
            lives_used += 1
            p.set_data_value("lives_used", lives_used)
            p.set_data_value("allow_input", False)
            self.disable()

            def event_fn(event: DelayedEvent, data):
                p.set_data_value("reset_required", True)
                return []
            delay = 10*gamectx.content.speed_factor()
            event = DelayedEvent(event_fn, delay)
            gamectx.add_event(event)

        else:
            p.set_data_value("allow_input", True)


class Monster(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "monster"
        self.attack_strength = 10
        self.health =  40
        self.config_id = "monster1"

    def get_sprites(self):
        return gamectx.content.get_object_sprites(self.config_id).get('body',{})

    def update(self):
        super().update()
        if self.get_action().get('blocking',True):
            return

        # TODO: Actions should be processed as event
        for obj in self.get_visible_objects():
            if obj.type != self.type and 'animal' in obj.get_types():
                orig_direction: Vector = obj.get_position() - self.get_position()
                direction = orig_direction.normalized()
                updated_x = 0
                updated_y = 0
                if abs(direction.x) > abs(direction.y):
                    updated_y = 0
                    if direction.x > 0.5:
                        updated_x = 1.0
                    elif direction.x < -0.5:
                        updated_x = -1.0
                    else:
                        updated_x = 0
                else:
                    updated_x = 0
                    if direction.y >= 0.5:
                        updated_y = 1.0
                    elif direction.y < -0.5:
                        updated_y = -1.0
                    else:
                        updated_y = 0
                new_angle = Vector(0, 1).get_angle_between(direction)
                if orig_direction.length <= gamectx.content.tile_size:
                    direction = Vector(0, 0)
                else:
                    direction = Vector(updated_x, updated_y)
                if orig_direction.length <= gamectx.content.tile_size and new_angle == self.angle:
                    self.attack()
                else:
                    self.walk(direction, new_angle)



class Deer(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "deer"
        self.set_image_id("deer")
        self.attack_strength = 3
        self.health =  100


    def update(self):
        super().update()
        if self.get_action().get('blocking',True):
            return

        # TODO: Actions should be processed as event
        for obj in self.get_visible_objects():
            if  obj.type != self.type and 'animal' in obj.get_types():
                orig_direction: Vector = obj.get_position() - self.get_position()
                direction = orig_direction.normalized()
                updated_x = 0
                updated_y = 0
                if abs(direction.x) > abs(direction.y):
                    updated_y = 0
                    if direction.x > 0.5:
                        updated_x = 1.0
                    elif direction.x < -0.5:
                        updated_x = -1.0
                    else:
                        updated_x = 0
                else:
                    updated_x = 0
                    if direction.y >= 0.5:
                        updated_y = 1.0
                    elif direction.y < -0.5:
                        updated_y = -1.0
                    else:
                        updated_y = 0
                new_angle = Vector(0, 1).get_angle_between(direction)
                direction = Vector(-updated_x, -updated_y)
                self.walk(direction, new_angle)


class Tree(PhysicalObject):


    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        
        self.type="tree"
        self.health =  100
        self.set_visiblity(False)
        self.pushable = False
        self.top_id = None
        self.trunk_id = None
        self.fruit_ids = []

    def spawn(self,position):
        super().spawn(position=position)
        self.add_tree_trunk()
        self.add_tree_top()
        for i in range(0,random.randint(0,3)):
            self.add_fruit()

    def add_tree_trunk(self):
        o = PhysicalObject(depth=1)
        o.type = "part"
        o.pushable = False
        o.collision_type = 0
        o.set_image_id(f"tree_trunk")
        o.spawn(position=self.get_position())
        
        self.trunk_id = o.get_id()

    def add_fruit(self):
        o = PhysicalObject(depth=3)
        o.type = "part"
        o.pushable = False
        o.collision_type = 0
        o.set_image_id(f"food")
        y = random.random() * gamectx.content.tile_size*1.8
        x = random.random()* gamectx.content.tile_size - gamectx.content.tile_size/2
        o.set_image_offset(Vector(x,y))
        o.spawn(position=self.get_position())
        self.fruit_ids.append(o.get_id())


    def add_tree_top(self):
        o = PhysicalObject(depth=3)
        o.type = "part"
        o.set_image_id(f"tree_top")
        o.pushable = False
        o.set_image_offset(Vector(0, gamectx.content.tile_size*1.4))
        o.collision_type = 0
        o.spawn(position=self.get_position())        
        self.top_id = o.get_id()
    
    def get_trunk(self)->PhysicalObject:
        return gamectx.object_manager.get_by_id(self.trunk_id)
        
    def get_top(self)->PhysicalObject:
        return gamectx.object_manager.get_by_id(self.top_id)

    def receive_damage(self, attacker_obj, damage):
        super().receive_damage(attacker_obj, damage)
        if self.health <20:
            gamectx.content.remove_object_by_id(self.top_id)
            for fruit_id in self.fruit_ids:
                gamectx.content.remove_object_by_id(fruit_id)
            self.fruit_ids = []
        if self.health <=0:
            gamectx.content.remove_object_by_id(self.trunk_id)
            gamectx.content.remove_object(self)
            Wood().spawn(self.position)
            
        
        
class Wood(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type = "wood"
        self.set_image_id('wood')
        self.collectable = True
        self.collision = True
        self.breakable = True
        self.pushable = False
        self.set_shape_color(color=(200, 200, 50))

    def spawn(self,position):
        super().spawn(position=position)

class Food(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'food'
        self.set_image_id('food')
        self.set_shape_color(color=(100, 130, 100))
        self.energy = gamectx.content.config['food_energy']
        self.collision = True
        self.collectable = True
        self.breakable = True
        
    def spawn(self,position):
        super().spawn(position=position)

class Rock(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'rock'
        self.collectable = True
        self.set_image_id('rock')
        self.set_shape_color(color=(100, 130, 100))
        self.breakable=False


class Water(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 0
        self.type =  'water'
        self.set_shape_color(color=(30, 30, 150))
        self.breakable=False
        self.collision = False



class WorldMap:

    def __init__(self,path,map_config):
        full_path = pkg_resources.resource_filename(__name__,path)
        map_layers = []
        for layer_filename in map_config['layers']:
            with open(os.path.join(full_path,layer_filename),'r') as f:
                layer = f.readlines()
                map_layers.append(layer)            
        
        keys = set(map_config['index'].keys())
        for i, lines in enumerate(map_layers):
            self.spawn_locations = []
            for ridx, line in enumerate(lines):
                linel = len(line)
                for cidx in range(0,linel,2):
                    key = line[cidx:cidx+2]
                    coord = (cidx//2, ridx)
                    if key in keys:
                        info = map_config['index'].get(key)
                        config_id = info['obj']
                        if info.get('type') == "spawn_point":
                            gamectx.content.add_spawn_point(config_id,coord_to_vec(coord))
                        else:
                            object_config = gamectx.content.game_config['objects'].get(config_id)
                            cls = gamectx.content.get_class_by_type_name(object_config['obj_class'])
                            obj:PhysicalObject = cls(config_id=config_id,config=object_config)
                            obj.spawn(position=coord_to_vec(coord))
                            