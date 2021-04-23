import pygame
from typing import List, Dict
from .event import (Event, AdminEvent, MechanicalEvent,
                            PeriodicEvent, ViewEvent, SoundEvent, DelayedEvent, InputEvent)
from .event_manager import EventManager

from .common import (get_dict_snapshot, load_dict_snapshot, Body, Circle,  Line,
                     Polygon, Space, Vector,  Base, Camera)
from simpleland.player import Player

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

import sys
def get_input_events(player:Player) -> List[Event]:

    player_id = player.get_id()

    events: List[Event] = []

    key_list = []
    key_list.append(pygame.K_q)
    key_list.append(pygame.K_e)
    key_list.append(pygame.K_f)
    key_list.append(pygame.K_r)
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
            if event.button == 4:
                view_event = ViewEvent(player_id, 50, Vector.zero())
                events.append(view_event)
            elif event.button == 5:
                view_event = ViewEvent(player_id, -50, Vector.zero())
                events.append(view_event)

    keys = pygame.key.get_pressed()
    for key in key_list:
        if keys[key]:
            key_pressed.add(key)
    if len(key_pressed)>0:
        event = InputEvent(
            player_id  = player_id, 
            input_data = {
                'inputs':[DEFAULT_KEYMAP[k] for k in key_pressed], # TAG: BJK1
                'mouse_pos': pygame.mouse.get_pos(),
                'mouse_rel': pygame.mouse.get_rel(),
                'focused': pygame.mouse.get_focused()
                })
        events.append(event)
    return events