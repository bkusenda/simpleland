from typing import List
from ..event import InputEvent, Event, AdminEvent,ViewEvent
from .. import gamectx
from ..common import Body, Vector
import pygame

import sys
import math
def input_event_callback(input_event: InputEvent) -> List[Event]:
    player = gamectx.player_manager.get_player(input_event.player_id)
    # FRAME STEP Motation

    if player is None:
        return []
    events= []
    grid_size = gamectx.physics_engine.config.grid_size
    keys = set(input_event.input_data['inputs'])

    obj = gamectx.object_manager.get_latest_by_id(player.get_object_id())
    if obj is None:
        return events

    rotation_multiplier = obj.get_data_value('rotation_multiplier')
    velocity_multiplier = obj.get_data_value('velocity_multiplier')

    obj_orientation_diff = 0
    if 1 in keys:
        obj_orientation_diff = math.pi/2

    if 4 in keys:
        obj_orientation_diff = -math.pi/2

    # Object Movement
    direction = Vector.zero()
    if 23 in keys:
        direction = Vector(0, 1)

    if 19 in keys:
        direction = Vector(0, -1)

    if 31 in keys:
        events.append(ViewEvent(player.get_id(), 100))

    # if 4 in keys:
    #     direction += Vector(1., 0)

    if 10 in keys:
        print("Adding admin_event ...TODO!!")

    orientation_diff = obj_orientation_diff * rotation_multiplier

    direction = direction * velocity_multiplier
    obj.set_last_change(gamectx.clock.get_time())
    body:Body = obj.get_body()
    angle = body.angle
    direction = direction.rotated(angle)
    new_pos = grid_size * direction + body.position
    obj.update_position(new_pos)
    body.angle = angle + orientation_diff

    return events
