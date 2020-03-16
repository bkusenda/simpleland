import time
from typing import List, Dict

import numpy as np
import pygame


from .common import (get_dict_snapshot, load_dict_snapshot, SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock, SLBase)
from .utils import gen_id
from .event_manager import (SLAdminEvent, SLEventManager, SLMechanicalEvent,
                            SLPeriodicEvent, SLViewEvent, SLEvent)

class SLPlayer(SLBase):

    def __init__(self, uid=None, data=None):
        """

        :return:
        """
        self.uid = uid
        self.obj_id = None
        self.events=[]
        self.data = {} if data is None else data

    def get_id(self):
        return self.uid    

    def get_data_value(self,k, default_value=None):
        return self.data.get(k,default_value)
    
    def set_data_value(self,k,value):
        self.data[k] = value

    def add_input(self, input):
        raise NotImplementedError

    def attach_object(self, obj: SLObject):
        self.obj_id = obj.get_id()

    def get_object_id(self) -> str:
        return self.obj_id
    
    def pull_input_events(self) -> List[SLEvent]:
        return []
    
    def get_snapshot(self):
        data =  get_dict_snapshot(self, exclude_keys={'events'})
        return data

    def load_snapshot(self, data):
        load_dict_snapshot(self, data, exclude_keys={"events"})


class SLHumanPlayer(SLPlayer):



    @classmethod
    def build_from_dict(cls,data_dict):
        data = data_dict['data']
        player = cls()
        player.uid = data['uid']
        player.obj_id = data['obj_id']
        player.data = data.get('data',{})
        print(data_dict)
        return player


    def __init__(self):
        """

        :return:
        """
        super(SLHumanPlayer, self).__init__()
        self.blocking_player = True
        #self.block_sleep_secs = 0.01
        self.ready = False

    def pull_input_events(self) -> List[SLEvent]:

        events = None

        if self.blocking_player and self.ready:
            done = False
            while not done:
                #time.sleep(self.block_sleep_secs)
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


    def _pull_input_events_old(self) -> List[SLEvent]:
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

        move_speed = 1
        obj_orientation_diff = None
        if keys[pygame.K_q]:
            obj_orientation_diff = -1
        elif keys[pygame.K_e]:
            obj_orientation_diff = 1

        if obj_orientation_diff is not None:
            events.append(SLMechanicalEvent(self.get_object_id(), 
                    direction=SLVector.zero(),
                    orientation_diff=obj_orientation_diff * move_speed))

        # Object Movement
        force = 0.5
        direction = SLVector.zero()
        if keys[pygame.K_w]:
            direction += SLVector(0, 1)

        if keys[pygame.K_s]:
            direction += SLVector(0, -1)

        if keys[pygame.K_a]:
            direction += SLVector(-0.5, 0)

        if keys[pygame.K_d]:
            direction += SLVector(0.5, 0)

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
            events.append(SLMechanicalEvent(self.get_object_id(), direction=SLVector.zero(), orientation_diff=obj_orientation_diff * move_speed))

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


class SLPlayerManager:

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

    def get_snapshot(self):
        players = list(self.players_map.values())
        results = {}
        for p in players:
            results[p.get_id()]= p.get_snapshot()
        return results

    def load_snapshot(self,data):
        new_players = []
        for k,p_data in data.items():
            if k in self.players_map:
                self.players_map[k].load_snapshot(p_data)
            else:
                new_p = SLHumanPlayer.build_from_dict(p_data)
                self.players_map[k] = new_p
                new_players.append(new_p)
        return new_players