import pymunk
import pygame
from pygame.time import Clock
from .utils import gen_id
from typing import List, Dict

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
        self.velocity_multiplier = 10.0
        self.orientation_multiplier = 2.0
        self.space_damping = 0.5
        self.fps = 60
        self.clock_multiplier = 1

class GameConfig(SLBase):

    def __init__(self):
        self.move_speed = 2
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
        
        # body_data = state_to_dict(dict_data['body'])
        # print(body_data)
        
        # body = SLBody(**body_data['init'])
        # body.position = body_data['general']['position']
        # body.force = body_data['general']['force']
        # body.velocity = body_data['general']['velocity']
        # body.torque = body_data['general']['torque']

        body = SLBody()

        body.__setstate__(dict_data['body'])
        # shape_group = SLShapeGroup.build_from_dict(body,data['shape_group'])
        obj = SLObject(body=body, obj_id=data['id'])
        load_dict_snapshot(obj, dict_data, exclude_keys={"body"})

        for k,v in data['shape_group'].items():
            obj.add_shape(get_shape_from_dict(body,v))

        if data['camera'] :
            obj.camera = SLCamera(**data['camera']['data'])
        obj.get_snapshot()
        return obj
        

    def __init__(self,
                 body:SLBody=None,
                 obj_id= None,
                 camera=None):
        if  obj_id is None:
            self.id = gen_id()
        else:
            self.id = obj_id
        self.camera = camera
        self.body: SLBody = body
        self.shape_group: SLShapeGroup = SLShapeGroup()
        self.energy = 100
        self.health = 100

    def get_energy(self):
        return self.energy
    
    def set_energy(self,energy):
        self.energy = energy

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

    def get_snapshot(self):
        data = get_dict_snapshot(self, exclude_keys={'body'})
        data['body'] = self.body.__getstate__()
        return data

    def load_snapshot(self, data):
        load_dict_snapshot(self, data, exclude_keys={"body"})
        body_data = state_to_dict(data['body'])

        # This breaks things
        #self.body.__setstate__(data['body'])
        self.body.position = body_data['general']['position']
        self.body.force = body_data['general']['force']
        self.body.velocity = body_data['general']['velocity']
        self.body.torque = body_data['general']['torque']


def build_event_from_dict(data_dict):
    cls = globals()[data_dict['_type']]
    event = cls(**data_dict['data'])
    return event

class SLEvent(SLBase):

    def __init__(self, id=None):
        if id == None:
            self.id = gen_id()
        else:
            self.id = id

    def get_id(self):
        return self.id


class SLRewardEvent(SLEvent):

    def __init__(self, reward=0, id = None):
        super(SLRewardEvent, self).__init__(id)
        self.reward = reward


class SLPlayerCollisionEvent(SLEvent):

    def __init__(self, player_id, obj, id=None):
        super(SLPlayerCollisionEvent,self).__init__(id)
        self.player_id = player_id
        self.obj = obj


class SLMechanicalEvent(SLEvent):

    def __init__(self, obj_id: str,
                 direction: SLVector ,
                 orientation_diff: float = 0.0,
                 id=None):
        super(SLMechanicalEvent,self).__init__(id)
        self.obj_id = obj_id
        self.direction = direction
        self.orientation_diff = orientation_diff

    def __str__(self):
        return "obj_id: %s, direction: %s" % (self.obj_id, self.direction)


class SLMoveEvent(SLEvent):

    def __init__(self, obj_id: str,
                 direction: SLVector,
                 orientation_diff: float = 0.0, 
                 id=None):
        super(SLMoveEvent, self).__init__(id)
        self.obj_id = obj_id
        self.direction = direction
        self.orientation_diff = orientation_diff

    def __str__(self):
        return "obj_id: %s, direction: %s" % (self.obj_id, self.direction)


class SLAdminEvent(SLEvent):

    def __init__(self, value, id=None):
        super(SLAdminEvent, self).__init__(id)
        self.value = value

    def __str__(self):
        return "%s" % self.value
# http://www.dcs.gla.ac.uk/~pat/52233/slides/Geometry1x1.pdf


class SLViewEvent(SLEvent):

    def __init__(self, obj_id: str,
                 distance_diff: float = 0,
                 center_diff: SLVector = SLVector.zero(),
                 orientation_diff: float = 0.0, 
                 id=None):
        super(SLViewEvent, self).__init__(id)
        self.obj_id = obj_id
        self.distance_diff = distance_diff
        self.center_diff = center_diff
        self.angle_diff = orientation_diff