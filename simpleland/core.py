from typing import Any, Dict, List

import numpy
import pygame
import pymunk
from pymunk import Vec2d

from .common import (PhysicsConfig, SLBody, SLCircle, SLClock, SLVector, SLSpace,
                               SLEvent, SLLine, SLObject, SLPolygon,
                               SLMoveEvent, SLMechanicalEvent, SLPlayerCollisionEvent, SLViewEvent, Singleton)
from .player import SLPlayer
from .utils import gen_id
from .object_manager import SLObjectManager

class SLEventManager(metaclass=Singleton):
    """
    Contains references to all game events
    """

    def __init__(self):
        self.__events: Dict[str, SLEvent] = {}

    def add_update(self, e: SLEvent):
        self.__events[e.get_id()] = e

    def add_events(self, events: List[SLEvent]):
        for e in events:
            self.add_update(e)

    def get_events(self):
        return list(self.__events.values())

    def get_event_by_id(self, id):
        return self.__events[id]

    def remove_event_by_id(self, id):
        del self.__events[id]

    def get_snapshot(self):
        results = {}
        for k,o in self.__events.items():
            results[k]= o.get_snapshot()
        return results

    def load_snapshot(self,data):
        for k,o in data.items():
            self.__events[k].load_snapshot(o)

class SLPhysicsEngine:
    """
    Handles physics events and collision
    """

    def __init__(self):
        self.clock = SLClock()
        self.config = PhysicsConfig()
        self.space = SLSpace()
        self.space.damping = self.config.space_damping
        self.events = []

    def enable_collision_detection(self, callback):


        h = self.space.add_collision_handler(1, 1)

        def begin(arbiter, space, data):
            callback(arbiter,space,data)
            return True

        h.begin = begin

    def add_event(self, event: SLEvent):
        self.events.append(event)

    def clear_events(self):
        self.events = []

    def pull_events(self) -> List[SLEvent]:
        events = self.events
        self.events = []
        return events

    def add_object(self, obj: SLObject):
        self.space.add(obj.get_body(), obj.get_shapes())

    def add_static_object(self, obj: SLObject):
        self.space.add(obj.get_shapes())

    def process_mechanical_event(self, e: SLMechanicalEvent) -> List[SLEvent]:
        direction_delta = e.direction * self.config.velocity_multiplier * self.config.clock_multiplier
        body = e.obj.get_body()

        direction_delta = direction_delta.rotated(-1 * body.angle)
        body.apply_impulse_at_world_point(direction_delta, body.position)
        body.angular_velocity += e.orientation_diff * self.config.orientation_multiplier

        return []

    def process_move_event(self, e: SLMoveEvent) -> List[SLEvent]:
        direction_delta = e.direction * self.config.velocity_multiplier * self.config.clock_multiplier
        body = e.obj.get_body()

        direction_delta = direction_delta.rotated(-1 * body.angle)
        body.position += direction_delta
        body.angle += e.orientation_diff * self.config.orientation_multiplier
        return []

    def process_view_event(self, e: SLViewEvent):
        e.object.get_camera().distance += e.distance_diff
        e.object.get_camera().angle = e.angle_diff
        return []

    def update(self, event_manager: SLEventManager, object_manager: SLObjectManager):
        # self.get_collision_events(event_store,object_manager)
        new_events: List[SLEvent] = []
        done = False
        events_to_remove: List[SLEvent] = []
        for event in event_manager.get_events():
            result_events: List[SLEvent] = []
            if type(event) == SLMechanicalEvent:
                result_events = self.process_mechanical_event(event)
                events_to_remove.append(event)
            elif type(event) == SLMoveEvent:
                result_events = self.process_move_event(event)
                events_to_remove.append(event)
            elif type(event) == SLViewEvent:
                result_events = self.process_view_event(event)
                events_to_remove.append(event)

            new_events.extend(result_events)

            # Check if process time is exceeded?
            if done:
                break
        for event in events_to_remove:
            event_manager.remove_event_by_id(event.get_id())

        # After processed so we don't just continue processing events for ever
        event_manager.add_events(new_events)

        # Update physics
        fps = self.config.fps
        dt = 1. / fps
        self.space.step(dt)

        self.clock.tick(fps)


# class SLUniverse(object):

#     def __init__(self, physics_engine: SLPhysicsEngine):
#         """

#         """
        
#         self.physics_engine = physics_engine
#         self.direction: Vec2d = None  # TODO: Temp for testing


    # def get_direction(self)->Vec2d:
    #     return numpy.array([self.direction.x, self.direction.y])




# class SLViewState(object):

#     def __init__(self, obj: SLObject, universe: SLUniverse):
#         """

#         """
#         self.obj = obj
#         self.universe = universe
