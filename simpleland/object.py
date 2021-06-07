
from .utils import gen_id
from typing import Callable, List, Dict
import time

from .common import Shape, Vector, load_dict_snapshot, Base, dict_to_state, get_shape_from_dict
from .camera import Camera
from .common import get_dict_snapshot, state_to_dict, ShapeGroup, TimeLoggingContainer
from .common import COLLISION_TYPE
from .clock import clock
import copy

# class RenderAble:

#     def __init__(self)

class RenderAble:

    def __init__(self, position:Vector, angle, depth = 2):
        self.position = position
        self.angle = angle
        self.depth = depth
        self.image_offset = Vector(0,0)
        self.visible=True
        self.image_id_default = None
        self.shape = None

class GObject(Base):

        
    def __init__(self,
                 id= None,
                 data = None,
                 depth = 2):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.position = None
        self.angle = 0
        self.config_id = None
        self.created_tick = clock.get_tick_counter()
        self.player_id = None

        self.shape_group: ShapeGroup = ShapeGroup()
        self.data = {} if data is None else data
        self.last_change = None
        self.is_deleted = False
        self.enabled=True
        self.depth=depth
        self.visible=True
        self.image_width, self.image_height = 80,80
        self.shape_color = None
        self._update_position_callback = lambda obj,new_pos, skip_collision_check,callback: None

        self.image_id_default = None
        self.rotate_sprites = False
        self.image_offset = Vector(0,0)
        self.child_object_ids =set()


    def get_types(self):
        return set()     

    def update(self):
        pass

    def get_view_position(self):
        return self.position

    def get_image_id(self, angle):
        return self.image_id_default

    def set_visiblity(self,visible):
        self.visible=visible

    def set_image_offset(self,v):
        self.image_offset = v    

    def is_visible(self):
        return self.visible

    def set_image_id(self,id):
        self.image_id_default = id

    def update_last_change(self):
        self.set_last_change(clock.get_tick_counter())
    
    def set_update_position_callback(self,callback):
        self._update_position_callback = callback

    def get_data_value(self,k, default_value=None):
        return self.data.get(k,default_value)

    def disable(self):
        self.enabled=False
        self.update_position(None, skip_collision_check=True)

    def enable(self):
        self.enabled=True

    def is_enabled(self):
        return self.enabled

    def set_shape_color(self,color):
        self.shape_color = color

    def delete(self):        
        self.is_deleted = True
    
    def set_data_value(self,k,value):
        self.data[k] = value
        self.update_last_change()

    def get_id(self):
        return self.id

    def get_image_dims(self):
        return self.image_width, self.image_height
    
    def set_image_dims(self,height,width):
        self.image_width, self.image_height = (height,width)

    def update_position(self, position: Vector,skip_collision_check=False,callback=None):
        self._update_position_callback(
            self,
            position,
            skip_collision_check=skip_collision_check,
            callback=callback)

    def sync_position(self):
        self.update_position(self.position,True)

    def set_position(self, position: Vector):
        self.update_position(position,True)

    def get_position(self):
        return self.position

    def __repr__(self) -> str:
        return f"{super().__repr__()}, id:{self.id}, data:{self.data}, dict_data:{self.__dict__}"

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
        return self.last_change

    def get_snapshot(self):
        data = get_dict_snapshot(self, exclude_keys={'on_change_func'})
        data['data']['last_change']= self.get_last_change()
        data['data']['data'] = self.data
        return data

    def load_snapshot(self, data,exclude_keys=set()):
        load_dict_snapshot(self, data, exclude_keys=exclude_keys)