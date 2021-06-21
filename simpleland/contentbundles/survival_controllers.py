
from typing import List
import random
from ..common import Base, Vector2
from ..clock import clock
from .survival_common import StateController,SurvivalContent
from .survival_objects import TagTool,AnimateObject,Monster, PhysicalObject
from .survival_behaviors import PlayingTag
from .survival_utils import coord_to_vec
from ..player import Player
from .. import gamectx



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
            point_found= False
            while not point_found:
                coord = self.content.gamemap.random_coords(num=1)[0]
                
                objs = gamectx.physics_engine.space.get_objs_at(coord)
                if len(objs) == 0:
                    point_found = True
                    spawn_point = coord_to_vec(coord)

        player_object.spawn(spawn_point)
        return player_object

    def spawn_players(self,reset=True):
        for player in gamectx.player_manager.players_map.values():
            self.spawn_player(player,reset)


# class SpawnController(StateController):


#     def __init__(self,*args,**kwargs):
#         super().__init__(*args,**kwargs)
#         self.content:SurvivalContent = gamectx.content

#     # self.spawn_player(player,reset=True)        
#     #########################
#     # Loading/Spawning
#     #########################
#     def spawn_objects(self):
#         #TOOD: make configurable
#         config_id = 'monster1'
#         objs = gamectx.object_manager.get_objects_by_config_id(config_id)
#         spawn_points = self.content.gamemap.get_spawn_points(config_id)
#         if len(objs) < 1 and len(spawn_points)>0:
#             object_config = self.content.get_game_config()['objects'][config_id]['config']
#             Monster(config_id = config_id, config=object_config).spawn(spawn_points[0])
#     #TODO: Move to spawncontroller
#     def spawn_player(self,player:Player, reset=False):
#         if player.get_object_id() is not None:
#             player_object = gamectx.object_manager.get_by_id(player.get_object_id())
#         else:
#             # TODO: get playertype from game mode + client config

#             player_config = self.game_config['player_types']['1']
#             config_id = player_config['config_id']
#             spawn_points = self.gamemap.get_spawn_points(config_id)
            
#             player.set_data_value("spawn_point",random.choice(spawn_points))
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

        print("Tag Controller Created")

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
            self.tag_tool.set_controller_id(self.cid)
        
        if self.tagged_obj is not None:
            slot_tools = self.tagged_obj.inventory().find("tag_tool")
            for i, tool in slot_tools:
                self.tagged_obj.inventory().remove_by_slot(i)
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
        obj.inventory().add(self.tag_tool, True)
        self.tag_tool.add_effect(obj)
        self.tagged_obj = obj
        self.game_start_tick = clock.get_tick_counter()
        self.last_tag = clock.get_tick_counter()


    def receive_message(self,sender_obj,message_name,**kwargs):
        if message_name == "tagged":
            self.tagged(sender_obj,kwargs['source_obj'],kwargs['target_obj'])

    def tagged(self,tag_tool, old_obj, new_obj):
        self.tagged_obj = new_obj
        old_obj.tags.discard(self.is_tagged_tag)
        self.last_tag = clock.get_tick_counter()
        self.tagged_obj.reward += -10
        self.tag_changes+=1
    
    def update(self):
        tag_time = clock.get_tick_counter() - self.last_tag
        if tag_time > self.ticks_per_round:
            print("Resetting tag game")
            for obj in self.get_objects():
                if obj is not None and obj.get_id() != self.tagged_obj.get_id():
                    obj.reward=10
            # self.reset()
            self.content.request_reset()
            
