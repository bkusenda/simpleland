from typing import Set

from .common import (PhysicsConfig, SLAdminEvent, SLBody,
                     SLCircle, SLClock, SLEvent, SLLine, SLMechanicalEvent,
                     SLMoveEvent, SLObject, SLPlayerCollisionEvent,
                     SLPolygon, SLRewardEvent, SLSpace, SLVector, SLViewEvent)
from .core import SLEventManager, SLPhysicsEngine
from .object_manager import SLObjectManager
from .player import SLPlayer, SLPlayerManager
from .renderer import SLRenderer
from .utils import gen_id
from pymunk import Vec2d

import json
from uuid import UUID

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
        self.object_manager = SLObjectManager()
        self.physics_engine = SLPhysicsEngine()
        self.player_manager = SLPlayerManager()
        self.event_manager = SLEventManager()
        self.renderer = SLRenderer()
        self.game_state = "NOT_READY"


    def change_game_state(self, new_state):
        self.game_state = new_state
        return True

    def start(self):
        if self.game_state == "NOT_READY":
            self.change_game_state("READY")
        else:
            print("State must be NOT_READY, current state is %s" % self.game_state)

        self.change_game_state("RUNNING")

    def check_game_events(self):
        new_events = []
        events_to_remove = []
        for e in self.event_manager.get_events():
            if type(e) == SLAdminEvent:
                e: SLAdminEvent = e
                if e.value == 'QUIT':
                    self.change_game_state("QUITING")
                    events_to_remove.append(e)

        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())

        self.event_manager.add_events(new_events)

    def attach_objects(self, objs):
        for obj in objs:
            self.object_manager.add(obj)
            self.physics_engine.add_object(obj)

    def attach_static_objects(self, objs):
        for obj in objs:
            self.object_manager.add(obj)
            self.physics_engine.add_static_object(obj)

    def get_object_manager(self) -> SLObjectManager:
        """

        :return:
        """
        return self.object_manager

    def get_new_player_location(self):
        return SLVector.zero()

    def quit(self):
        pass

    def add_player(self, player: SLPlayer):
        self.player_manager.add_player(player)

    def step(self):
        # Get Input From Players
        self.event_manager.add_events(self.player_manager.pull_events())
        self.event_manager.add_events(self.physics_engine.pull_events())

        self.check_game_events()
        self.physics_engine.update(self.event_manager, self.object_manager)

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

    def run(self, obj: SLObject, renderer: SLRenderer, max_steps = None):
        """

        :return:
        """
        import json
        self.start()


        step_counter = 0

        while self.game_state == "RUNNING":
            """
            """
            self.step()
            renderer.process_frame(obj,self.object_manager)
            renderer.render_frame()

            obj_man_snapshot = self.object_manager.get_snapshot()
            print(obj_man_snapshot)
            event_man_snapshot =  self.event_manager.get_snapshot()
            encoded_as_st = json.dumps(obj_man_snapshot, indent=4, cls=StateEncoder)
            #print(encoded_as_st)
            results = json.loads(encoded_as_st,cls=StateDecoder)
            self.object_manager.clear_objects()
            self.object_manager.load_snapshot(results)

            step_counter += 1
            if max_steps and step_counter > max_steps:
                self.game_state = "QUITING"





    # def process_frame(self, universe: SLUniverse):
    #     """

    #     :return:
    #     """
    #     additional_info = {'console info': "health:%s" % self.health}
    #     self.renderer.process_frame(
    #         SLViewState(self.get_object(), universe), 
    #         additional_info)

    # def quit(self):
    #     self.renderer.quit()


    #     def process_frame(self, universe: SLUniverse):
    #     """

    #     :return:
    #     """
    #     additional_info = {'console info': "health:%s" % self.health}
    #     self.renderer.process_frame(SLViewState(self.get_object(), universe), additional_info)


    # def process_frame(self, universe: SLUniverse):
    #     """

    #     :return:
    #     """
    #     self.renderer.render_frame(SLViewState(self.get_object(), universe))
    #     self.ready = True
