import time
from typing import List, Dict

import numpy as np
import pygame


from .common import (get_dict_snapshot, load_dict_snapshot, SLBody, SLCircle, SLClock, SLLine,
                     SLObject, SLPolygon, SLSpace, SLVector, SimClock, SLBase)
from .utils import gen_id
from .event_manager import (SLAdminEvent, SLEventManager, SLMechanicalEvent,
                            SLPeriodicEvent, SLViewEvent, SLEvent, SLInputEvent)


def get_default_key_map():
    key_map = {}
    key_map[pygame.K_a] = 1
    key_map[pygame.K_b] = 2
    key_map[pygame.K_c] = 3
    key_map[pygame.K_d] = 4
    key_map[pygame.K_e] = 5
    key_map[pygame.K_f] = 6
    key_map[pygame.K_g] = 7
    key_map[pygame.K_h] = 8
    key_map[pygame.K_i] = 9
    key_map[pygame.K_j] = 10
    key_map[pygame.K_k] = 11
    key_map[pygame.K_l] = 12
    key_map[pygame.K_m] = 13
    key_map[pygame.K_n] = 14
    key_map[pygame.K_o] = 15
    key_map[pygame.K_p] = 16
    key_map[pygame.K_q] = 17
    key_map[pygame.K_r] = 18
    key_map[pygame.K_s] = 19
    key_map[pygame.K_t] = 20
    key_map[pygame.K_u] = 21
    key_map[pygame.K_v] = 22
    key_map[pygame.K_w] = 23
    key_map[pygame.K_x] = 24
    key_map[pygame.K_y] = 25
    key_map[pygame.K_z] = 26
    key_map[pygame.K_ESCAPE] = 27
    key_map["MOUSE_DOWN_1"] = 28
    key_map["MOUSE_DOWN_2"] = 29
    key_map["MOUSE_DOWN_3"] = 30
    key_map["MOUSE_DOWN_4"] = 31
    key_map["MOUSE_DOWN_5"] = 32
    return key_map
DEFAULT_KEYMAP = get_default_key_map()
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
        super(SLHumanPlayer, self).__init__()


    def pull_input_events(self) -> List[SLEvent]:

        events: List[SLEvent] = []

        key_list = []
        key_list.append(pygame.K_q)
        key_list.append(pygame.K_e)
        key_list.append(pygame.K_w)
        key_list.append(pygame.K_q)
        key_list.append(pygame.K_s)
        key_list.append(pygame.K_a)
        key_list.append(pygame.K_d)
        key_list.append(pygame.K_ESCAPE)

        key_pressed=set()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                key_pressed.add("QUIT")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                key_pressed.add("MOUSE_DOWN_{}".format(event.button))

        keys = pygame.key.get_pressed()
        for key in key_list:
            if keys[key]:
                key_pressed.add(key)
        event = SLInputEvent(
            player_id  =self.get_id(), 
            input_data = {
                'inputs':{DEFAULT_KEYMAP[k]:1 for k in key_pressed},
                'mouse_pos': pygame.mouse.get_pos(),
                'mouse_rel': pygame.mouse.get_rel(),
                'focused': pygame.mouse.get_focused()
                })
        events.append(event)
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