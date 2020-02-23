from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (PhysicsConfig, SLBody, SLCircle, SLClock, SLVector, SLSpace,
                               SLEvent, SLLine, SLObject, SLPoint, SLPolygon,
                               SLMoveEvent, SLMechanicalEvent, FollowBehaviour, SLPlayerCollisionEvent, SLViewEvent)
from .player import SLPlayer
from .utils import gen_id


class SLObjectManager:
    """
    Contains references to all game objects
    """

    def __init__(self):
        """

        """
        self.objects = {}

    def add(self, obj: SLObject):
        self.objects[obj.get_id()] = obj

    def get(self, id):
        return self.objects[id]

    def get_all_objects(self) -> List[SLObject]:
        return list(self.objects.values())


    def snapshot_data(self):
        objects = []
        for o in self.objects:
            objects.append(o.serialize())
        return objects

