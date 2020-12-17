from typing import List
from ..event import InputEvent, Event, AdminEvent,ViewEvent
from .. import gamectx
from ..common import Body, Vector
import pygame

def input_event_callback(input_event: InputEvent) -> List[Event]:
    player = gamectx.player_manager.get_player(input_event.player_id)
    
    if player is None:
        return []
    events= []

    keys = set(input_event.input_data['inputs'])


    obj = gamectx.object_manager.get_latest_by_id(player.get_object_id())
    if obj is None:
        return events

    is_kinematic = obj.get_data_value('is_kinematic')
    rotation_multiplier = obj.get_data_value('rotation_multiplier')
    velocity_multiplier = obj.get_data_value('velocity_multiplier')

    obj_orientation_diff = 0
    if 1 in keys:
        obj_orientation_diff = 1

    if 4 in keys:
        obj_orientation_diff = -1

    # Object Movement
    direction = Vector.zero()
    if 23 in keys:
        direction += Vector(0, 1)

    if 19 in keys:
        direction += Vector(0, -1)

    # if 1 in keys:
    #     direction += Vector(-1, 0)

    # if 4 in keys:
    #     direction += Vector(1., 0)

    if 10 in keys:
        print("Adding admin_event ...TODO!!")

    mag = direction.length
    if mag != 0:
        direction = ((1.0 / mag) * direction)
        obj.set_data_value("image", "1_thrust")
    else:
        direction = Vector.zero()
        obj.set_data_value("image", "1")

    orientation_diff = obj_orientation_diff * rotation_multiplier

    direction = direction * velocity_multiplier
    obj.set_last_change(gamectx.clock.get_time())
    body:Body = obj.get_body()

    direction = direction.rotated(body.angle)
    if is_kinematic:
        body.velocity = direction
        body.angular_velocity = orientation_diff
    else:
        body.apply_impulse_at_world_point(direction, body.position)
        body.angular_velocity += orientation_diff

    
    player_angular_vel_max = gamectx.physics_engine.config.player_angular_vel_max
    if body.angular_velocity > player_angular_vel_max:
        body.angular_velocity = player_angular_vel_max
    elif body.angular_velocity < -player_angular_vel_max:
        body.angular_velocity = -player_angular_vel_max
    return events
