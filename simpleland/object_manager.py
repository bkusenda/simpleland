from typing import Any, Dict, List, Tuple

from pymunk import Vec2d

from .object import GObject
from .utils import gen_id


class GObjectManager:

    def __init__(self):
        self.objects: Dict[str, GObject] = {}
        

    def add(self,obj: GObject):
        # self.objects[obj.get_id()] = obj
        self.objects[obj.get_id()] = obj


    def clear_objects(self):
        self.objects: Dict[str, GObject] = {}

    def get_by_id(self, obj_id) -> GObject:
        return self.objects.get(obj_id, None)

    def remove_by_id(self, obj_id):
        del self.objects[obj_id]

    def get_objects(self) -> Dict[str, GObject]:
        return self.objects

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