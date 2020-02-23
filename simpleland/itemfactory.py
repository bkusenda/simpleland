from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (FollowBehaviour, PhysicsConfig, SLBody,
                               SLCircle, SLClock, SLEvent, SLLine,
                               SLMechanicalEvent, SLMoveEvent, SLObject,
                               SLPlayerCollisionEvent, SLPoint, SLPolygon,
                               SLSpace, SLVector, SLViewEvent)
from .player import SLPlayer
from .utils import gen_id


class SLShapeFactory(object):

    @classmethod
    def attach_circle(cls, obj: SLObject, radius=5):
        body = obj.get_body()
        inertia = pymunk.moment_for_circle(body.mass, 0, radius, (0, 0))
        body.moment = inertia
        circle = SLCircle(body, radius, (0, 0))
        shapes = [circle]
        obj.set_shapes(shapes)

    @classmethod
    def attach_circle2(cls, obj: SLObject, radius=5):
        body = obj.get_body()
        inertia = pymunk.moment_for_circle(body.mass, 0, radius, (0, 0))
        body.moment = inertia
        circle = SLCircle(body, radius, (0, 0))
        circle.elasticity = 0.1
        circle.friction = 0.4
        shapes = [circle]
        obj.set_shapes(shapes)

    @classmethod
    def attach_square(cls, obj: SLObject, thickness=0, side_length=12):
        body = obj.get_body()
        p1 = SLPoint(-1 * side_length, -1 * side_length)
        p2 = SLPoint(-1 * side_length, side_length)
        p3 = SLPoint(side_length, side_length)
        p4 = SLPoint(side_length, -1 * side_length)
        l1 = SLLine(body, p1, p2, thickness)
        l2 = SLLine(body, p2, p3, thickness)
        l3 = SLLine(body, p3, p4, thickness)
        l4 = SLLine(body, p4, p1, thickness)
        shapes = [l1, l2, l3, l4]
        obj.set_shapes(shapes)

    @classmethod
    def attach_psquare(cls, obj: SLObject, side_length=12):
        body = obj.get_body()
        p1 = SLPoint(-1 * side_length, -1 * side_length)
        p2 = SLPoint(-1 * side_length, side_length)
        p3 = SLPoint(side_length, side_length)
        p4 = SLPoint(side_length, -1 * side_length)
        p = SLPolygon(body, vertices=[p1, p2, p3, p4])
        obj.set_shapes([p])

    @classmethod
    def attach_triangle(cls, obj: SLObject, side_length=12):
        body = obj.get_body()
        p1 = SLPoint(0, side_length)
        p2 = SLPoint(side_length / 2, 0)
        p3 = SLPoint(-1 / 2 * side_length, 0)
        p = SLPolygon(body, vertices=[p1, p2, p3])
        obj.set_shapes([p])


class SLItemFactory(object):

    @classmethod
    def border(cls, body=SLBody(), position=SLPoint(0, 0), size=5):
        obj = SLObject(body)
        obj.set_position(position=position)
        SLShapeFactory.attach_square(obj, side_length=size)
        return obj

    @classmethod
    def box(cls, body=SLBody(), position=SLPoint(0, 0), size=5):
        obj = SLObject(body)
        obj.set_position(position=position)
        SLShapeFactory.attach_psquare(obj, side_length=size)
        return obj

    @classmethod
    def circle(cls, body=SLBody(), position=SLPoint(0, 0), radius=5):
        obj = SLObject(body)
        obj.set_position(position=position)
        SLShapeFactory.attach_circle(obj, radius=radius)
        return obj

    @classmethod
    def triangle(cls, body=SLBody(), position=SLPoint(0, 0), size=5):
        obj = SLObject(body)
        obj.set_position(position=position)
        SLShapeFactory.attach_triangle(obj, side_length=size)
        return obj
