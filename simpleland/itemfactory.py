from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (Body,
                               Circle, Clock, Line,
                            
                               Polygon,
                               Space, Vector)
from .object import GObject
from .player import Player
from .utils import gen_id


class ShapeFactory(object):

    @classmethod
    def attach_circle(cls, obj: GObject, radius=5, pos = (0,0)):
        body = obj.get_body()
        inertia = pymunk.moment_for_circle(body.mass, 0, radius, pos)
        body.moment = inertia
        circle = Circle(body, radius = radius, offset= pos)
        obj.add_shape(circle)
        body.size =  (radius * 2,radius *2)

    @classmethod
    def attach_circle2(cls, obj: GObject, radius=5, pos = (0,0)):
        body = obj.get_body()
        inertia = pymunk.moment_for_circle(body.mass, 0, radius, (0, 0))
        body.moment = inertia
        circle = Circle(body, radius, offset=pos)
        circle.elasticity = 0.1
        circle.friction = 0.4
        obj.add_shape(circle)
        body.size = (radius * 2,radius *2)

    @classmethod
    def attach_square(cls, obj: GObject, thickness=0, side_length=12):
        body = obj.get_body()
        p1 = Vector(-1 * side_length, -1 * side_length)
        p2 = Vector(-1 * side_length, side_length)
        p3 = Vector(side_length, side_length)
        p4 = Vector(side_length, -1 * side_length)
        l1 = Line(body, p1, p2, thickness)
        l2 = Line(body, p2, p3, thickness)
        l3 = Line(body, p3, p4, thickness)
        l4 = Line(body, p4, p1, thickness)
        body.size = (side_length,side_length)
        shapes = [l1, l2, l3, l4]
        for s in shapes:
            obj.add_shape(s)

    @classmethod
    def attach_psquare(cls, obj: GObject, side_length=12):
        body = obj.get_body()
        body.size = (side_length,side_length)
        p1 = Vector(-1 * side_length, -1 * side_length)
        p2 = Vector(-1 * side_length, side_length)
        p3 = Vector(side_length, side_length)
        p4 = Vector(side_length, -1 * side_length)
        p = Polygon(body, vertices=[p1, p2, p3, p4])
        obj.add_shape(p)

    @classmethod
    def attach_rectangle(cls, obj: GObject, width=1, height=3):
        body = obj.get_body()
        body.size = (width,height)
        h = height/2
        w = width/2
        p1 = Vector(-1 * w, -1 * h)
        p2 = Vector(-1 * w,h)
        p3 = Vector(w, h)
        p4 = Vector(w, -1 * h)
        p = Polygon(body, vertices=[p1, p2, p3, p4])
        obj.add_shape(p)

    @classmethod
    def attach_triangle(cls, obj: GObject, side_length=12):
        body = obj.get_body()
        p1 = Vector(0, side_length)
        p2 = Vector(side_length / 2, 0)
        p3 = Vector(-1 / 2 * side_length, 0)
        p = Polygon(body, vertices=[p1, p2, p3])
        obj.add_shape(p)
        body.size = (side_length,side_length)


class ItemFactory(object):

    @classmethod
    def border(cls, body=None, position=Vector(0, 0), size=5):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_square(obj, side_length=size)
        return obj

    @classmethod
    def box(cls, body=None, position=Vector(0, 0), size=5):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_psquare(obj, side_length=size)
        return obj

    @classmethod
    def circle(cls, body=None, position=Vector(0, 0), radius=5):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_circle(obj, radius=radius)
        return obj

    @classmethod
    def triangle(cls, body=None, position=Vector(0, 0), size=5):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_triangle(obj, side_length=size)
        return obj
