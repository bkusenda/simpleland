from ..asset_bundle import AssetBundle
import math
import random


from .. import gamectx
from ..clock import clock
from ..common import (COLLISION_TYPE, Body, Camera, Circle, Line, Polygon,
                      Shape, Space, TimeLoggingContainer, Vector)


from ..itemfactory import  ShapeFactory
from ..object import GObject

from ..player import Player
from ..event import (DelayedEvent, Event, InputEvent,
                     PeriodicEvent, SoundEvent, ViewEvent)
from .survival_config import TILE_SIZE

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
                    return sprites_list[direction][sprite_idx]
                elif action_data['type'] == 'attack':
                    sprites_list = gamectx.content.player_attack_sprites
                    action_idx = (cur_tick - action_data['start_tick'])
                    sprite_idx = int((action_idx/action_data['ticks']) * len(sprites_list[direction]))
                    return sprites_list[direction][sprite_idx]
        if sprite_idx is None:
            sprite_idx = int(cur_tick//gamectx.content.speed_factor()) % len(sprites_list[direction])
        return sprites_list[direction][sprite_idx]
    else:
        return obj.image_id_default


def load_asset_bundle():
    image_assets = {}

    #player idle
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

    #player walk
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

    #player attack
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
    # sound_assets['crunch_eat'] = 'assets/sounds/crunch_eat.wav'
    sound_assets['bleep'] = 'assets/sounds/bleep.wav'
    music_assets = {}
    music_assets['background'] = "assets/music/PianoMonolog.mp3"


    return AssetBundle(
        image_assets=image_assets, 
        sound_assets=sound_assets,
        music_assets=music_assets,
        get_image_id_fn=get_image_id_fn,
        get_view_position_fn=get_view_position_fn)




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
        self.disable()
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)
        player.attach_object(self)
        gamectx.add_object(self)
        self.reset()

    def get_player(self):
        return gamectx.player_manager.get_player(self.get_data_value("player_id"))

    def reset(self):
        player = self.get_player()
        player.set_data_value("lives_used", 0)
        player.set_data_value("food_reward_count", 0)
        player.set_data_value("reset_required", False)
        player.set_data_value("allow_obs", True)
        player.events = []

    def spawn(self,position):
        self.update_position(position=position)
        self.set_data_value("energy",  gamectx.content.config['player_config']['energy_start'])
        self.set_data_value("health", gamectx.content.config['player_config']['health_start'])
        self.set_data_value("stamina", gamectx.content.config['player_config']['stamina_max'])
        self.set_data_value("next_energy_decay", 0)
        self.set_data_value("next_health_gen", 0)
        player = self.get_player()
        player.set_data_value("allow_input", False)
        self.enable()

    def move(self,direction,new_angle):

        body:Body = self.get_body()
        direction = direction * self.get_data_value("velocity_multiplier")
        if new_angle is not None and body.angle != new_angle:
            ticks_in_action = 1 * gamectx.content.speed_factor()
            action_complete_time = clock.get_time() + ticks_in_action
            self.set_data_value("action_completion_time",action_complete_time/2)
            body.angle = new_angle
            return []
        ticks_in_action = 1 * gamectx.content.speed_factor()
        action_complete_time = clock.get_time() + ticks_in_action
        self.set_data_value("action_completion_time",action_complete_time)
        new_pos = TILE_SIZE * direction + self.get_position()
        self.set_data_value("action",
            {
                'type':'walk',
                'start_tick':clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
                'start_position': body.position,
                'direction': direction
            })

        self.update_position(new_pos)

    def grab(self):

        ticks_in_action = int(1 * gamectx.content.speed_factor())
        action_complete_time = clock.get_time() + ticks_in_action
        self.set_data_value("action_completion_time",action_complete_time)
        direction= Vector(0,1).rotated(self.body.angle)

        target_pos= self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            target_obj = gamectx.object_manager.get_by_id(oid)
            if target_obj.get_data_value("type") =="rock":
                gamectx.remove_object(target_obj)
        
        self.set_data_value("action",
            {
                'type':'grab',
                'start_tick':clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            })

    def drop(self):
        ticks_in_action = int(1 * gamectx.content.speed_factor())
        action_complete_time = clock.get_time() + ticks_in_action
        self.set_data_value("action_completion_time",action_complete_time)
        direction= Vector(0,1).rotated(self.body.angle)

        target_pos= self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        oids = gamectx.physics_engine.space.get_objs_at(target_coord)

        if len(oids)==0 or (len(oids)==1 and gamectx.object_manager.get_by_id(oids[0]).get_data_value("type") == 'grass'):
            Rock(target_pos)
            
        self.set_data_value("action",
            {
                'type':'drop',
                'start_tick':clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            })
        return []


    def update(self):
        p = self.get_player()
        cur_time = clock.get_time()
        if cur_time > self.get_data_value("next_energy_decay", 0):
            energy = max(0, self.get_data_value("energy") - gamectx.content.config['player_config']['energy_decay'])
            self.set_data_value('energy', energy)
            if energy <= 0:
                health = self.get_data_value("health") - gamectx.content.config['player_config']['low_energy_health_penalty']
                self.set_data_value('health', health)
            self.set_data_value("next_energy_decay", cur_time + (gamectx.content.config['player_config']['energy_decay_period'] * gamectx.content.speed_factor()))

        # Health regen
        if cur_time > self.get_data_value("next_health_gen", 0):
            health = min(gamectx.content.config['player_config']['health_max'], self.get_data_value("health") + gamectx.content.config['player_config']['health_gen'])
            self.set_data_value('health', health)
            self.set_data_value("next_health_gen", cur_time + (gamectx.content.config['player_config']['health_gen_period'] * gamectx.content.speed_factor()))

        # Stamina regen
        if cur_time > self.get_data_value("next_stamina_gen", 0):
            stamina = min(gamectx.content.config['player_config']['stamina_max'], self.get_data_value("stamina") + gamectx.content.config['player_config']['stamina_gen'])
            self.set_data_value('stamina', stamina)
            self.set_data_value("next_stamina_gen", cur_time + (gamectx.content.config['player_config']['stamina_gen_period'] * gamectx.content.speed_factor()))

        # Check for death
        if self.get_data_value("health") <= 0:
            p.set_data_value("allow_input", False)
            lives_used = p.get_data_value("lives_used", 0)
            lives_used += 1
            p.set_data_value("lives_used", lives_used)
            self.disable()
            def event_fn(event: DelayedEvent, data):
                p.set_data_value("reset_required", True)
                return []
            delay = 10*gamectx.content.speed_factor()
            event = DelayedEvent(event_fn,delay)
            gamectx.add_event(event)

            
        else:
            p.set_data_value("allow_input", True)


    def attack(self):
        ticks_in_action = int(3 * gamectx.content.speed_factor())
        action_complete_time = clock.get_time() + ticks_in_action
        self.set_data_value("action_completion_time",action_complete_time)
        direction= Vector(0,1).rotated(self.body.angle)
        print(direction)

        target_pos= self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            obj2 = gamectx.object_manager.get_by_id(oid)
            if obj2.get_data_value("type") == "tree":
                new_health = obj2.get_data_value("health") -10
                print(new_health)
                obj2.set_data_value("health", new_health)
                if new_health < 30:
                    gamectx.remove_object_by_id(obj2.get_data_value("top_id"))
        
        self.set_data_value("action",
            {
                'type':'attack',
                'start_tick':clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            })
        return []

class Tree(GObject):

    def __init__(self,position, shape_color=(100, 130, 100)):
        super().__init__(Body())
        self.set_data_value("type", "tree")
        self.set_data_value("health", 100)
        self.set_position(position)
        self.set_visiblity(False)
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
        ShapeFactory.attach_rectangle(o, width=TILE_SIZE, height=TILE_SIZE)
        gamectx.add_object(o)
        return o

    def add_tree_top(self):
        o = GObject(Body(),depth=3)
        o.set_data_value("type", "part")
        o.set_image_id(f"tree_top")
        o.set_image_offset(Vector(0,-TILE_SIZE*1.5))
        o.set_position(position=self.get_position())
        
        ShapeFactory.attach_rectangle(o, width=TILE_SIZE*2, height=TILE_SIZE*2)
        gamectx.add_object(o)
        return o

class Rock(GObject):

    def __init__(self,position, shape_color=(100, 130, 100)):
        super().__init__(Body())
        self.set_data_value("type", 'rock')
        self.set_image_id('rock')
        self.set_position(position=position)
        self.set_shape_color(shape_color)
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)
        gamectx.add_object(self)

class Grass(GObject):

    def __init__(self,position, shape_color=(100, 130, 100)):
        super().__init__(Body())
        self.set_data_value("type", "grass")
        self.set_image_id(f"grass{random.randint(1,3)}")
        self.set_position(position=position)
        self.set_shape_color(shape_color)
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE*2, height=TILE_SIZE*2)
        gamectx.add_object(self)
