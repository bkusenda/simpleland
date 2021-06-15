
from typing import List
import random
from ..common import Base, Vector2
from ..clock import clock
from .survival_common import StateController,SurvivalContent
from .survival_objects import TagTool,AnimateObject
from .survival_behaviors import PlayingTag
from .. import gamectx

class TagController(StateController):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.content:SurvivalContent = gamectx.content
        self.tag_tool:TagTool = None
        self.tagged_obj = None
        self.behavior = "PlayingTag"
        self.obj_ids = set()
        self.game_start_tick = 0
        self.ticks_per_round = 400
        self.last_tag = 0
        self.tag_changes = 0
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
        for obj in gamectx.object_manager.get_objects_by_config_id("monster1"):
            objs.append(obj)
            self.obj_ids.add(obj.get_id())

        for obj in objs:
            p= obj.get_player() 
            if p is None:
                obj.default_behavior = PlayingTag(self)

        # Select Who is "it"
        obj = random.choice(objs)
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
        self.last_tag = clock.get_tick_counter()
        self.tag_changes+=1
    
    def update(self):
        tag_time = clock.get_tick_counter() - self.last_tag
        if tag_time > self.ticks_per_round:
            pass
        
        pass