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
from .common import build_event_from_dict

class SLEventManager(metaclass=Singleton):
    """
    Contains references to all game events
    """

    def __init__(self):
        self.events: Dict[str, SLEvent] = {}

    def add_update(self, e: SLEvent):
        self.events[e.get_id()] = e

    def add_events(self, events: List[SLEvent]):
        for e in events:
            self.add_update(e)

    def get_events(self):
        return list(self.events.values())

    def get_event_by_id(self, id):
        return self.events[id]

    def remove_event_by_id(self, id):
        del self.events[id]

    def clear(self):
        self.events: Dict[str, SLEvent] = {}

    def get_snapshot(self):
        results = {}
        for k,o in self.events.items():
            results[k]= o.get_snapshot()
        return results

    def load_snapshot(self,data):
        for k,e_data in data.items():
            if k in self.events:
                self.events[k].load_snapshot(e_data)
            else:
                self.events[k] = build_event_from_dict(e_data)

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

        self.dt = 1. / self.config.fps

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

    def remove_object(self,obj):
        self.space.remove(obj.get_shapes())
        self.space.remove(obj.get_body())

    def process_mechanical_event(self, e: SLMechanicalEvent, om: SLObjectManager) -> List[SLEvent]:
        direction_delta = e.direction * self.config.velocity_multiplier * self.config.clock_multiplier
        obj = om.get_by_id(e.obj_id)
        body = obj.get_body()

        direction_delta = direction_delta.rotated(-1 * body.angle)
        body.apply_impulse_at_world_point(direction_delta, body.position)
        body.angular_velocity += e.orientation_diff * self.config.orientation_multiplier
        return []

    def process_move_event(self, e: SLMoveEvent,om: SLObjectManager) -> List[SLEvent]:
        direction_delta = e.direction * self.config.velocity_multiplier * self.config.clock_multiplier
        obj = om.get_by_id(e.obj_id())
        body = obj.get_body()

        direction_delta = direction_delta.rotated(-1 * body.angle)
        body.position += direction_delta
        body.angle += e.orientation_diff * self.config.orientation_multiplier
        return []

    def process_view_event(self, e: SLViewEvent,om: SLObjectManager):
        obj = om.get_by_id(e.obj_id)
        obj.get_camera().distance += e.distance_diff
        obj.get_camera().angle = e.angle_diff
        return []

    def apply_events(self, em: SLEventManager, om: SLObjectManager, remove_processed = True):
        # self.get_collision_events(event_store,object_manager)
        new_events: List[SLEvent] = []
        done = False
        events_to_remove: List[SLEvent] = []
        for event in em.get_events():
            result_events: List[SLEvent] = []
            if type(event) == SLMechanicalEvent:
                result_events = self.process_mechanical_event(event,om)
                events_to_remove.append(event)
            elif type(event) == SLMoveEvent:
                result_events = self.process_move_event(event,om)
                events_to_remove.append(event)
            elif type(event) == SLViewEvent:
                result_events = self.process_view_event(event,om)
                events_to_remove.append(event)

            new_events.extend(result_events)

            # Check if process time is exceeded?
            if done:
                break
        if remove_processed:
            for event in events_to_remove:
                em.remove_event_by_id(event.get_id())

        # After processed so we don't just continue processing events for ever
        em.add_events(new_events)


    def update(self, om: SLObjectManager):

        self.space.step(self.dt)
        self.clock.tick(self.config.fps)