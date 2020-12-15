import pymunk
import pygame
from .utils import gen_id
from typing import List, Dict
import time

from .common import Shape, Vector, load_dict_snapshot, Base, Body, dict_to_state, get_shape_from_dict, Camera
from .common import get_dict_snapshot, state_to_dict, ShapeGroup, TimeLoggingContainer
from .common import COLLISION_TYPE

class GObject(Base):

    @classmethod
    def build_from_dict(cls,dict_data):
        data = dict_data['data']
        

        body = Body()

        body.__setstate__(dict_to_state(dict_data['body']))
        # shape_group = SLShapeGroup.build_from_dict(body,data['shape_group'])
        obj = GObject(body=body, id=data['id'])
        load_dict_snapshot(obj, dict_data, exclude_keys={"body"})

        for k,v in data['shape_group']['data'].items():
            obj.add_shape(get_shape_from_dict(body,v))
        
        # print(data)
        if "data" in data:
            obj.data = data['data']

        return obj
        
    def __init__(self,
                 body:Body=None,
                 id= None,
                 data = None,
                 depth = 2):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.body: Body = body

        self.shape_group: ShapeGroup = ShapeGroup()
        self.data = {} if data is None else data
        self.last_change = None
        self.is_deleted = False
        self.depth=depth

    def get_data_value(self,k, default_value=None):
        return self.data.get(k,default_value)
    
    def delete(self):
        self.is_deleted = True
    
    def set_data_value(self,k,value):
        self.data[k] = value

    def get_body(self) -> Body:
        return self.body

    def get_id(self):
        return self.id

    def set_position(self, position: Vector):
        self.get_body().position = position

    def get_position(self):
        return self.get_body().position


    def add_shape(self,shape:Shape, collision_type=1,label=None):
        shape.set_object_id(self.get_id())
        shape.collision_type = collision_type
        if collision_type == COLLISION_TYPE['sensor']:
            shape.sensor = True
        shape.set_label(label)
        self.shape_group.add(shape)

    def get_shapes(self):
        return self.shape_group.get_shapes()


    def set_last_change(self,timestamp):
        self.last_change = timestamp

    def get_last_change(self):
        if self.body.last_change is None and self.last_change is None:
            return None
        if self.body.last_change is None:
            return self.last_change
        if self.last_change is None:
            return None
        if self.body.last_change > self.last_change:
            return self.body.last_change
        return self.last_change

    def get_snapshot(self):
        data = get_dict_snapshot(self, exclude_keys={'body','on_change_func'})
        data['body'] = state_to_dict(self.body.__getstate__())
        data['data']['last_change']= self.get_last_change()
        data['data']['data'] = self.data
        # print(data['body']['special'].keys())
        del data['body']['special']['_velocity_func']
        del data['body']['special']['_position_func']
        return data

    def get_snapshot_struct(self):
        data = get_dict_snapshot(self, exclude_keys={'body','on_change_func'})
        data['body'] = state_to_dict(self.body.__getstate__())
        data['data']['last_change']= self.get_last_change()
        data['data']['data'] = self.data
        # print(data['body']['special'].keys())
        del data['body']['special']['_velocity_func']
        del data['body']['special']['_position_func']
        return data

    def load_snapshot(self, data):
        load_dict_snapshot(self, data, exclude_keys={"body"})
        body_data = data['body']

        # This breaks things
        #self.body.__setstate__(data['body'])
        self.body.position = body_data['general']['position']
        # self.body.force = body_data['general']['force']
        self.body.velocity = body_data['general']['velocity']
        self.body.angle = body_data['general']['angle']
        #self.body.moment = body_data['general']['moment']
        #self.body.rotation_vector = body_data['general']['rotation_vector']


        # self.body.torque = body_data['general']['torque']
        self.body.angular_velocity = body_data['general']['angular_velocity']


def build_interpolated_object(obj_1:GObject,obj_2:GObject,fraction=0.5):
    
    b1 = obj_1.get_body()
    b2 = obj_2.get_body()
    # print("--")
    # print(b1.position)
    # print(b2.position)
    # print(fraction)
    pos_x = (b2.position.x - b1.position.x) * fraction + b1.position.x
    pos_y = (b2.position.y - b1.position.y) * fraction + b1.position.y
    b_new = Body()
    b_new.last_change = b1.last_change

    # b_new._set_position(SLVector(pos_x,pos_y))
    b_new.position = Vector(pos_x,pos_y)
    # print(pos_x)
    # print(pos_y)

    force_x = (b2.force.x - b1.force.x) * fraction + b1.force.x
    force_y = (b2.force.y - b1.force.y) * fraction + b1.force.y
    b_new.force = Vector(force_x,force_y)

    b_new.angle = (b2.angle - b1.angle) * fraction + b1.angle

    b_new.velocity.x = (b2.velocity.x - b1.velocity.x) * fraction + b1.velocity.x
    b_new.velocity.y = (b2.velocity.y - b1.velocity.y) * fraction + b1.velocity.y

    b_new.angular_velocity = (b2.angular_velocity - b1.angular_velocity) * fraction + b1.angular_velocity
    # b_new.angular_velocity.y = (b2.angular_velocity.y - b1.angular_velocity.y) * fraction + b1.angular_velocity.y

    # shape_group = SLShapeGroup.build_from_dict(body,data['shape_group'])
    obj = GObject(body=b_new, id=obj_1.get_id(),data=obj_1.data)
    obj.is_deleted = obj_1.is_deleted
    obj.last_change = obj_1.last_change
    #load_dict_snapshot(obj, obj_1.get_snapshot(), exclude_keys={"body"})

    #TODO: COPY??
    for shape in obj_1.shape_group.get_shapes():
        obj.add_shape(get_shape_from_dict(b_new,shape.get_snapshot()))

    # if obj_2.get_camera() is not None:
    #     camera_dist = (obj_2.get_camera().distance - obj_1.get_camera().distance) * fraction + obj_1.get_camera().distance
    #     obj.camera = Camera(distance=camera_dist)
    return obj

class ExtendedGObject(TimeLoggingContainer):

    def add(self,timestamp, obj:GObject):
        super().add(timestamp,obj)
  
    def get_interpolated(self, timestamp):
        prev_obj, prev_timestamp, next_obj, next_timestamp = self.get_pair_by_timestamp(timestamp)
        if prev_obj is None:
            return None
        if next_obj is None:
            return prev_obj

        if next_timestamp-prev_timestamp  ==0:
            return prev_obj

        fraction = (timestamp - prev_timestamp)/(next_timestamp-prev_timestamp)
        return build_interpolated_object(prev_obj, next_obj, fraction)
