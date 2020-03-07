import pymunk
import pygame
from pygame.time import Clock
from .utils import gen_id
from typing import List, Dict
import time

SLClock: Clock = pygame.time.Clock

SLVector = pymunk.Vec2d

def get_dict_snapshot(obj, exclude_keys = {}):
    _type = type(obj).__name__
    data = {}
    for k, v in obj.__dict__.items():
        if k in exclude_keys:
            continue
        if issubclass(type(v), SLBase):
            data[k] = v.get_snapshot()
        elif v is None or isinstance(v, (int, float, str, SLVector)):
            data[k] = v
        elif type(v) is list:
            data[k] = []
            for vv in v:
                data[k].append(get_dict_snapshot(vv))
        else:
            
            pass
            #print("Skipping snapshotting of:{} with value {}".format(k, v))
    return {"_type":_type,"data": data}


def load_dict_snapshot(obj, dict_data, exclude_keys={}):

    for k, v in dict_data['data'].items():
        if k in exclude_keys:
            continue
        
        if issubclass(type(v), SLBase):
            data = v.load_snapshot(obj.__dict__[k], v)
        elif v is None or isinstance(v, (int, float, str)):
            obj.__dict__[k] = v
        else:
            pass
           # print("Skipping loading of:{} with value {}".format(k, v))


class SimClock:
    
    def __init__(self, start_time= None):
        self.resolution = 1000# milliseconds
        self.start_time = self._current_time() if start_time is None else start_time
        # self.last_tick = self.start_time
        self.pygame_clock = SLClock()

    def _current_time(self):
        return time.time() * self.resolution
    
    def copy(self):
        return SimClock(self.start_time)

    def get_start_time(self):
        return self.start_time
    
    def tick(self,ticks_per_second):
        return self.pygame_clock.tick(ticks_per_second)

    # def tick(self, ticks_per_second = 60):
    #     expected_diff = (1.0/ticks_per_second) * 1000
    #     tick_diff = self.get_time() - self.last_tick
    #     delay_seconds = (expected_diff - tick_diff)/self.resolution
    #     if delay_seconds < 0:
    #         delay_seconds = 0
    #     #print("Delay in seconds = {} ".format(delay_seconds))
    #     time.sleep(delay_seconds)
    #     self.last_tick = self.get_time()

    def set_time(self,time):
        self.start_time = time
        self.last_tick = self.get_time()

    def reset(self):
        self.start_time = self._current_time()

    def get_time(self):
        return self._current_time() - self.start_time

# source: https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class SLBase:

    def get_snapshot(self):
        return get_dict_snapshot(self)

    def load_snapshot(self, data):
        load_dict_snapshot(self, data)


class PlayerConfig(SLBase):

    def __init__(self):
        """
        """

class PhysicsConfig(SLBase):
    def __init__(self):
        self.velocity_multiplier = 5.0
        self.orientation_multiplier = 1.0
        self.space_damping = 0.5
        self.steps_per_second = 60
        self.clock_multiplier = 1

class GameConfig(SLBase):

    def __init__(self):
        self.move_speed = 1
        self.keep_moving = 0
        self.clock_factor = 1.0

SLSpace = pymunk.Space
SLBody = pymunk.Body

def state_to_dict(state):
    new_state={}
    for k,tuplist in state.items():
        new_state[k] ={}
        for kk,vv in tuplist:
            new_state[k][kk] = vv
    return new_state

def dict_to_state(data):
    state={}
    for k,d in data.items():
        state[k] =[]
        for kk,vv in d.items():
            state[k].append((kk,vv))
    return state

class SLShape(pymunk.Shape, SLBase):

    def __init__(self):
        self.object_id= None
        self.id = gen_id()
    
    def get_id(self):
        return self.id

    def set_object_id(self, object_id):
        self.object_id = object_id

    def get_object_id(self):
        return self.object_id

    def get_common_info(self):
        dict_data = get_dict_snapshot(self, exclude_keys={"_body"})
        dict_data['state'] = state_to_dict(self.__getstate__())
        del dict_data['state']['init']['body'] 
        return dict_data


class SLLine(SLShape, pymunk.Segment):

    def __init__(self,body:SLBody,a,b,radius,**kwargs):
        pymunk.Segment.__init__(self,body,a,b,radius, **kwargs)
        SLShape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {
                    "a":self.a,
                    "b":self.b,
                    "radius": self.radius}
        return data
        
class SLPolygon(SLShape, pymunk.Poly):

    def __init__(self, body, vertices,**kwargs):
        pymunk.Poly.__init__(self,body, vertices,**kwargs)
        SLShape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {
                "vertices":[v for v in self.get_vertices()],
            }
        return data

class SLCircle(SLShape, pymunk.Circle):

    def __init__(self, body,radius,**kwargs):
        pymunk.Circle.__init__(self,body,radius,**kwargs)
        SLShape.__init__(self)

    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {"radius": self.radius}
        return data

def get_shape_from_dict(body,dict_data):
    if dict_data['_type'] == 'SLLine':
        shape = SLLine(body, **dict_data['params'])
    else:
        cls = globals()[dict_data['_type']]
        shape = cls(body, **dict_data['params'])
    
    shape.load_snapshot(dict_data)
    gen_data = dict_data['state']['general']
    shape.collision_type = gen_data['collision_type']  
    shape.filter = gen_data['filter']
    shape.elasticity = gen_data['elasticity']
    shape.friction = gen_data['friction']
    shape.surface_velocity = gen_data['surface_velocity']
    return shape


class SLShapeGroup(SLBase):

    def __init__(self):
        self._shapes:Dict[str,SLShape]={}

    def add(self,shape):
        self._shapes[shape.get_id()] = shape
    
    def get_shapes(self)->List[SLShape]:
        return self._shapes.values()

    def get_snapshot(self):
        data = {}
        for k,s in self._shapes.items():
            data[k] = s.get_snapshot()
        return data

    def load_snapshot(self, data: Dict[str,Dict]):
        for k,shape_dict in data:
            self._shapes[k].load_snapshot(shape_dict)

class SLCamera(SLBase):

    def __init__(self, distance: float = 30):
        self.distance = distance  # zoom

    def get_distance(self):
        return self.distance

class SLObject(SLBase):

    @classmethod
    def build_from_dict(cls,dict_data):
        data = dict_data['data']
        

        body = SLBody()

        body.__setstate__(dict_to_state(dict_data['body']))
        # shape_group = SLShapeGroup.build_from_dict(body,data['shape_group'])
        obj = SLObject(body=body, id=data['id'])
        load_dict_snapshot(obj, dict_data, exclude_keys={"body"})

        for k,v in data['shape_group'].items():
            obj.add_shape(get_shape_from_dict(body,v))

        if data['camera'] :
            obj.camera = SLCamera(**data['camera']['data'])
        return obj
        
    def __init__(self,
                 body:SLBody=None,
                 id= None,
                 data = None,
                 camera=None):
        if id is None:
            self.id = gen_id()
        else:
            self.id = id
        self.camera = camera
        self.body: SLBody = body

        self.shape_group: SLShapeGroup = SLShapeGroup()
        self.data = {} if data is None else data
        self.last_change = None
        self.is_deleted = False

    def get_data_value(self,k, default_value=None):
        return self.data.get(k,default_value)
    
    def delete(self,time_stamp):
        self.is_deleted = True
        self.last_change = time_stamp
    
    def set_data_value(self,k,value,time_stamp):
        self.data[k] = value
        self.last_change = time_stamp

    def get_body(self) -> SLBody:
        return self.body

    def get_id(self):
        return self.id

    def set_position(self, position: SLVector):
        self.get_body().position = position

    def add_shape(self,shape:SLShape, collision_type=1):
        shape.set_object_id(self.get_id())
        shape.collision_type = collision_type
        self.shape_group.add(shape)

    def get_shapes(self):
        return self.shape_group.get_shapes()

    def get_camera(self) -> SLCamera:
        return self.camera

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

def build_interpolated_object(obj_1:SLObject,obj_2:SLObject,fraction=0.5):
    
    b1 = obj_1.get_body()
    b2 = obj_2.get_body()
    # print("--")
    # print(b1.position)
    # print(b2.position)
    # print(fraction)
    pos_x = (b2.position.x - b1.position.x) * fraction + b1.position.x
    pos_y = (b2.position.y - b1.position.y) * fraction + b1.position.y
    b_new = SLBody()
    b_new.last_change = b1.last_change

    # b_new._set_position(SLVector(pos_x,pos_y))
    b_new.position = SLVector(pos_x,pos_y)
    # print(pos_x)
    # print(pos_y)

    force_x = (b2.force.x - b1.force.x) * fraction + b1.force.x
    force_y = (b2.force.y - b1.force.y) * fraction + b1.force.y
    b_new.force = SLVector(force_x,force_y)

    b_new.angle = (b2.angle - b1.angle) * fraction + b1.angle

    b_new.velocity.x = (b2.velocity.x - b1.velocity.x) * fraction + b1.velocity.x
    b_new.velocity.y = (b2.velocity.y - b1.velocity.y) * fraction + b1.velocity.y

    b_new.angular_velocity = (b2.angular_velocity - b1.angular_velocity) * fraction + b1.angular_velocity
    # b_new.angular_velocity.y = (b2.angular_velocity.y - b1.angular_velocity.y) * fraction + b1.angular_velocity.y

    # shape_group = SLShapeGroup.build_from_dict(body,data['shape_group'])
    obj = SLObject(body=b_new, id=obj_1.get_id(),data=obj_1.data)
    obj.is_deleted = obj_1.is_deleted
    obj.last_change = obj_1.last_change
    #load_dict_snapshot(obj, obj_1.get_snapshot(), exclude_keys={"body"})

    #TODO: COPY??
    for shape in obj_1.shape_group.get_shapes():
        obj.add_shape(get_shape_from_dict(b_new,shape.get_snapshot()))

    if obj_2.get_camera() is not None:
        camera_dist = (obj_2.get_camera().distance - obj_1.get_camera().distance) * fraction + obj_1.get_camera().distance
        obj.camera = SLCamera(distance=camera_dist)
    return obj