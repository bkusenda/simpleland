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
        elif v is None or isinstance(v, (int, float, str)):
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

class SLBody(SLBase, pymunk.Body):

    @classmethod
    def build_from_dict(cls,dict_data):
        print(dict_data)
        if dict_data['body_type'] == 2:
            print("here")
            body = SLBody(body_type = pymunk.Body.STATIC)
        else:
            body = SLBody(dict_data['data']['init'])
        return body.load_snapshot(dict_data)

    def __init__(self,*args, **kwargs):
        self.id = gen_id()
        super(SLBody,self).__init__(*args,**kwargs)

    def get_id(self):
        return self.id

    def get_snapshot(self):
        return {
            "_type":type(self).__name__,
            "body_type": self.body_type,
            "data":self.__getstate__()}

    def load_snapshot(self, data):
        self.__setstate__(data['data'])

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

    def get_snapshot(self, exclude_keys={'_body'}):
        pass

    def load_snapshot(self, data):
        pass

    def get_common_info(self):
        dict_data = get_dict_snapshot(self, exclude_keys={"_body"})
        params={}
        params['sensor'] = self.sensor
        params['collision_type'] = self.collision_type
        params['filter'] = self.filter
        params['elasticity'] = self.elasticity
        params['friction'] = self.friction
        params['surface_velocity'] = self.surface_velocity
        dict_data['params'] = params
        return dict_data


class SLLine(SLShape, pymunk.Segment):

    def __init__(self,body:SLBody,a,b,radius,**kwargs):
        self.body_id = body.get_id()
        pymunk.Segment.__init__(self,body,a,b,radius, **kwargs)
        SLShape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'].update({
                    "a":self.a,
                    "b":self.b,
                    "radius": self.radius})
        return data
        
class SLPolygon(SLShape, pymunk.Poly):

    def __init__(self, body, vertices,**kwargs):
        self.body_id = body.get_id()
        pymunk.Poly.__init__(self,body, vertices,**kwargs)
        SLShape.__init__(self)
    
    def get_snapshot(self):
        data = self.get_common_info()
        data['params'].update({
                "vertices":[v for v in self.get_vertices()],
            })
        return data

class SLCircle(SLShape, pymunk.Circle):

    def __init__(self, *args,**kwargs):
        pymunk.Circle.__init__(self,*args,**kwargs)
        SLShape.__init__(self)

    def get_snapshot(self):
        data = self.get_common_info()
        data['params'].update({"radius": self.radius})
        return data

def get_shape_from_dict(body,dict_data):
    cls = globals()[dict_data['_type']]
    instance = cls(body, **dict_data['data']['params'])
    load_dict_snapshot(instance,dict_data['data'])
    return instance


class SLShapeGroup(SLBase):


    @classmethod
    def build_from_dict(cls,body,dict_data):
        shape_group = SLShapeGroup()
        for k,v in dict_data.items():
            shape_group.add(get_shape_from_dict(body,v))
        return shape_group

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

        body = SLBody.build_from_dict(data['body'])
        shape_group = SLShapeGroup.build_from_dict(body,data['shape_group'])
        obj = SLObject()
        obj.load_snapshot(dict_data)
        obj.body = body
        obj.shape_group = shape_group
        return obj
        

    def __init__(self,
                 body=None,
                 camera=None):
        """

        """
        self.id = gen_id()
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


class SLEvent(SLBase):

    def __init__(self):
        """

        """
        self.__id = gen_id()

    def get_id(self):
        return self.__id


class SLRewardEvent(SLEvent):

    def __init__(self, puid, reward=0):
        super().__init__()
        self.puid = puid
        self.reward = reward


class SLPlayerCollisionEvent(SLEvent):

    def __init__(self, player_id, obj):
        super().__init__()
        self.player_id = player_id
        self.obj = obj


class SLMechanicalEvent(SLEvent):

    def __init__(self, obj: SLObject,
                 direction: SLVector = SLVector.zero(),
                 orientation_diff: float = 0.0):
        super().__init__()
        self.obj = obj
        self.direction = direction
        self.orientation_diff = orientation_diff

    def __str__(self):
        return "object: %s, direction: %s" % (self.obj, self.direction)


class SLMoveEvent(SLEvent):

    def __init__(self, obj: SLObject,
                 direction: SLVector = SLVector.zero(),
                 orientation_diff: float = 0.0):
        super().__init__()
        self.obj = obj
        self.direction = direction
        self.orientation_diff = orientation_diff

    def __str__(self):
        return "object: %s, direction: %s" % (self.obj, self.direction)


class SLAdminEvent(SLEvent):

    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self):
        return "%s" % self.value
# http://www.dcs.gla.ac.uk/~pat/52233/slides/Geometry1x1.pdf


class SLViewEvent(SLEvent):

    def __init__(self, obj: SLObject,
                 distance_diff: float = 0,
                 center_diff: SLVector = SLVector.zero(),
                 orientation_diff: float = 0.0):
        super().__init__()
        self.object = obj
        self.distance_diff = distance_diff
        self.center_diff = center_diff
        self.angle_diff = orientation_diff