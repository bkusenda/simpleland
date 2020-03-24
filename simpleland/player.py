import time
from typing import List, Dict

import numpy as np
import pygame


from .common import (get_dict_snapshot, load_dict_snapshot, Body, Circle, Clock, Line,
                     Polygon, Space, Vector, SimClock, Base)
from .utils import gen_id

from .object import (GObject, ExtendedGObject)
from .physics_engine import PhysicsEngine
from .event import (Event, AdminEvent, MechanicalEvent,
                            PeriodicEvent, ViewEvent, SoundEvent, DelayedEvent, InputEvent)
from .event_manager import EventManager

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

def get_input_events(player_id) -> List[Event]:

    events: List[Event] = []

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
    event = InputEvent(
        player_id  = player_id, 
        input_data = {
            'inputs':{DEFAULT_KEYMAP[k]:1 for k in key_pressed},
            'mouse_pos': pygame.mouse.get_pos(),
            'mouse_rel': pygame.mouse.get_rel(),
            'focused': pygame.mouse.get_focused()
            })
    events.append(event)
    return events

class Player(Base):

    @classmethod
    def build_from_dict(cls,data_dict):
        data = data_dict['data']
        player = cls()
        player.uid = data['uid']
        player.obj_id = data['obj_id']
        player.data = data.get('data',{})
        print(data_dict)
        return player

    def __init__(self, uid=None, data=None, player_type =0):
        """

        :return:
        """
        self.uid = uid
        self.player_type = player_type
        self.obj_id = None
        self.events=[]
        self.data = {} if data is None else data

    def get_id(self):
        return self.uid    

    def get_data_value(self,k, default_value=None):
        return self.data.get(k,default_value)
    
    def set_data_value(self,k,value):
        self.data[k] = value

    def attach_object(self, obj: GObject):
        self.obj_id = obj.get_id()

    def get_object_id(self) -> str:
        return self.obj_id

    def add_event(self, event: Event):
        self.events.append(event)
    
    def pull_input_events(self) -> List[Event]:
        events =  self.events
        self.events = []
        return events

    def get_snapshot(self):
        data =  get_dict_snapshot(self, exclude_keys={'events'})
        return data

    def load_snapshot(self, data):
        load_dict_snapshot(self, data, exclude_keys={"events"})



class PlayerManager:

    def __init__(self):
        self.players_map: Dict[str, Player] = {}

    def add_player(self, player: Player):
        """

        :param player:
        :return:
        """
        self.players_map[player.uid] = player

    def get_player(self, uid) -> Player:
        return self.players_map.get(uid, None)

    def pull_events(self) -> List[Event]:
        all_player_events: List[Event] = []
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
                new_p = Player.build_from_dict(p_data)
                self.players_map[k] = new_p
                new_players.append(new_p)
        return new_players