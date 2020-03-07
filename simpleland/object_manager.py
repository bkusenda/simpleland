from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (PhysicsConfig, Singleton, SLBody, SLCircle, SLClock,
                     SLLine, SLObject, SLPolygon, SLSpace, SLVector)
from .utils import gen_id

class SLObjectManager:
    """
    Contains references to all game objects
    """

    def __init__(self):
        self.objects:Dict[str,SLObject] = {}

    def add(self, obj: SLObject):
        self.objects[obj.get_id()] = obj

    def clear_objects(self):
        self.objects:Dict[str,SLObject] = {}

    def get_by_id(self, obj_id)->SLObject:
        return self.objects.get(obj_id,None)

    def remove_by_id(self, obj_id)->SLObject:
        self.objects[obj_id]
        del self.objects[obj_id]

    def get_all_objects(self) -> List[SLObject]:
        return list(self.objects.values())

    def get_snapshot(self):
        objs = self.get_all_objects()
        results = {}
        for o in objs:
            results[o.get_id()]= o.get_snapshot()
        return results

    def set_last_change(self,timestamp):
        objs = list(self.objects.values())
        for obj in objs:
            obj.set_last_change(timestamp)

    def load_snapshot(self,data):
        new_objs = []
        removed_objs = []
        for k,o_data in data.items():
            is_deleted = o_data['data']['is_deleted']
            if k in self.objects:
                if is_deleted:
                    removed_objs.append(self.objects[k])
                else:
                    self.objects[k].load_snapshot(o_data)
            elif not is_deleted:
                new_obj = SLObject.build_from_dict(o_data)
                self.objects[k] = new_obj
                new_objs.append(new_obj)
        return new_objs, removed_objs
