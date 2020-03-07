import json
from typing import List, Set
from uuid import UUID

from pymunk import Vec2d

from .common import (PhysicsConfig, SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock)
from .core import SLPhysicsEngine
from .event_manager import (SLEvent, SLAdminEvent, SLEventManager, SLMechanicalEvent,
                            SLPeriodicEvent, SLViewEvent)
from .object_manager import SLObjectManager
from .player import SLPlayer, SLPlayerManager
from .renderer import SLRenderer
from .utils import gen_id


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

    def __init__(self):
        self.clock = SimClock()
        self.object_manager = SLObjectManager()
        self.physics_engine = SLPhysicsEngine(self.clock)
        self.player_manager = SLPlayerManager()
        self.event_manager = SLEventManager()
        self.renderer = SLRenderer()
        self.game_state = "NOT_READY"
        self.step_counter = 0
        self.id = gen_id()

    def change_game_state(self, new_state):
        self.game_state = new_state
        return True

    def start(self):
        if self.game_state == "NOT_READY":
            self.change_game_state("READY")
        else:
            print("State must be NOT_READY, current state is %s" % self.game_state)
        self.change_game_state("RUNNING")
    
    def update_game_state(self,snapshot):
        if snapshot is None:
            return

        if 'object_manager' in snapshot:
            #self.game.object_manager.clear_objects()
            new_objs, removed_objs = self.object_manager.load_snapshot(snapshot['object_manager'])
            for obj in removed_objs:
                self.purge_object(obj)
                #self.physics_engine.remove_object(obj)
            
            for obj in new_objs:
                self.physics_engine.add_object(obj)
        if 'player_manager' in snapshot:
            self.player_manager.load_snapshot(snapshot['player_manager'])

    def process_all_events(self, game_time):
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
                result_events, remove_event = e.run(game_time,self.object_manager)
                # NOT REMOVED
                if remove_event:
                    events_to_remove.append(e)

            new_events.extend(result_events)

        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())

        self.event_manager.add_events(new_events)

    def process_mechanical_event(self, e: SLMechanicalEvent) -> List[SLEvent]:
        direction_delta = e.direction * self.physics_engine.config.velocity_multiplier * self.physics_engine.config.clock_multiplier
        obj = self.get_object_manager().get_by_id(e.obj_id)
        body = obj.get_body()

        direction_delta = direction_delta.rotated(-1 * body.angle)
        body.apply_impulse_at_world_point(direction_delta, body.position)
        body.angular_velocity += e.orientation_diff * self.physics_engine.config.orientation_multiplier
        return []

    def process_view_event(self, e: SLViewEvent):
        obj = self.get_object_manager().get_by_id(e.obj_id)
        obj.get_camera().distance += e.distance_diff
        return []

    def attach_objects(self, objs):
        for obj in objs:
            self.object_manager.add(obj)
            self.physics_engine.add_object(obj)
    
    def remove_object(self,obj:SLObject):
        obj.delete(self.clock.get_time())
        self.physics_engine.remove_object(obj)
        print("Deleting:{}".format(obj.is_deleted))

    def purge_object(self,obj:SLObject):
        self.physics_engine.remove_object(obj)
        self.object_manager.remove_by_id(obj.get_id())

    def get_object_manager(self) -> SLObjectManager:
        return self.object_manager

    def quit(self):
        pass

    def add_player(self, player: SLPlayer):
        self.player_manager.add_player(player)

    # def manual_player_action_step(self, action_set: Set[int], puid: str):
    #     # this should be handled on client side
    #     player = self.player_manager.get_player(puid)
    #     player.add_input(action_set)
    #     self.step()
    #     # player.process_frame(self.universe)
    #     obs = player.renderer.get_observation()
    #     # step_reward = self.get_step_reward()
    #     done = self.game_state == "QUITING"
    #     return obs, step_reward, done
        

    def load_game_snapshot(self,data):
        new_objs = self.object_manager.load_snapshot(data['object_manager'])
        for o in new_objs:
            self.physics_engine.add_object(o)
