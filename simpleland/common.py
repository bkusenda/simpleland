import pymunk
import pygame
from pygame.time import Clock
from .utils import gen_id
from typing import List

class PlayerConfig(object):

    def __init__(self):
        """

        """


class PhysicsConfig:
    def __init__(self):
        self.velocity_multiplier = 10.0
        self.orientation_multiplier = 2.0
        self.space_damping = 0.5
        self.fps = 60
        self.clock_multiplier = 1

class GameConfig(object):

    def __init__(self):
        self.move_speed = 2
        self.keep_moving = 0
        self.clock_factor = 1.0


SLClock: Clock = pygame.time.Clock

SLPoint = pymunk.Vec2d

SLVector = pymunk.Vec2d

SLSpace = pymunk.Space

SLShape = pymunk.Shape


# SLBody = pymunk.Body


class SLBody(pymunk.Body):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.obj = None

    def attach_object(self, obj):
        self.obj = obj

    def get_object(self):
        return self.obj


SLCircle = pymunk.Circle

SLLine = pymunk.Segment

SLPolygon = pymunk.Poly


class SLViewer:

    def __init__(self, distance=30):
        self.distance = distance  # zoom

    def get_distance(self):
        return self.distance


class Behaviour:

    def __init__(self):
        """

        """

class SLObject:
    def __init__(self, body=SLBody(),
                 config=None,
                 collision_func=None,
                 update_func=None,
                 viewer=SLViewer()):
        """

        """
        self.__id = gen_id()

        self.__viewer = viewer
        self.behavior_list: List[Behaviour] = []
        self.__body: SLBody = body
        self.__shapes: List[SLShape] = []
        self.__energy = 100
        self.__health = 100
        self.__config = config
        self.__collision_func = collision_func
        self.__update_func = update_func

    def set_collision_type(self, collision_type):
        for shape in self.__shapes:
            shape.collision_type = collision_type

    def get_body(self) -> SLBody:
        return self.__body

    def get_id(self):
        return self.__id

    def set_position(self, position: SLVector):
        self.get_body().position = position

    def set_shapes(self, shapes):
        self.__shapes = shapes

    def get_shapes(self):
        return self.__shapes

    def get_viewer(self) -> SLViewer:
        return self.__viewer

    def attach_behavior(self, behaviour: Behaviour):
        self.behavior_list.append(behaviour)
    
    def snapshot_data(self):
        data = self.__dict__
        return data


class FollowBehaviour(Behaviour):

    def __init__(self, obj: SLObject):
        super().__init__()
        self.obj = obj


class SLEvent(object):

    def __init__(self):
        """

        """
        self.__id = gen_id("event")

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
        
