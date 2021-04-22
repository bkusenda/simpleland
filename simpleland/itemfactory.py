from typing import Any, Dict, List

import pymunk
from pymunk import Vec2d

from .common import (Body,
                     Circle, Line,
                     Polygon,
                     Space, Vector, COLLISION_TYPE)
from .object import GObject
from .player import Player
from .utils import gen_id
import math


class ShapeFactory:

    @classmethod
    def attach_circle(cls, obj: GObject, radius=5, pos=(0, 0), collision_type=COLLISION_TYPE['default'], friction=0.2):
        body = obj.get_body()
        inertia = pymunk.moment_for_circle(body.mass, 0, radius, pos)
        body.moment = inertia
        circle = Circle(body, radius=radius, offset=pos)
        circle.friction = friction
        obj.set_image_dims(radius*2,radius*2)
        obj.add_shape(circle, collision_type=collision_type)

    @classmethod
    def attach_rectangle(cls, obj: GObject, width=32, height=32, collision_type=COLLISION_TYPE['default']):
        body = obj.get_body()
        h = height/2
        w = width/2
        p1 = Vector(-w, -1 * h)
        p2 = Vector(-1 * w, h)
        p3 = Vector(w, h)
        p4 = Vector(w, -1 * h)
        obj.set_image_dims(width,height)
        p = Polygon(body, vertices=[p1, p2, p3, p4])
        obj.add_shape(p, collision_type=collision_type)

    @classmethod
    def attach_triangle(cls, obj: GObject, side_length=12, collision_type=COLLISION_TYPE['default']):
        body = obj.get_body()
        p1 = Vector(0, side_length)
        p2 = Vector(side_length / 2, 0)
        p3 = Vector(-1 / 2 * side_length, 0)
        obj.set_image_dims(side_length/2,side_length/2)
        p = Polygon(body, vertices=[p1, p2, p3])
        obj.add_shape(p, collision_type=collision_type)

    @classmethod
    def attach_poly(cls, obj: GObject, size=10, num_sides=3, collision_type=COLLISION_TYPE['default']):
        body = obj.get_body()
        verts = []
        for i in range(num_sides):
            angle = math.pi + 2.0 * math.pi * i / num_sides
            x = (size/2.0) * math.sin(angle)
            y = (size/2.0) * math.cos(angle)
            verts.append(Vector(x, y))

        p = Polygon(body, vertices=verts)
        obj.set_image_dims(size,size)
        obj.add_shape(p, collision_type=collision_type)

    @classmethod
    def attach_line_array(cls, obj: GObject, length=3, num=12, thickness=1, collision_type=COLLISION_TYPE['default']):
        body = obj.get_body()
        for i in range(num):
            angle = math.pi + 2.0 * math.pi * i / num
            x = length * math.sin(angle)
            y = length * math.cos(angle)
            l = Line(body, Vector(0, 0), Vector(x, y), thickness)
            obj.add_shape(l, collision_type=collision_type)

    @classmethod
    def attach_square(cls, obj: GObject, thickness=0, side_length=12, collision_type=COLLISION_TYPE['default'], friction=0.2, elasticity=1):
        body = obj.get_body()
        p1 = Vector(0, 0)
        p2 = Vector(0, side_length)
        p3 = Vector(side_length, side_length)
        p4 = Vector(side_length, 0)
        obj.set_image_dims(side_length,side_length)

        l1 = Line(body, p1, p2, thickness)
        l2 = Line(body, p2, p3, thickness)
        l3 = Line(body, p3, p4, thickness)
        l4 = Line(body, p4, p1, thickness)
        shapes = [l1, l2, l3, l4]
        for s in shapes:
            s.friction = friction
            s.elasticity = elasticity
        for s in shapes:
            obj.add_shape(s, collision_type=collision_type)

    @classmethod
    def attach_psquare(cls, obj: GObject, side_length=12, collision_type=COLLISION_TYPE['default']):
        body = obj.get_body()
        p1 = Vector(-1 * side_length, -1 * side_length)
        p2 = Vector(-1 * side_length, side_length)
        p3 = Vector(side_length, side_length)
        p4 = Vector(side_length, -1 * side_length)
        p = Polygon(body, vertices=[p1, p2, p3, p4])
        obj.add_shape(p, collision_type=collision_type)

class ItemFactory:

    @classmethod
    def circle(cls, body=None, position=Vector(0, 0), radius=5, collision_type=COLLISION_TYPE['default']):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_circle(obj, radius=radius, collision_type=collision_type)
        return obj

    @classmethod
    def triangle(cls, body=None, position=Vector(0, 0), size=5, collision_type=COLLISION_TYPE['default']):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_triangle(obj, side_length=size, collision_type=collision_type)
        return obj


    @classmethod
    def border(cls, body=None, position=Vector(0, 0), size=5, thickness=3, collision_type=COLLISION_TYPE['default']):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_square(obj, side_length=size, thickness=thickness, collision_type=collision_type)
        return obj

    @classmethod
    def box(cls, body=None, position=Vector(0, 0), size=5, collision_type=COLLISION_TYPE['default']):
        obj = GObject(body)
        obj.set_position(position=position)
        ShapeFactory.attach_psquare(obj, side_length=size, collision_type=collision_type)
        return obj