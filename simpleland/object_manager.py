from typing import Any, Dict, List, Tuple

from pymunk import Vec2d

from .common import (Singleton, Body, Circle,
                     Line, Polygon, Space, Vector)
from .object import GObject
from .utils import gen_id


class GObjectManager:

    def __init__(self):
        self.objects: Dict[str, GObject] = {}

    def add(self,obj: GObject):
        current_obj = self.objects.get(obj.get_id())
        if current_obj is None:
            self.objects[obj.get_id()] = obj
        else:
            raise Exception("Object already added")


    def clear_objects(self):
        self.objects: Dict[str, GObject] = {}

    def get_by_id(self, obj_id) -> GObject:
        return self.objects.get(obj_id, None)

    def remove_by_id(self, obj_id):
        del self.objects[obj_id]

    def get_objects(self) -> Dict[str, GObject]:
        return self.objects
   

        #TODO: Check on code below.        
        # not_updated_keys = snapshot_keys - self.objects.keys()

        # # link objs not in update
        # for k in not_updated_keys:
        #     self.link_to_latest(timestamp, k)

    def get_snapshot_update(self, changed_since):
        snapshot_list = []
        for obj in list(self.get_objects().values()):
            if obj.get_last_change() >= changed_since:
                snapshot_list.append(obj.get_snapshot())
        return snapshot_list


    def get_snapshot_full(self):
        snapshot_list = []
        for obj in list(self.get_objects().values()):
            snapshot_list.append(obj.get_snapshot())
        return snapshot_list