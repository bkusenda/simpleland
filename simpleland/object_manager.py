from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (PhysicsConfig, SLBody, SLCircle, SLClock, SLVector, SLSpace,
                               SLEvent, SLLine, SLObject, SLPolygon,
                               SLMoveEvent, SLMechanicalEvent, SLPlayerCollisionEvent, SLViewEvent, Singleton)
from .player import SLPlayer
from .utils import gen_id


class SLObjectManager(metaclass=Singleton):
    """
    Contains references to all game objects
    """

    def __init__(self):
        """

        """
        self.objects:Dict[str,SLObject] = {}

    def add(self, obj: SLObject):
        self.objects[obj.get_id()] = obj

    def clear_objects(self):
        self.objects:Dict[str,SLObject] = {}

    def get_by_id(self, obj_id)->SLObject:
        return self.objects[obj_id]

    def get_all_objects(self) -> List[SLObject]:
        return list(self.objects.values())

    def get_snapshot(self):
        results = {}
        for k,o in self.objects.items():
            results[k]= o.get_snapshot()
        return results

    def load_snapshot(self,data):
        new_objs = []
        for k,o_data in data.items():
            if k in self.objects:
                self.objects[k].load_snapshot(o_data)
            else:
                new_obj = SLObject.build_from_dict(o_data)
                self.objects[k] = new_obj
                new_objs.append(new_obj)
        return new_objs

