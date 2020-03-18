import json
from typing import List, Set
from uuid import UUID

from pymunk import Vec2d

from .common import (SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock, SLExtendedObject)
from .physics_engine import SLPhysicsEngine
from .event_manager import (SLEvent, SLAdminEvent, SLEventManager, SLMechanicalEvent,
                            SLPeriodicEvent, SLViewEvent, SLSoundEvent, SLDelayedEvent, SLInputEvent)
from .object_manager import SLObjectManager
from .player import SLPlayer, SLPlayerManager
# from .renderer import SLRenderer
from .utils import gen_id
from .config import GameConfig, PhysicsConfig
import pygame


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

    def __init__(self, 
            physics_config: PhysicsConfig, 
            config:GameConfig):

        self.config = config
        self.physics_config = physics_config
        self.clock = SimClock()

        self.object_manager:SLObjectManager = None
        self.physics_engine:SLPhysicsEngine = None
        self.player_manager: SLPlayerManager = None
        self.event_manager: SLEventManager = None
        self.game_state = "RUNNING"
        self.step_counter = 0
        self.last_position_lookup = {}
        self.reset()

        self.tick_rate = self.config.tick_rate #steps per second
        self.physics_tick_rate = self.physics_config.tick_rate  #steps per second
        self.id = gen_id()
        self.pre_event_processing_callback = lambda game: []
        self.pre_physics_callback = lambda game: []
        self.input_event_callback = lambda event, game: []

    def reset(self):
        self.object_manager = SLObjectManager(200)
        self.physics_engine = SLPhysicsEngine(self.clock, self.physics_config)
        self.player_manager = SLPlayerManager()
        self.event_manager = SLEventManager()
        self.game_state = "RUNNING"
        self.step_counter = 0
        self.last_position_lookup = {}

    def change_game_state(self, new_state):
        self.game_state = new_state

    def set_input_event_callback(self, callback):
        self.input_event_callback = callback

    def set_pre_event_processing_callback(self, callback):
        self.pre_event_processing_callback = callback

    def set_pre_physics_callback(self, callback):
        self.pre_physics_callback = callback

    def create_snapshot(self,last_update_timestamp):
        snapshot_timestamp = self.clock.get_time()
        om_snapshot = self.object_manager.get_snapshot_update(last_update_timestamp)
        pm_snapshot = self.player_manager.get_snapshot() # TODO, updates since
        em_snapshot = self.event_manager.get_snapshot_for_client(last_update_timestamp)
        return snapshot_timestamp, {
            'om':om_snapshot,
            'pm':pm_snapshot,
            'em': em_snapshot,
            'timestamp':snapshot_timestamp,
            }
    
    def load_snapshot(self,snapshot):
        snapshot_timestamp = snapshot['timestamp']
        if 'om' in snapshot:
            self.object_manager.load_snapshot_from_data(
                snapshot_timestamp,
                snapshot['om'])
        if 'pm' in snapshot:
            self.player_manager.load_snapshot(snapshot['pm'])
        if 'em' in snapshot:
            self.event_manager.load_snapshot(snapshot['em'])

    def run_pre_event_processing(self):
        if self.pre_physics_callback is not None:
            events = self.pre_event_processing_callback(self)
            self.event_manager.add_events(events)

    def run_event_processing(self):
        new_events = []
        events_to_remove = []
        for e in self.event_manager.get_events():
            result_events = []
            if type(e) == SLAdminEvent:
                e: SLAdminEvent = e
                if e.value == 'QUIT':
                    self.change_game_state("QUITING")
                    events_to_remove.append(e)
            elif type(e) == SLInputEvent:
                result_events = self.input_event_callback(e,self)
                events_to_remove.append(e)
            elif type(e) == SLMechanicalEvent:
                result_events = self._process_mechanical_event(e)
                events_to_remove.append(e)
            elif type(e) == SLViewEvent:
                result_events = self._process_view_event(e)
                events_to_remove.append(e)

            elif type(e) == SLDelayedEvent:
                e: SLDelayedEvent = e
                result_events, delete_event = e.run(self.clock.get_time(),self.object_manager)
                if delete_event:
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

    def run_pre_physics_processing(self):
        if self.pre_physics_callback is not None:
            events = self.pre_physics_callback(self)
            self.event_manager.add_events(events)

    def run_physics_processing(self):

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
    
    def tick(self):
        self.clock.tick(self.tick_rate)     

    def add_player(self, player: SLPlayer):
        self.player_manager.add_player(player) 

    def add_object(self,obj):
        obj.set_last_change(self.clock.get_time())
        self.object_manager.add(self.clock.get_time(), obj)
        self.physics_engine.add_object(obj)

    def remove_object(self,obj:SLObject):
        # Marks as deleted, but not removed completely
        obj.delete()
        obj.set_last_change(self.clock.get_time())
        self.physics_engine.remove_object(obj)
        for p in self.player_manager.players_map.values():
            if obj.get_id() == p.get_object_id():
                p.obj_id = None
        print("Deleting:{}".format(obj.is_deleted))

    def get_sound_events(self,render_time):
        events_to_remove = []
        sound_ids = []
        for e in self.event_manager.get_events():
            if e.is_client_event and not e.is_realtime_event:
                result_events = []
                if type(e) == SLSoundEvent:
                    e:SLSoundEvent = e
                    sound_ids.append(e.sound_id)
                    events_to_remove.append(e)
        
        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())
        return sound_ids
    
    def _process_mechanical_event(self, e: SLMechanicalEvent) -> List[SLEvent]:
        # TODO: use callback instead
        direction_delta = e.direction * self.physics_engine.config.velocity_multiplier * self.physics_engine.config.clock_multiplier
        t, obj = self.object_manager.get_latest_by_id(e.obj_id)
        if obj is None:
            return []
        obj.set_last_change(self.clock.get_time())
        body = obj.get_body()

        direction_delta = direction_delta.rotated(body.angle)
        body.apply_impulse_at_world_point(direction_delta, body.position)
        # body.angle += 0.1 * (e.orientation_diff * self.physics_engine.config.orientation_multiplier)
        body.angular_velocity += (e.orientation_diff * self.physics_engine.config.orientation_multiplier)

        if body.angular_velocity > 2:
            body.angular_velocity = 2
        elif body.angular_velocity < -2:
            body.angular_velocity = -2
        return []

    def _process_view_event(self, e: SLViewEvent):
        # TODO: use callback instead
        t, obj = self.object_manager.get_latest_by_id(e.obj_id)
        obj.set_last_change(self.clock.get_time())
        obj.get_camera().distance += e.distance_diff
        return []