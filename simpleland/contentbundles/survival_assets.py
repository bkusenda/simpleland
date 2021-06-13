from ..asset_bundle import AssetBundle
import math
import random

from typing import List, Dict
from .. import gamectx
from ..clock import clock
from ..common import Vector2


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
import logging
from ..common import Base

class GameMapLoader:

    def __init__(self):
        self.gamemap = None
    
    def get(self,name):
        if self.gamemap is None:
            self.gamemap = gamectx.content.gamemap
        return self.gamemap

def load_asset_bundle(asset_bundle):

    return AssetBundle(
        image_assets=asset_bundle['images'],
        sound_assets=asset_bundle['sounds'],
        music_assets=asset_bundle['music'],
        maploader = GameMapLoader())


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


def direction_to_angle(direction):
    angle_num = 0
    if direction == "down":
        angle_num = 0
    elif direction == "left":
        angle_num = 0.50
    elif direction == "right":
        angle_num = -0.5
    elif direction == "up":
        angle_num =1
    return angle_num * math.pi


type_tree={
    'physical_object': None,
    'plant': 'physical_object',
    'tree': 'plant',
    'bush':'plant',
    'animal':'animate',
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

class Behavior:

    def __init__(self):
        pass

    def on_update(self,obj):
        pass

class FollowAnimals(Behavior):
    
    def on_update(self,obj):
        for obj2 in obj.get_visible_objects():
            if obj.config_id != obj2.config_id and 'animal' in obj2.get_types():
                orig_direction: Vector2 = obj2.get_position() - obj.get_position()
                direction = orig_direction.normalize()
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
                new_angle = math.radians(Vector2(0, 1).angle_to(direction))
                mag = orig_direction.magnitude()
                if mag <= gamectx.content.tile_size:
                    direction = Vector2(0, 0)
                else:
                    direction = Vector2(updated_x, updated_y)
                if mag <= gamectx.content.tile_size and new_angle == obj.angle:
                    obj.use()
                else:
                    obj.walk(direction, new_angle)

class FleeAnimals(Behavior):
    
    def on_update(self,obj):
        for obj2 in obj.get_visible_objects():
            if  obj.config_id != obj2.config_id and 'animal' in obj2.get_types():
                orig_direction: Vector2 = obj2.get_position() - obj.get_position()
                direction = orig_direction.normalize()
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
                new_angle = math.radians(Vector2(0, 1).angle_to(direction))
                direction = Vector2(-updated_x, -updated_y)
                obj.walk(direction, new_angle)   


class Action:
    def __init__(self):
        pass

# TODO: Effects as objects
class Effect(Base):

    def __init__(self,config_id="",ticks=1,step_size=1,angle_step_size=0):
        self.config_id = config_id
        self.ticks = ticks
        self.step_size = step_size
        self.start_tick = clock.get_tick_counter()
        self.angle_step_size= angle_step_size

class StateController(Base):

    def __init__(self,config_id="",config={},*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.config_id = config_id
        self.config = config

    def reset(self):
        pass

    def update(self):
        pass


# class PlayerSpawnController(StateController):


#     def reset(self):
#         pass


#     def spawn_player(self,player:Player, reset=False):
#         if player.get_object_id() is not None:
#             player_object = gamectx.object_manager.get_by_id(player.get_object_id())
#         else:
#             # TODO: get playertype from game mode + client config

#             player_config = self.game_config['player_types']['1']
#             config_id = player_config['config_id']
#             spawn_points = self.get_spawn_points(config_id)
#             player.set_data_value("spawn_point",spawn_points[0])
#             player_object:PhysicalObject = self.create_object_from_config_id(config_id)
#             player_object.set_player(player)

#         if reset:
#             self.reset_player(player)

#         spawn_point = player.get_data_value("spawn_point")

#         player_object.spawn(spawn_point)
#         return player_object

#     def spawn_players(self,reset=True):
#         for player in gamectx.player_manager.players_map.values():
#             self.spawn_player(player,reset)


class TagController(StateController):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        print("Tag Controller Created")

    def reset(self):
        player_objs:List[AnimateObject] = []
        for player in gamectx.player_manager.players_map.values():
            p_obj = gamectx.object_manager.get_by_id(player.get_object_id())
            if p_obj is not None:
                player_objs.append(p_obj)
        # "tag_tool":1
        obj = player_objs[0]
        tag_tool:Tool = gamectx.content.create_object_from_config_id("tag_tool")
        tag_tool.spawn(Vector2(0,0))
        tag_tool.disable()
        obj.inventory().add(tag_tool)
        print("Adding tag tool")
    
    def update(self):
        pass

class PhysicalObject(GObject):


    def __init__(self,config_id="",config={}, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.config = config
        self.config_id = config_id
        
   
        self.type = "physical_object"
        self._types = None
        self.image_id_default = None
        self.health = self.config.get('health_start',100)
        self.permanent = self.config.get('permanent',False)
        self.remove_on_destroy = self.config.get('remove_on_destroy',True)
        self.pushable = self.config.get('pushable',False)
        self.collision_type = self.config.get('collision_type',1)
        self.height = self.config.get('height',1)

        self.collectable = self.config.get('collectable',False)
        self.count_max = self.config.get('count_max',1)
        self.count = self.config.get('count',1)
        
        self._l_model = None
        self._l_sounds = None

        self.default_action_type = self.config.get('default_action_type','idle')
        self._action = {}
        self._effects:Dict[str,Effect] = {}

        self._l_event_log = []
        self.view_position = None

        self.default_action()
        self.disable()
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)

    def log_event(self,event):
        self._l_event_log.append(event)

    def get_event_log(self):
        return self._l_event_log

    def clear_event_log(self):
        self._l_event_log = []

    def add_effect(self,effect:Effect):
        self._effects[effect.config_id] = effect
    
    def remove_effect(self,config_id):
        if config_id in self._effects:
            del self._effects[config_id]
        

    def get_effect_sprites(self,effect_config_id):
        return gamectx.content.get_effect_sprites(effect_config_id).get('default')

    def get_effect_renderables(self):
        effects = self.get_effects()
        renderables = []
        for name, effect in effects.items():
            sprites = self.get_effect_sprites(effect.config_id)
            cur_tick = clock.get_tick_counter()
            idx = cur_tick - effect.start_tick
            total_sprite_images = len(sprites)
            sprite_idx = int((idx/effect.ticks) * total_sprite_images)  % total_sprite_images
            angle = effect.angle_step_size * idx 
            renderables.append({'position':Vector2(0,0), 'image_id': sprites[sprite_idx], 'angle':angle})
        return renderables

    def get_sprites(self,action,angle):
        if self._l_model is None:
            self._l_model =  gamectx.content.get_object_sprites(self.config_id)
        
        action_sprite = self._l_model.get(action)
        if action_sprite is None:
            action_sprite = self._l_model.get(self.default_action_type)
            if action_sprite is None:
                return self._l_model.get('default',[self.image_id_default])
        direction = angle_to_direction(angle)
        return action_sprite[direction]

    def get_action_renderables(self, angle=0):
        action = self.get_action()
        sprites = self.get_sprites(action['type'],self.angle)
        if sprites is None or len(sprites) ==0:
            return None
        cur_tick = clock.get_tick_counter()
        action_idx = (cur_tick - action['start_tick'])
        total_sprite_images = len(sprites)
        sprite_idx = int((action_idx/action['ticks']) * total_sprite_images)  % total_sprite_images
        return [{'position':Vector2(0,0), 'image_id': sprites[sprite_idx], 'angle':0}]

    def get_renderables(self, angle=0):
        action_renderables = self.get_action_renderables(angle)
        effect_renderables = self.get_effect_renderables()
        return action_renderables + effect_renderables

    def play_sound(self,name):
        if self._l_sounds is None:
            self._l_sounds = gamectx.content.get_object_sounds(self.config_id)
        sound_id = self._l_sounds.get(name)
        if sound_id is not None:
            gamectx.add_event(SoundEvent(sound_id=sound_id,
                position=self.get_view_position()))

    def spawn(self,position):
        gamectx.add_object(self)
        self.set_image_offset(Vector2(0,0))
        
        self._action = {
            'type': 'spawn',
            'ticks':1,
            'step_size':1,
            'start_tick': clock.get_tick_counter(),
            'blocking':True
        }
        self.health = 50

        self.enable()
        self.update_position(position=position,skip_collision_check=True)
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

    def get_effects(self):
        return self._effects

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

    def update_view_position(self):
        cur_tick = clock.get_tick_counter()
        action = self.get_action()
        if cur_tick >= action['start_tick'] and action.get('start_position') is not None and self.position is not None:
            idx = cur_tick - action['start_tick']
            direction = (self.position - action['start_position'])
            if direction.magnitude() != 0:
                direction = direction.normalize()
            new_view_position = action['step_size'] * idx * direction + action['start_position']
        else:
            new_view_position = self.get_position()
        if new_view_position != self.view_position:
            self.view_position = new_view_position
            self.mark_updated()


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
        
        if not self.permanent:
            self.health -= damage
        self.play_sound("receive_damage")

    def receive_push(self,pusher_obj,power, direction):
        if not self.pushable or not self.collision_type:
            return
        self.move(direction,None)
        self.play_sound("receive_push")
    
    def receive_grab(self,actor_obj):
        if self.collectable:
            return self
        else:
            return None

    def update(self):
        self.update_view_position()
        if self.health <= 0:
            self.destroy()

    def destroy(self):
        if self.remove_on_destroy:
            for child_id in self.child_object_ids:
                gamectx.remove_object_by_id(child_id)
            gamectx.remove_object(self)
        else:
            self.disable()
        self.play_sound("destroy")


class Inventory(PhysicalObject):

    def __init__(self,start_inventory={},*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.slots = 10
        self.items = []
        for i in range(0,self.slots - len(self.items)):
            self.items.append(None)
        for i, (config_id, item_count) in enumerate(start_inventory.items()):
            obj:PhysicalObject = gamectx.content.create_object_from_config_id(config_id)
            obj.spawn(Vector2(0,0))
            obj.count = item_count
            obj.disable()
            self.add(obj)

        self.selected_slot = 0

    def get_selected(self):
        return gamectx.get_object_by_id(self.items[self.selected_slot])

    def select_item(self,prev=False):
        if prev:
            if self.selected_slot ==0:
                self.selected_slot = self.slots -1
            else:
                self.selected_slot-=1
                
        else:
            if self.selected_slot == self.slots +1:
                self.selected_slot=0
            else:
                self.selected_slot+=1
                self.selected_slot = self.selected_slot % self.slots

    def get_objects(self)->List[PhysicalObject]:
        objs = []
        for i, inv_obj_id in enumerate(self.items):
            inv_obj = gamectx.get_object_by_id(inv_obj_id)
            objs.append(inv_obj)
        return objs

    def add(self,obj:PhysicalObject):
        if obj.count_max > 1:
            for inv_obj_id in self.items:
                if inv_obj_id is not None:
                    inv_obj = gamectx.get_object_by_id(inv_obj_id)
                    if inv_obj is not None and inv_obj.config_id == obj.config_id and inv_obj.count < inv_obj.count_max:
                        inv_obj.count+=1
                        gamectx.remove_object(obj)
                        return True
            
        for i, inv_obj_id in enumerate(self.items):
            if i != 0 and inv_obj_id is None:
                self.items[i]= obj.get_id()
                obj.disable()
                return True
        return False

    def find(self,config_id):
        objs = []
        for i, inv_obj_id in enumerate(self.items):

            if inv_obj_id is not None:
                inv_obj = gamectx.get_object_by_id(inv_obj_id)
                if inv_obj is not None and inv_obj.config_id == config_id:
                    objs.append((i,inv_obj))
        return objs

    def remove_selected(self,remove_all=False):
        return self.remove_by_slot(self.selected_slot,remove_all=remove_all)

    def remove_by_slot(self,slot_id, remove_all=False):
        if slot_id == 0:
            return None
        obj_id = self.items[slot_id]
        if obj_id is None:
            return None
        else:
            obj:PhysicalObject = gamectx.get_object_by_id(obj_id)
            if obj is not None and not remove_all and obj.count > 1:
                obj.count-=1
                newobj = gamectx.content.create_object_from_config_id(obj.config_id)
                newobj.spawn(position=Vector2(0,0))
                newobj.disable()
                return newobj
            else:
                self.items[slot_id] = None
                return obj

    def as_string(self):
        inv_info = []
        for i, obj in enumerate(self.get_objects()):
            if obj is None:
                item_name = "self" if i is 0 else "x"
                if i==self.selected_slot:
                    inv_info.append(f"[{item_name}]")
                else:
                    inv_info.append(f" {item_name} ")
            elif i==self.selected_slot:
                inv_info.append(f"[{obj.config_id}:{obj.count}]")
            else:
                inv_info.append(f" {obj.config_id}:{obj.count} ")
        return ', '.join(inv_info)

class CraftMenu:

    def __init__(self, items, requirements):
        self.slots = 10
        self.items = items

        self.requirements = requirements
        
        self.selected_slot = 0

    def get_selected(self):
        return self.items[self.selected_slot]

    def select_item(self,prev=False):
        if prev:
            if self.selected_slot ==0:
                self.selected_slot =len(self.items) - 1
            else:
                self.selected_slot-=1
                
        else:
            if self.selected_slot ==  len(self.items) -1:
                self.selected_slot=0
            else:
                self.selected_slot+=1

    def craft_selected(self,inventory:Inventory):
        config_id = self.get_selected()
        reqs = self.requirements.get(config_id)
        if reqs is not None:
            have_reqs = True
            # Check requirements
            for req_id, count in reqs.items():
                objs = inventory.find(req_id)
                if len(objs) == 0:
                    print("NON FOUND")
                    break
                else:
                    inv_count = sum([o.count for _,o in objs])
                    if inv_count < count:
                        break
            if not have_reqs:
                print("Dont have req")
                return None

            # Remove requirements
            for req_id, count in reqs.items():
                objs = inventory.find(req_id)
                
                for i, obj in objs:
                    remainder = count - obj.count
                    if remainder >= 0:
                        inventory.remove_by_slot(i)
                        gamectx.remove_object(obj)
                        count = remainder
                    else:
                        obj.count = obj.count - count
                    if count == 0:
                        break
        obj:PhysicalObject = gamectx.content.create_object_from_config_id(config_id)
        obj.spawn(position=Vector2(0,0))
        obj.disable()
        inventory.add(obj)

    def as_string(self):
        info = []
        for i, craft_type in enumerate(self.items):
            if i==self.selected_slot:
                info.append(f"[{craft_type}]")
            else:
                info.append(f" {craft_type} ")
        return " ,".join(info)



class AnimateObject(PhysicalObject):


    def __init__(self,player:Player= None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "animate"
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
        self.height = 2
        self.pushable = True

        self.default_behavior = None


        self.reward = 0

        # Visual Range in x and y direction
        self.vision_radius =  self.config.get('vision_radius',2)
        
        self._inventory = Inventory(self.config.get('start_inventory',{}))
        self._l_craftmenu = CraftMenu(
            self.config.get('craft_items',[]),
            self.config.get('craft_requirements',{}))


    def inventory(self):
        return self._inventory


    def select_item(self,prev=False):
        self._inventory.select_item(prev)

    def remove_selected_item(self):
        return self._inventory.remove_selected()

    def craftmenu(self):
        return self._l_craftmenu

    def craft(self):
        self.craftmenu().craft_selected(self.inventory())

    def select_craft_type(self,prev=False):
        self._l_craftmenu.select_item(prev)
                
    def spawn(self,position:Vector2):
        super().spawn(position)
        self.energy = self.config.get('energy_start',100)
        self.stamina = self.config.get('stamina_max',100)
        self.attack_speed = self.config.get('attack_speed',0.3)
        self.walk_speed = self.config.get('walk_speed',0.3)
        self.next_energy_decay = 0
        self.next_health_gen = 0
        self.next_stamina_gen =0

    # TODO: not in use
    def get_observation_space(self):
        pass

    # TODO: not in use
    def get_observation(self):
        pass
 
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
                    if obj_seen is not None and obj_seen.is_visible() and obj_seen.is_enabled():
                        obj_list.append(obj_seen)

        return obj_list

    def receive_push(self,*args,**kwargs):
        super().receive_push(*args,**kwargs)
        self.stunned()

    def consume_food(self,food_obj:PhysicalObject):
        self.energy += food_obj.energy
        self.play_sound("eat")
        ticks_in_action = gamectx.content.speed_factor()/0.3

        self._action = \
            {
                'type': 'eat',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
                'blocking':True
            } 

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

    def jump(self):
        
        direction = Vector2(0, 1).rotate_rad(self.angle)
        
        target_pos = self.get_position() + (direction * TILE_SIZE *2)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        oids = gamectx.physics_engine.space.get_objs_at(target_coord)

        if len(oids) == 0:
            ticks_in_action = gamectx.content.speed_factor()/0.5
            self._action = \
                {
                    'type': 'jump',
                    'start_tick': clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': (TILE_SIZE *2)/ticks_in_action,
                    'start_position': self.position,
                    'blocking':True
                }     
            self.update_position(target_pos, callback = lambda suc: self.play_sound('walk') if suc else None )



    def grab(self):

        ticks_in_action = int(gamectx.content.speed_factor())

        received_obj = None

        target_coord = gamectx.physics_engine.vec_to_coord(self.get_position())
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            target_obj:PhysicalObject = gamectx.object_manager.get_by_id(oid)
            received_obj = target_obj.receive_grab(self)
            if received_obj is not None:
                break

        if received_obj is None:
            direction = Vector2(0, 1).rotate_rad(self.angle).normalize()
            target_pos = self.get_position() + (direction * TILE_SIZE)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
                target_obj:PhysicalObject = gamectx.object_manager.get_by_id(oid)
                received_obj = target_obj.receive_grab(self)
                if received_obj is not None:
                    break

        if received_obj is not None:
            self.inventory().add(received_obj)
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

        direction = Vector2(0, 1).rotate_rad(self.angle)

        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        oids = gamectx.physics_engine.space.get_objs_at(target_coord)

        if len(oids) == 0:
            obj = self.remove_selected_item()
            if obj is not None:
                obj.enable()
                obj.update_position(target_pos)
            

        self._action = \
            {
                'type': 'drop',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }
        self.play_sound("drop")
        
    def use(self):
        selected_obj:PhysicalObject = self.inventory().get_selected()
        if self.inventory().selected_slot ==0 or selected_obj is None:
            self.unarmed_attack()
            return
        elif selected_obj.type == "tool":
            selected_obj.use_by(self)
        elif selected_obj.type == "food":
            self.consume_food(selected_obj)
            self.inventory().remove_selected()
       

    def unarmed_attack(self):

        # selected_obj:PhysicalObject = self.inventory().get_selected()
        attack_speed = self.attack_speed

        if self.stamina <= 0:
            attack_speed = attack_speed/2
        else:
            self.stamina -= 15

        ticks_in_action = round(gamectx.content.speed_factor()/attack_speed)
        direction = Vector2(0, 1).rotate_rad(self.angle)
        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)

        target_objs = []
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            obj2: PhysicalObject = gamectx.object_manager.get_by_id(oid)
            if obj2.collision_type > 0:
                target_objs.append(obj2)
        
        for obj2 in target_objs:
            obj2.receive_damage(self, self.attack_strength)

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
        direction = Vector2(0, 1).rotate_rad(self.angle)
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

        p = self.get_player()

        # Check for death
        if self.health <= 0:

            self.disable()

            #TODO :move me
            #player logic
            if p is not None:
                lives_used = p.get_data_value("lives_used", 0)
                lives_used += 1
                p.set_data_value("lives_used", lives_used)
                p.set_data_value("allow_input", False)

                def event_fn(event: DelayedEvent, data):
                    p.set_data_value("reset_required", True)
                    return []
                delay = 10*gamectx.content.speed_factor()
                event = DelayedEvent(event_fn, delay)
                gamectx.add_event(event)
                

        else:
            if p is not None:
                p.set_data_value("allow_input", True)
            elif self.default_behavior is not None and not self.get_action().get('blocking',True):
                self.default_behavior.on_update(self)

        super().update()       

    def destroy(self):
        if self.get_player() is not None:
            self.disable()
        else:
            super().destroy()

class Tool(PhysicalObject):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.attack_speed = 2
        self.type="tool"

    def use_by(self,user_object:AnimateObject):
        attack_speed = self.attack_speed

        attack_speed = attack_speed/2

        ticks_in_action = round(gamectx.content.speed_factor()/attack_speed)
        direction = Vector2(0, 1).rotate_rad(user_object.angle)
        target_pos = user_object.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)

        new_user_obj = None
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            obj2: PhysicalObject = gamectx.object_manager.get_by_id(oid)
            if 'animal' in obj2.get_types():
                added = obj2.inventory().add(self)
                if added:
                    new_user_obj = obj2
                    break
        
        if new_user_obj is not None:
            new_user_obj.add_effect(Effect("blue",3,1,0))
            user_object.inventory().remove_selected(True)        
            user_object.remove_effect("blue")
        

        user_object._action =\
            {
                'type': 'attack',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }

class Monster(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "monster"
        self.attack_strength = 10
        self.health =  40
        self.height = 2
        self.default_behavior = FollowAnimals()
        

class Animal(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "animal"
        self.default_behavior = FleeAnimals()

    def receive_damage(self,attacker_obj, damage):
        super().receive_damage(attacker_obj=attacker_obj,damage=damage)
        if self.health<=0:
            drop_on_death = self.config.get("drop_on_death")
            if drop_on_death is not None:
                for config_id, count in drop_on_death.items():
                    obj = gamectx.content.create_object_from_config_id(config_id)
                    obj.spawn(self.position)

class Human(Animal):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "human"
        self.next_energy_decay = 10
        self.next_health_gen = 0
        self.attack_strength = 10
        self.health =  40
        self.height = 2
    

    def update(self):
        super().update()


class Tree(PhysicalObject):


    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        
        self.type="tree"
        self.health =  100
        self.set_visiblity(False)
        self.pushable = False
        self.remove_on_destroy = True
        self.top_id = None
        self.trunk_id = None
        self.height = 3
        self.__fruit = []


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
        o.set_image_id('tree_trunk')
        o.spawn(position=self.get_position())
        self.trunk_id = o.get_id()
        self.child_object_ids.add(self.trunk_id)

    def add_fruit(self):
        o = gamectx.content.create_object_from_config_id('apple1')
        o.spawn(position=self.get_position())
        o.depth = 3
        o.collectable = 1
        y = random.random() * gamectx.content.tile_size*1.8
        x = random.random()* gamectx.content.tile_size - gamectx.content.tile_size/2
        o.set_image_offset(Vector2(x,y))
        self.__fruit.append(o)
        self.child_object_ids.add(o.get_id())

    def add_tree_top(self):
        o = PhysicalObject()
        o.depth=2
        o.type = "part"
        o.set_image_id('tree_top')
        o.pushable = False
        o.collision_type = 0
        o.spawn(position=self.get_position())        
        o.set_image_offset(Vector2(0, gamectx.content.tile_size*1.4))
        self.top_id = o.get_id()
        self.child_object_ids.add(self.top_id)
    
    def get_trunk(self)->PhysicalObject:
        return gamectx.object_manager.get_by_id(self.trunk_id)
        
    def get_top(self)->PhysicalObject:
        return gamectx.object_manager.get_by_id(self.top_id)

    def receive_damage(self, attacker_obj, damage):
        super().receive_damage(attacker_obj, damage)
        if self.health <=0:
            gamectx.remove_object_by_id(self.trunk_id)
            self.child_object_ids.discard(self.trunk_id)
            gamectx.remove_object(self)
            obj = gamectx.content.create_object_from_config_id('wood1')
            obj.spawn(self.position)
        elif self.health <20:
            gamectx.remove_object_by_id(self.top_id)
            self.child_object_ids.discard(self.top_id)
            for fruit in self.__fruit:
                self.child_object_ids.discard(fruit.get_id())
                gamectx.remove_object(fruit)
            self.__fruit = []

    def receive_grab(self,actor_obj):
        print("Receiving grab")
        if len(self.__fruit) >0:
            fruit = self.__fruit.pop()
            self.child_object_ids.discard(fruit.get_id())
            return fruit
        else:
            return None

    # TODO: Add start age, and growth
    def get_age(self):
        return clock.get_tick_counter() - self.created_tick 
        

class Food(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'food'
        self.energy = gamectx.content.config['food_energy']
        
    def spawn(self,position):
        super().spawn(position=position)
        self.depth = 1

class Rock(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'rock'


class Liquid(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 0
        self.type =  'liquid'
        self.permanent = True
        self.set_shape_color(color=(30, 30, 150))


    def on_collision_with_animate(self,obj:AnimateObject):
        obj.health = 0
        return 0

def rand_int_from_coord(x,y,seed=123):
    v =  (x + y * seed ) % 12783723
    h = hashlib.sha1()
    h.update(str.encode(f"{v}"))
    return int(h.hexdigest(),16) % 172837

def get_tile_image_id(x,y,seed):
    v = rand_int_from_coord(x,y,seed) % 3 + 1
    return f"grass{v}"

class Sector:

    def __init__(self, scoord, height,width):
        self.height= height
        self.width = width
        self.scoord = scoord
        self.items = {}

    
    def add(self,coord, info):
        local_items = self.items.get(coord,[])
        local_items.append(info)
        self.items[coord] = local_items


class GameMap:

    def __init__(self,path,map_config):

        self.seed = 123
        self.full_path = pkg_resources.resource_filename(__name__,path)
        self.map_layers = []
        for layer_filename in map_config['layers']:
            with open(os.path.join(self.full_path,layer_filename),'r') as f:
                layer = f.readlines()
                self.map_layers.append(layer)            
        self.index = map_config['index']
        self.tile_size = 16
        self.sector_size = 64
        self.sectors = {}
        self.sectors_loaded = set()
        self.loaded = False

    def get_sector_coord(self,coord):
        if coord is None:
            return 0,0
        return coord[0]//self.sector_size,coord[1]//self.sector_size

    def get_sector_coord_from_pos(self,pos):
        if pos is None:
            return 0,0
        return pos[0]//self.tile_size//self.sector_size,pos[1]//self.tile_size//self.sector_size

    
    def add(self,coord,info):
        scoord = self.get_sector_coord(coord)
        sector:Sector = self.sectors.get(scoord)
        if sector is None:
            logging.debug(f"Creating sector {scoord}")
            sector = Sector(scoord,self.sector_size,self.sector_size)
        sector.add(coord,info)
        self.sectors[scoord] = sector
        return sector
        
    def load_static_layers(self):
        keys = set(self.index.keys())
        for i, lines in enumerate(self.map_layers):
            self.spawn_locations = []
            for ridx, line in enumerate(lines):
                linel = len(line)
                for cidx in range(0,linel,2):
                    key = line[cidx:cidx+2]
                    coord = (cidx//2, ridx)
                    if key in keys:
                        info = self.index.get(key)
                        self.add(coord,info)

    def initialize(self,coord):
        if not self.loaded:
            print("Loading Static Layers")
            self.load_static_layers()
            self.loaded= True
        self.load_sectors_near_coord(self.get_sector_coord(coord))

    def get_neigh_coords(self,scoord) -> set:
        x,y = scoord
        dirs = {
            (x,y+1),
            (x,y-1),
            (x-1,y),
            (x+1,y),
            (x-1,y-1),
            (x+1,y-1),
            (x-1,y+1),
            (x+1,y+1)}
        return dirs

    def load_sectors_near_coord(self,scoord):
        nei_scoords = self.get_neigh_coords(scoord)
        not_loaded_scoords = nei_scoords.difference(self.sectors_loaded)
        if scoord not in self.sectors_loaded:
            print(f"Loading Current sector {scoord}")
            self.load_sector(scoord)
        for new_scoord in not_loaded_scoords:
            print(f"Loading sector {new_scoord}")
            self.load_sector(new_scoord)        

    def load_sector(self,scoord):
        sector:Sector = self.sectors.get(scoord)
        if sector is None:
            coord = scoord[0] * self.sector_size, scoord[1] * self.sector_size
            sector = self.add(coord, info = {'type':'obj','obj':'water1'})
            logging.debug(f"Adding obj at in sector: {scoord} at {coord}" )
        self.sectors_loaded.add(scoord)
        for coord, item_list in sector.items.items():
            for info in item_list:
                self.load_obj_from_info(info,coord)
     

    def load_obj_from_info(self,info,coord):
        config_id = info['obj']
        if info.get('type') == "spawn_point":
            gamectx.content.add_spawn_point(config_id,coord_to_vec(coord))
        else:
            obj = gamectx.content.create_object_from_config_id(config_id)
            obj.spawn(position=coord_to_vec(coord))      


    def get_layers(self):
        return range(2)
        
    def get_image_by_loc(self,x,y, layer_id):
        if layer_id == 0:
            return get_tile_image_id(x,y,self.seed)
        
        loc_id = rand_int_from_coord(x,y,self.seed)
        if x ==0 and y==0:
            return "baby_tree"
        if x ==2 and y==3:
            return "baby_tree"
        return None