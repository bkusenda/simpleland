
from typing import List
import random
from ..common import Base, Vector2
from ..clock import clock
from .survival_common import StateController,SurvivalContent
from .survival_objects import TagTool,AnimateObject,Monster, PhysicalObject, Food
from .survival_behaviors import PlayingTag
from ..player import Player
from .. import gamectx
import logging


class PlayerSpawnController(StateController):


    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.content:SurvivalContent = gamectx.content

    def reset_player(self,player:Player):
        player.set_data_value("lives_used", 0)
        player.set_data_value("food_reward_count", 0)
        player.set_data_value("reset_required", False)
        player.set_data_value("allow_obs", True)
        player.events = []

    def reset(self):
        self.spawn_players(reset=True)

    def update(self):
        pass

    #TODO: Move to spawncontroller
    def spawn_player(self,player:Player, reset=False):
        if player.get_object_id() is not None:
            player_object = gamectx.object_manager.get_by_id(player.get_object_id())
        else:
            # TODO: get playertype from game mode + client config
            player_config = self.content.get_game_config()['player_types']['1']
            config_id = player_config['config_id']
            player_object:PhysicalObject = self.content.create_object_from_config_id(config_id)
            player_object.set_player(player)

        if reset:
            self.reset_player(player)

        spawn_point = player.get_data_value("spawn_point")
        if spawn_point is None:
            spawn_point = self.content.get_available_location()
        if spawn_point is None:
            logging.error("No spawnpoint available")


        player_object.spawn(spawn_point)
        return player_object

    def spawn_players(self,reset=True):
        for player in gamectx.player_manager.players_map.values():
            self.spawn_player(player,reset)


class ObjectCollisionController(StateController):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.content:SurvivalContent = gamectx.content
        self.actor_obj_ids = set()
        self.obj_config_ids = set(["rock1"])
        self.reward_delta = -1

    def get_objects(self):
        objs = []
        for obj_id in self.actor_obj_ids:
            obj = gamectx.object_manager.get_by_id(obj_id)
            if obj is not None:
                objs.append(obj)
        return objs

    def collision_with_trigger(self,obj,obj2):
        if obj2.config_id not in self.obj_config_ids:
            return True
        obj.reward+=self.reward_delta
        return True


    def reset(self):
        self.actor_obj_ids = set()
        objs:List[AnimateObject] = []
        for obj in gamectx.object_manager.get_objects_by_config_id("human1"):
            obj.add_trigger("collision_with","obj_collid",self.collision_with_trigger)
            objs.append(obj)
            self.actor_obj_ids.add(obj.get_id())

    def update(self):
        pass

class FoodCollectController(StateController):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.content:SurvivalContent = gamectx.content
        self.actor_obj_ids = set()
        self.food_ids = set()
        self.game_start_tick = 0
        self.last_check = 0
        self.check_freq = 10 * self.content.speed_factor()
        self.needed_food = 4

    def get_objects(self):
        objs = []
        for obj_id in self.actor_obj_ids:
            obj = gamectx.object_manager.get_by_id(obj_id)
            if obj is not None:
                objs.append(obj)
        return objs

    def collected_trigger(self,obj,actor_obj):
        actor_obj.reward+=1
        self.food_ids.discard(obj.get_id())
        return True

    def collision_with_trigger(self,obj,obj2):
        if obj2.get_id() not in self.food_ids:
            return True
        obj.reward+=1
        gamectx.remove_object(obj2)
        obj.consume_food(obj2)
        self.food_ids.discard(obj2.get_id())
        gamectx.remove_object(obj2)
        return True

    def die_trigger(self,obj):
        obj.reward-=20
        print("DIE TRIGGER")
        
        return True

    def spawn_food(self):
        loc = self.content.get_available_location()
        if loc is not None:
            food:Food = self.content.create_object_from_config_id("apple1")
            food.spawn(loc)
            self.food_ids.add(food.get_id())
            food.add_trigger("receive_grab","collect",self.collected_trigger)  

    def reset(self):

        # Assign players to tag game
        self.actor_obj_ids = set()
        self.food_ids = set()
        objs:List[AnimateObject] = []
        for obj in gamectx.object_manager.get_objects_by_config_id("human1"):
            obj.add_trigger("collision_with","collect",self.collision_with_trigger)
            obj.add_trigger("die","collect",self.die_trigger)
            objs.append(obj)
            self.actor_obj_ids.add(obj.get_id())


        # Get All Food in game
        self.actor_obj_ids = set()
        objs:List[Food] = []
        for obj in gamectx.object_manager.get_objects_by_config_id("apple1"):
            obj.add_trigger("receive_grab","collect",self.collected_trigger)
            self.food_ids.add(obj.get_id())
            objs.append(obj)
        self.spawn_food()
            

    def update(self):
        time_since = clock.get_tick_counter() - self.last_check
        if time_since > self.check_freq:
            if len(self.food_ids)< self.needed_food:
                self.spawn_food()

            self.last_check = clock.get_tick_counter()
            


class TagController(StateController):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.content:SurvivalContent = gamectx.content
        self.tag_tool:TagTool = None
        self.tagged_obj = None
        self.behavior = "PlayingTag"
        self.obj_ids = set()
        self.game_start_tick = 0
        self.ticks_per_round = 100 * self.content.speed_factor()
        self.last_tag = 0
        self.tag_changes = 0
        self.is_tagged_tag = "tagged"
        self.tags_used = set(self.is_tagged_tag)
        # self.rounds = 0


    def get_objects(self):
        objs = []
        for obj_id in self.obj_ids:
            obj = gamectx.object_manager.get_by_id(obj_id)
            if obj is not None:
                objs.append(obj)
        return objs

    def reset(self):
        # Create Tag Tool
        if self.tag_tool is None:
            self.tag_tool = self.content.create_object_from_config_id("tag_tool")
            self.tag_tool.spawn(Vector2(0,0))
            self.tag_tool.disable()
            self.tag_tool.add_trigger("tag_user","tag_user",self.tag_trigger)
        
        if self.tagged_obj is not None:
            slot_tools = self.tagged_obj.get_inventory().find("tag_tool")
            for i, tool in slot_tools:
                self.tagged_obj.get_inventory().remove_by_slot(i)
            self.tag_tool.remove_effect(self.tagged_obj)

        # Assign players to tag game
        self.obj_ids = set()
        objs:List[AnimateObject] = []
        for obj in gamectx.object_manager.get_objects_by_config_id("human1"):
            objs.append(obj)
            self.obj_ids.add(obj.get_id())
            obj.tags.discard(self.is_tagged_tag)
        for obj in gamectx.object_manager.get_objects_by_config_id("monster1"):
            objs.append(obj)
            obj.tags.discard(self.is_tagged_tag)
            self.obj_ids.add(obj.get_id())

        for obj in objs:
            p= obj.get_player() 
            if p is None:
                obj.default_behavior = PlayingTag(self)

        # Select Who is "it"
        obj = random.choice(objs)
        obj.tags.add(self.is_tagged_tag)
        obj.get_inventory().add(self.tag_tool, True)
        self.tag_tool.add_effect(obj)
        self.tagged_obj = obj
        self.game_start_tick = clock.get_tick_counter()
        self.last_tag = clock.get_tick_counter()

    def tag_trigger(self,tag_tool, source_obj, target_obj):
        self.tagged_obj = target_obj
        source_obj.tags.discard(self.is_tagged_tag)
        self.last_tag = clock.get_tick_counter()
        self.tagged_obj.reward += -10
        self.tag_changes+=1
        return True
    
    def update(self):
        tag_time = clock.get_tick_counter() - self.last_tag
        if tag_time > self.ticks_per_round:
            print("Resetting tag game")
            for obj in self.get_objects():
                if obj is not None and obj.get_id() != self.tagged_obj.get_id():
                    obj.reward+=10
            self.content.request_reset()
            
