
from .utils import gen_id
from typing import Callable, List, Dict
import time

from .common import Shape, Vector, load_dict_snapshot, Base, dict_to_state, get_shape_from_dict
from .camera import Camera
from .common import get_dict_snapshot, state_to_dict, ShapeGroup, TimeLoggingContainer
from .common import COLLISION_TYPE
from .clock import clock
import copy
class GObject(Base):

        
    def __init__(self,
                 id= None,
                 data = None,
                 depth = 2):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.position = Vector(0,0)
        self.angle = 0

        self.shape_group: ShapeGroup = ShapeGroup()
        self.data = {} if data is None else data
        self.last_change = None
        self.is_deleted = False
        self.enabled=True
        self.depth=depth
        self.visible=True
        self.image_width, self.image_height = 80,80
        self.shape_color = None
        self._update_position_callback = lambda obj,new_pos: None

        self.image_id_default = None
        self.image_id_current = None
        self.rotate_sprites = False
        self.image_offset = Vector(0,0)
        self.child_object_ids =[]

    # This function should be overridden
    def create(self,*args,**kwargs):
        pass        

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

    def update_position(self, position: Vector,skip_collision_check=False):
        self._update_position_callback(self,position,skip_collision_check=skip_collision_check)

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


    def load_snapshot(self,timestamp, data):
        load_dict_snapshot(self, data, exclude_keys={""})



# def build_interpolated_object(obj_1:GObject,obj_2:GObject,fraction=0.5):
#     print("INTERPOLAT")
    
#     b1 = obj_1.get_body()
#     b2 = obj_2.get_body()

#     pos_x = (b2.position.x - b1.position.x) * fraction + b1.position.x
#     pos_y = (b2.position.y - b1.position.y) * fraction + b1.position.y
#     b_new = Body()
#     b_new.last_change = b1.last_change

#     b_new.position = Vector(pos_x,pos_y)

#     force_x = (b2.force.x - b1.force.x) * fraction + b1.force.x
#     force_y = (b2.force.y - b1.force.y) * fraction + b1.force.y
#     b_new.force = Vector(force_x,force_y)

#     b_new.angle = (b2.angle - b1.angle) * fraction + b1.angle

#     b_new.velocity.x = (b2.velocity.x - b1.velocity.x) * fraction + b1.velocity.x
#     b_new.velocity.y = (b2.velocity.y - b1.velocity.y) * fraction + b1.velocity.y

#     b_new.angular_velocity = (b2.angular_velocity - b1.angular_velocity) * fraction + b1.angular_velocity

#     obj = GObject(body=b_new, id=obj_1.get_id(),data=obj_1.data)
#     obj.is_deleted = obj_1.is_deleted
#     obj.last_change = obj_1.last_change
#     obj.set_image_dims(obj_1.image_width, obj_1.image_height)

#     for shape in obj_1.shape_group.get_shapes():
#         obj.add_shape(get_shape_from_dict(b_new,shape.get_snapshot()))

#     return obj

# #TODO: no longer used
# class ExtendedGObject(TimeLoggingContainer):

#     def add(self,timestamp, obj:GObject):
#         super().add(timestamp,obj)
  
#     def get_interpolated(self, timestamp):
#         prev_obj, prev_timestamp, next_obj, next_timestamp = self.get_pair_by_timestamp(timestamp)
#         if prev_obj is None:
#             return next_obj
#         if next_obj is None:
#             return prev_obj

#         if next_timestamp-prev_timestamp  ==0:
#             return prev_obj
#         return next_obj

#         # fraction = (timestamp - prev_timestamp)/(next_timestamp-prev_timestamp)
#         # return build_interpolated_object(prev_obj, next_obj, fraction)
