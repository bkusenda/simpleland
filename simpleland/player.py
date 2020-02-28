import time
from typing import List, Dict

import numpy as np
import pygame


from simpleland.common import (PhysicsConfig, SLBase,                               
                                SLCircle, SLClock, SLEvent, SLLine, SLAdminEvent,
                               SLMechanicalEvent, SLMoveEvent, SLObject,
                               SLPlayerCollisionEvent, SLPolygon,
                               SLSpace, SLVector, SLViewEvent)

from simpleland.utils import gen_id


class SLPlayer(SLBase):

    def __init__(self, uid=None):
        """

        :return:
        """
        self.uid = uid
        self.obj_id = None
        self.health = 0.0
        self.last_health_diff = 0.0
        self.events=[]

    def get_health(self):
        return self.health

    def add_input(self, input):
        raise NotImplementedError

    def attach_object(self, obj: SLObject):
        self.obj_id = obj.get_id()

    def get_object_id(self) -> str:
        return self.obj_id
    
    def pull_input_events(self) -> List[SLEvent]:
        return []
    


class SLHumanPlayer(SLPlayer):



    @classmethod
    def build_from_dict(cls,data_dict):
        data = data_dict['data']
        player = cls()
        player.uid = data['uid']
        player.obj_id = data['obj_id']
        player.health = data['health']
        player.last_health_diff = data['last_health_diff']
        return player


    def __init__(self):
        """

        :return:
        """
        super(SLHumanPlayer, self).__init__()
        self.blocking_player = True
        self.block_sleep_secs = 0.01
        self.ready = False

    def pull_input_events(self) -> List[SLEvent]:

        events = None

        if self.blocking_player and self.ready:
            done = False
            while not done:
                time.sleep(self.block_sleep_secs)
                events = self._pull_input_events()
                done = len(events) > 0
        else:
            events = self._pull_input_events()
        return events

    def _pull_input_events(self) -> List[SLEvent]:
        """

        :param action:
        :return:
        """
        # print("Getting action from player")

        events: List[SLEvent] = []

        for event in pygame.event.get():
            # print("%s" % event.type)
            if event.type == pygame.QUIT:
                admin_event = SLAdminEvent('QUIT')
                events.append(admin_event)
                print("Adding admin_event (via pygame_event) %s" % admin_event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # print("here %s" % event.button)
                if event.button == 4:
                    view_event = SLViewEvent(self.get_object_id(), 1, SLVector.zero())
                    events.append(view_event)
                elif event.button == 5:
                    view_event = SLViewEvent(self.get_object_id(), -1, SLVector.zero())
                    events.append(view_event)

        keys = pygame.key.get_pressed()

        move_speed = 0.02
        obj_orientation_diff = None
        if keys[pygame.K_q]:
            obj_orientation_diff = -1
        elif keys[pygame.K_e]:
            obj_orientation_diff = 1

        if obj_orientation_diff is not None:
            events.append(SLMechanicalEvent(self.get_object_id(), direction=SLVector.zero(), orientation_diff=obj_orientation_diff * move_speed))

        # Object Movement
        force = 0.5
        direction = SLVector.zero()
        if keys[pygame.K_w]:
            direction += SLVector(0, 1)

        if keys[pygame.K_s]:
            direction += SLVector(0, -1)

        if keys[pygame.K_a]:
            direction += SLVector(-1, 0)

        if keys[pygame.K_d]:
            direction += SLVector(1, 0)

        if keys[pygame.K_ESCAPE]:
            admin_event = SLAdminEvent('QUIT')
            events.append(admin_event)
            print("Adding admin_event %s" % admin_event)

        mag = float(np.sqrt(direction.dot(direction)))
        if mag != 0:
            direction = ((1.0 / mag) * force * direction)
            events.append(SLMechanicalEvent(self.get_object_id(), direction))
            # print("Adding movement_event %s" % direction_event)

        return events


class SLAgentPlayer(SLPlayer):

    def __init__(self):
        super(SLAgentPlayer, self).__init__()
        """

        :return:
        """
        self.blocking_player = True
        self.block_sleep_secs = 0.00
        self.ready = False

    def pull_input_events(self) -> List[SLEvent]:
        return self.events

    def add_input(self, action_set):
        self.events = self._get_events_from_input(action_set)

    def add_event(self, event: SLEvent):
        self.events.append(event)

    def clear_events(self):
        self.events = []

    def _get_events_from_input(self, action_set) -> List[SLEvent]:

        events: List[SLEvent] = []

        move_speed = 0.02

        obj_orientation_diff = None
        if 1 in action_set and not 2 in action_set:
            obj_orientation_diff = -1
        elif 2 in action_set and not 1 in action_set:
            obj_orientation_diff = 1

        if obj_orientation_diff is not None:
            events.append(SLMechanicalEvent(self.get_object_id(), orientation_diff=obj_orientation_diff * move_speed))

        # Object Movement
        force = 0.5
        direction = SLVector.zero()
        if 3 in action_set:
            direction += SLVector(0, 1)

        if 4 in action_set:
            direction += SLVector(0, -1)

        if 5 in action_set:
            direction += SLVector(-1, 0)

        if 6 in action_set:
            direction += SLVector(1, 0)

        mag = float(np.sqrt(direction.dot(direction)))
        if mag != 0:
            direction = ((1.0 / mag) * force * direction)
            events.append(SLMechanicalEvent(self.get_object_id(), direction))

        return events


class SLPlayerManager(object):

    def __init__(self):
        self.players_map: Dict[str, SLPlayer] = {}

    def add_player(self, player: SLPlayer):
        """

        :param player:
        :return:
        """
        self.players_map[player.uid] = player

    def get_player(self, uid) -> SLPlayer:
        return self.players_map.get(uid, None)

    def pull_events(self) -> List[SLEvent]:
        all_player_events: List[SLEvent] = []
        for player in self.players_map.values():
            all_player_events.extend(player.pull_input_events())
        return all_player_events
