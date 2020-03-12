import json
from typing import List, Set
from uuid import UUID

from pymunk import Vec2d

from .common import (SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock, SLExtendedObject)
from .physics_engine import SLPhysicsEngine
from .event_manager import (SLEvent, SLAdminEvent, SLEventManager, SLMechanicalEvent,
                            SLPeriodicEvent, SLViewEvent)
from .object_manager import SLObjectManager
from .player import SLPlayer, SLPlayerManager
from .renderer import SLRenderer
from .utils import gen_id
from .config import GameConfig

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

class SLGame:

    def __init__(self, config=None):
        self.config = GameConfig()
        self.clock = SimClock()
        self.object_manager = SLObjectManager(200)
        self.physics_engine = SLPhysicsEngine(self.clock, self.config)
        self.player_manager = SLPlayerManager(self.config)
        self.event_manager = SLEventManager(self.config)
        self.renderer = SLRenderer()
        self.game_state = "RUNNING"
        self.step_counter = 0
        self.tick_rate = 60#steps per second
        self.physics_tick_rate = self.tick_rate  #steps per second
        self.id = gen_id()
        self.last_position_lookup = {}

    def change_game_state(self, new_state):
        self.game_state = new_state

    def create_snapshot(self,last_update_timestamp):
        snapshot_timestamp = self.clock.get_time()
        om_snapshot = self.object_manager.get_snapshot_update(last_update_timestamp)
        # print("SNAPSHOT: {} SIZE: {}".format(last_update_timestamp,len(om_snapshot)))
        pm_snapshot = self.player_manager.get_snapshot() # TODO, updates since
        return snapshot_timestamp, {
            'object_manager':om_snapshot,
            'player_manager':pm_snapshot,
            'snapshot_timestamp':snapshot_timestamp}
    
    def load_snapshot(self,snapshot):
        snapshot_timestamp = snapshot['snapshot_timestamp']
        if 'object_manager' in snapshot:
            self.object_manager.load_snapshot_from_data(
                snapshot_timestamp,
                snapshot['object_manager'])
        if 'player_manager' in snapshot:
            self.player_manager.load_snapshot(snapshot['player_manager'])

    def process_events(self):
        new_events = []
        events_to_remove = []
        for e in self.event_manager.get_events():
            result_events = []
            if type(e) == SLAdminEvent:
                e: SLAdminEvent = e
                if e.value == 'QUIT':
                    self.change_game_state("QUITING")
                    events_to_remove.append(e)
            elif type(e) == SLMechanicalEvent:
                result_events = self.process_mechanical_event(e)
                events_to_remove.append(e)
            elif type(e) == SLViewEvent:
                result_events = self.process_view_event(e)
                events_to_remove.append(e)
            elif type(e) == SLPeriodicEvent:
                e: SLPeriodicEvent = e
                result_events, remove_event = e.run(self.clock.get_time(),self.object_manager)
                # NOT REMOVED
                if remove_event:
                    events_to_remove.append(e)

            new_events.extend(result_events)

        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())

        self.event_manager.add_events(new_events)

    def process_mechanical_event(self, e: SLMechanicalEvent) -> List[SLEvent]:
        direction_delta = e.direction * self.physics_engine.config.velocity_multiplier * self.physics_engine.config.clock_multiplier
        t, obj = self.get_object_manager().get_latest_by_id(e.obj_id)
        if obj is None:
            return []
        obj.set_last_change(self.clock.get_time())
        body = obj.get_body()

        direction_delta = direction_delta.rotated(-1 * body.angle)
        body.apply_impulse_at_world_point(direction_delta, body.position)
        # body.angle += 0.1 * (e.orientation_diff * self.physics_engine.config.orientation_multiplier)
        body.angular_velocity += (e.orientation_diff * self.physics_engine.config.orientation_multiplier)

        if body.angular_velocity > 2:
            body.angular_velocity = 2
        elif body.angular_velocity < -2:
            body.angular_velocity = -2
        return []

    def process_view_event(self, e: SLViewEvent):
        t, obj = self.get_object_manager().get_latest_by_id(e.obj_id)
        obj.set_last_change(self.clock.get_time())
        obj.get_camera().distance += e.distance_diff
        return []

    def apply_physics(self):

        self.physics_engine.update(self.physics_tick_rate)

        # Check for changes in position or angle and log change time
        new_position_lookup = {}
        for k,o in self.object_manager.get_objects_latest().items():
            angle = o.get_body().angle
            position = o.get_body().position
            current_position = {'angle':angle,'position':position}

            last_position = self.last_position_lookup.get(k,None)
            if last_position is not None:
                if ((last_position['angle'] != current_position['angle'] ) or
                (last_position['position'] != current_position['position'])):
                    o.set_last_change(self.clock.get_time())
            new_position_lookup[k] = current_position
        self.last_position_lookup = new_position_lookup
            

    def add_object(self,obj):
        obj.set_last_change(self.clock.get_time())
        self.object_manager.add(self.clock.get_time(), obj)
        self.physics_engine.add_object(obj)

    def remove_object(self,obj:SLObject):
        # Marks as deleted, but not removed completely
        obj.delete()
        obj.set_last_change(self.clock.get_time())
        self.physics_engine.remove_object(obj)
        print("Deleting:{}".format(obj.is_deleted))

    def tick(self):
        self.clock.tick(self.tick_rate)

    def add_player(self, player: SLPlayer):
        self.player_manager.add_player(player)

    def get_object_manager(self) -> SLObjectManager:
        return self.object_manager