from typing import Set

from .common import (FollowBehaviour, PhysicsConfig, SLAdminEvent, SLBody,
                     SLCircle, SLClock, SLEvent, SLLine, SLMechanicalEvent,
                     SLMoveEvent, SLObject, SLPlayerCollisionEvent, SLPoint,
                     SLPolygon, SLRewardEvent, SLSpace, SLVector, SLViewEvent)
from .core import SLEventManager, SLPhysicsEngine
from .object_manager import SLObjectManager
from .player import SLPlayer, SLPlayerManager
from .renderer import SLRenderer
from .utils import gen_id


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

            if type(e) == SLPlayerCollisionEvent:
                e: SLPlayerCollisionEvent = e
                self.player_manager.get_player(e.player_id).apply_health_update(-1.0)
                new_events.append(SLRewardEvent(e.player_id, -1))
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

    def pull_physical_events(self):
        return self.physics_engine.pull_events()

    def get_behavior_events(self):
        """
        TODO: Relocate me
        :return:
        """
        events = []
        for obj in self.object_manager.get_all_objects():
            for behavior in obj.behavior_list:
                if type(behavior) == FollowBehaviour:
                    behavior: FollowBehaviour = behavior
                    target_pos: SLPoint = behavior.obj.get_body().position
                    obj_pos = obj.get_body().position
                    direction = obj_pos - target_pos
                    self.direction = direction
                    distance = obj_pos.get_distance(target_pos)
                    if distance > 0:
                        new_direction = direction / distance * -1

                        events.append(SLMechanicalEvent(obj,
                                                        direction=new_direction,
                                                        orientation_diff=0.0))
        return events

    def physics_update(self, event_manager: SLEventManager):
        self.physics_engine.update(event_manager, self.object_manager)

    def get_step_reward(self):
        # TODO: need to make this so it works for multiple users,
        # TODO: events should expire!
        step_reward = 0
        events_to_remove = []
        for e in self.event_manager.get_events():
            if type(e) == SLRewardEvent:
                e: SLRewardEvent = e
                step_reward += e.reward
                events_to_remove.append(e)

        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())
        return step_reward

    def quit(self):
        pass

    def add_player(self, player: SLPlayer):
        self.player_manager.add_player(player)

    def step(self):
        # Get Input From Players
        self.event_manager.add_events(self.player_manager.pull_events())
        self.event_manager.add_events(self.pull_physical_events())
        self.event_manager.add_events(self.get_behavior_events())

        self.check_game_events()
        self.physics_update(self.event_manager)

    def manual_player_action_step(self, action_set: Set[int], puid: str):
        # this should be handled on client side
        player = self.player_manager.get_player(puid)
        player.add_input(action_set)
        self.step()
        # player.process_frame(self.universe)
        obs = player.renderer.get_observation()
        step_reward = self.get_step_reward()
        done = self.game_state == "QUITING"
        return obs, step_reward, done

    def run(self, obj: SLObject, renderer: SLRenderer, max_frames = None):
        """

        :return:
        """
        self.start()

        while self.game_state == "RUNNING":
            """
            """
            self.step()
            renderer.process_frame(obj,self.object_manager)
            renderer.render_frame()




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
