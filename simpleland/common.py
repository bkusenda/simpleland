import pymunk
import pygame
from .utils import gen_id
from typing import List, Dict
import time
import json
OBJ_TYPES = ['default','sensor']
COLLISION_TYPE = {v:i for i, v in enumerate(OBJ_TYPES)}
from pymunk import Vec2d

Clock = pygame.time.Clock

Vector = pymunk.Vec2d

class StateEncoder(json.JSONEncoder):
    def default(self, obj): # pylint: disable=E0202
        if type(obj) == Vec2d:
            return {
                "_type": "Vec2d",
                "x":obj.x,
                "y":obj.y}
        return json.JSONEncoder.default(self, obj)

class StateDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj): # pylint: disable=E0202
        if '_type' not in obj:
            return obj
        type = obj['_type']
        if type == 'Vec2d':
            return Vec2d(obj['x'],obj['y'])
        return obj

def get_dict_snapshot(obj, exclude_keys = {}):
    _type = type(obj).__name__
    data = {}
    for k, v in obj.__dict__.items():
        if k in exclude_keys:
            continue
        if issubclass(type(v), Base):
            data[k] = v.get_snapshot()
        elif v is None or isinstance(v, (int, float, str, Vector, dict)):
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
        
        if issubclass(type(v), Base):
            data = v.load_snapshot(obj.__dict__[k], v)
        elif v is None or isinstance(v, (int, float, str, Vector)):
            obj.__dict__[k] = v
        elif v is None or (isinstance(v, dict) and ("_type" not in v)):
            obj.__dict__[k] = v


class SimClock:
    
    def __init__(self, start_time= None):
        self.resolution = 1000# milliseconds
        self.start_time = self._current_time() if start_time is None else start_time
        self.pygame_clock = Clock()
        self.tick_time = self.get_exact_time()
        self.tick_counter = 0

    def _current_time(self):
        return time.time() * self.resolution
    
    def get_start_time(self):
        return self.start_time
    
    def tick(self,tick_rate):
        if tick_rate ==0:
            return
        self.pygame_clock.tick(tick_rate)
        self.tick_time = self.get_exact_time()
        self.tick_counter +=1
        return self.tick_time

    def get_time(self):
        return self.tick_time

    def get_tick_counter(self):
        return self.tick_counter

    def set_absolute_time(self,time):
        self.start_time = time
        self.tick_time = self.get_exact_time()

    def get_exact_time(self):
        return self._current_time() - self.start_time



class StepClock:
    
    def __init__(self, start_time= 0):
        self.start_time = start_time
        self.tick_time = 0
        print("USING STEP CLOCK")

    def _current_time(self):
        return self.tick_time

    def get_start_time(self):
        return self.start_time
    
    def tick(self,tick_rate=None):
        self.tick_time +=1
        return self.tick_time

    def get_time(self):
        return self.tick_time

    def get_tick_counter(self):
        return self.tick_time

    def set_absolute_time(self,time):
        self.tick_time = time

    def get_exact_time(self):
        return self.tick_time

# source: https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Base:

    def get_snapshot(self):
        return get_dict_snapshot(self)

    def load_snapshot(self, data):
        load_dict_snapshot(self, data)


class PlayerConfig(Base):

    def __init__(self):
        """
        """

Space = pymunk.Space
Body = pymunk.Body

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

class Shape(pymunk.Shape, Base):

    def __init__(self):
        self.object_id= None
        self.id = gen_id()
        self.label = None
    
    def get_id(self):
        return self.id

    def set_label(self,label):
        self.label = label

    def set_object_id(self, object_id):
        self.object_id = object_id

    def get_object_id(self):
        return self.object_id

    def get_common_info(self):
        dict_data = get_dict_snapshot(self, exclude_keys={"_body"})
        dict_data['state'] = state_to_dict(self.__getstate__())
        del dict_data['state']['init']['body'] 
        return dict_data


class Line(Shape, pymunk.Segment):

    def __init__(self,body:Body,a,b,radius,**kwargs):
        pymunk.Segment.__init__(self,body,a,b,radius, **kwargs)
        Shape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {
                    "a":self.a,
                    "b":self.b,
                    "radius": self.radius}
        return data
        
class Polygon(Shape, pymunk.Poly):

    def __init__(self, body, vertices,**kwargs):
        pymunk.Poly.__init__(self,body, vertices,**kwargs)
        Shape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {
                "vertices":[v for v in self.get_vertices()],
            }
        return data

class Rectangle(Shape,pymunk.Poly):

    def __init__(self, body, center,width,height,**kwargs):
        w =width/2
        h = height/2

        v1 = Vector(center.x - w,center.y + h)
        v2 = Vector(center.x + w,center.y + h)
        v3 = Vector(center.x + w,center.y - h)
        v4 = Vector(center.x - w,center.y - h)
        pymunk.Poly.__init__(self,body, vertices=[v1,v2,v3,v4],**kwargs)
        Shape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {
                "vertices":[v for v in self.get_vertices()],
            }
        return data

class Circle(Shape, pymunk.Circle):

    def __init__(self, body,radius,**kwargs):
        pymunk.Circle.__init__(self,body,radius,**kwargs)
        Shape.__init__(self)

    def get_snapshot(self):
        data = self.get_common_info()
        data['params'] = {"radius": self.radius}
        return data

def get_shape_from_dict(body,dict_data):
    if dict_data['_type'] == 'SLLine':
        shape = Line(body, **dict_data['params'])
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

class TimeLoggingContainer:

    def __init__(self, log_size):
        self.log_size = log_size
        self.log = [None for i in range(log_size)]
        self.timestamps = [None for i in range(log_size)]
        self.counter = 0

    def get_id(self):
        obj = self.get_latest()
        return obj.get_id()


    def add(self,timestamp, obj):
        self.log[self.counter % self.log_size] = obj
        self.timestamps[self.counter % self.log_size] = timestamp
        self.counter +=1
    
    def link_to_latest(self,timestamp):
        self.add(timestamp,self.get_latest_with_timestamp())

    def get_bordering_timestamps(self, timestamp):
        #TODO binary search is faster
        timestamp_lookup = {v:i for i,v in enumerate(self.timestamps)}
        lst = sorted([i for i in self.timestamps if i is not None])
        next_idx = None
        previous_idx = None
        for i,v in enumerate(lst):
            if v >= timestamp:
                next_idx = v
                break
            elif v< timestamp:
                previous_idx = lst[i]
        return (timestamp_lookup.get(previous_idx,None), 
                previous_idx, 
                timestamp_lookup.get(next_idx,None), 
                next_idx)
    
    def get_pair_by_timestamp(self, timestamp):
        prev_idx,prev_timestamp, next_idx, next_timestamp = self.get_bordering_timestamps(timestamp)
        next_obj = None if next_idx is None else self.log[next_idx]
        prev_obj = None if prev_idx is None else self.log[prev_idx]
        return prev_obj, prev_timestamp, next_obj, next_timestamp

    def get_prev_entry(self,timestamp):
        prev_obj, prev_timestamp, next_obj, next_timestamp = self.get_pair_by_timestamp(timestamp)
        return prev_timestamp, prev_obj

    def get_next_entry(self,timestamp):
        prev_obj, prev_timestamp, next_obj, next_timestamp = self.get_pair_by_timestamp(timestamp)
        return next_timestamp, next_obj

    def get_latest(self):
        if self.counter == 0:
            return None, None
        idx = (self.counter-1) % self.log_size
        return self.log[idx]

    def get_latest_with_timestamp(self):
        if self.counter == 0:
            return None, None
        idx = (self.counter-1) % self.log_size
        obj = self.log[idx]
        timestamp = self.timestamps[idx]
        return timestamp, obj

class ShapeGroup(Base):

    def __init__(self):
        self._shapes:Dict[str,Shape]={}

    def add(self,shape):
        self._shapes[shape.get_id()] = shape
    
    def get_shapes(self)->List[Shape]:
        return self._shapes.values()

    def get_snapshot(self):
        data = {}
        for k,s in self._shapes.items():
            data[k] = s.get_snapshot()
        dict_data = {}
        dict_data['data'] = data
        dict_data['_type'] = "SLShapeGroup"
        return dict_data

    def load_snapshot(self, dict_data: Dict[str,Dict]):
        data = dict_data['data']
        for k,shape_dict in data:
            self._shapes[k].load_snapshot(shape_dict)

class Camera(Base):

    def __init__(self, distance: float = 30, position_offset = Vector(0,0)):
        self.distance = distance  # zoom
        self.position_offset = position_offset

    def get_distance(self):
        return self.distance
