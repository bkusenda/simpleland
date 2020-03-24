from typing import Any, Dict, List, Tuple

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (Singleton, Body, Circle, Clock,
                     Line, Polygon, Space, Vector)
from .object import (GObject, ExtendedGObject)
from .utils import gen_id

class GObjectManager:

    def __init__(self, history_size):
        self.history_size = 10
        self.objects:Dict[str,ExtendedGObject] = {}

    def add(self,timestamp, obj: GObject):
        extObj = self.objects.get(obj.get_id(), ExtendedGObject(self.history_size))
        extObj.add(timestamp,obj)
        self.objects[obj.get_id()] = extObj
    
    def link_to_latest(self,timestamp, k):
        # Only useful when not using physics. 
        # dumb client or if history isn't needed
        extObj = self.objects[k]
        extObj.link_to_latest(timestamp)

    def clear_objects(self):
        self.objects:Dict[str,ExtendedGObject] = {}

    def get_latest_by_id(self, obj_id, include_deleted = False)->Tuple[int,GObject]:
        ext_obj = self.objects.get(obj_id,None)
        if ext_obj is None:
            return None, None
        else:
            t, o = ext_obj.get_latest()
            if not include_deleted and o.is_deleted:
                return None, None
            else:
                return t, o

    def get_by_id(self, obj_id, timestamp)->GObject:
        ext_obj = self.objects.get(obj_id,None)
        if ext_obj is None:
            return None
        else:
            return ext_obj.get_interpolated(timestamp)

    def remove_by_id(self, obj_id):
        self.objects[obj_id]
        del self.objects[obj_id]

    def get_objects_for_timestamp(self,timestamp):
        valid_objs = {}
        for k,eo in self.objects.items():
            o = eo.get_interpolated(timestamp)
            if o is not None and not o.is_deleted:
                valid_objs[k] = o
        return valid_objs

    def get_objects_latest(self)->Dict[str,GObject]:
        objs = {}
        for k,eo in self.objects.items():
            t,o = eo.get_latest()
            objs[k] = o
        return objs

    def load_snapshot_from_data(self,timestamp, data):
        snapshot_keys = set()
        for odata in data:
            new_obj = GObject.build_from_dict(odata)
            self.add(timestamp, new_obj)
            snapshot_keys.add(new_obj.get_id())
        not_updated_keys = snapshot_keys - self.objects.keys()

        # link objs not in update
        for k in not_updated_keys:
            self.link_to_latest(timestamp,k)

    def get_snapshot_update(self,changed_since):
        snapshot_list = []
        for obj in list(self.get_objects_latest().values()):
            if obj.get_last_change() >= changed_since:
                snapshot_list.append(obj.get_snapshot())
        return snapshot_list
