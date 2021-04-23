from typing import List,Dict,Any
from ..event import InputEvent, Event, AdminEvent,ViewEvent, DelayedEvent
from .. import gamectx
from ..common import Body, Vector
import pygame
from ..clock import clock

import sys
import math


def input_event_callback(input_event: InputEvent) -> List[Event]:

    player = gamectx.player_manager.get_player(input_event.player_id)
    if not player.get_data_value("allow_input",False):
        return []
    if player is None:
        return []
    if player.get_data_value("view_type") == 0:
        return input_event_callback_fpv(input_event,player)
    else:
        return input_event_callback_3rd(input_event,player)


def input_event_callback_3rd(input_event:InputEvent, player) -> List[Event]:
    
    events= []
    tile_size = gamectx.physics_engine.config.tile_size
    keys = set(input_event.input_data['inputs'])
    cur_tick = clock.get_tick_counter()

    obj = gamectx.object_manager.get_by_id(player.get_object_id())
    if obj is None:
        return events

    
    if not obj.enabled:
        return []
    elif player.get_data_value("reset_required",False):
        print("Episode is over. Reset required")
        return events

    velocity_multiplier = obj.get_data_value('velocity_multiplier')

    # Queued action prevents movement until complete. Trigger at a certain time and releases action lock later but 
    # cur_tick = clock.get_tick_counter()
    action_completion_time = obj.get_data_value("action_completion_time",0)
    if cur_tick <= obj.get_data_value("action_completion_time",0):
        return []


    # Object Movement
    actions_set = set()
    direction = Vector.zero()
    angle_update = None
    if 23 in keys:
        direction = Vector(0, 1)
        angle_update = 0
        actions_set.add("MOVE")

    if 19 in keys:
        direction = Vector(0, -1)
        angle_update = math.pi
        actions_set.add("MOVE")

    if 4 in keys:
        direction = Vector(1, 0)
        angle_update = -math.pi/2
        actions_set.add("MOVE")
        

    if 1 in keys:
        direction = Vector(-1, 0)
        angle_update = math.pi/2
        actions_set.add("MOVE")

    if 5 in keys:
        actions_set.add("GRAB")

    if 6 in keys:
        actions_set.add("PLACE")

    if 18 in keys:
        actions_set.add("ATTACK")

    if 31 in keys:
        events.append(ViewEvent(player.get_id(), 100))

    if 10 in keys:
        print("Adding admin_event ...TODO!!")

    


    if "GRAB" in actions_set:
        def grab_event_fn(event: DelayedEvent, data: Dict[str, Any]):

            obj.set_last_change(cur_tick)
            # new_pos = tile_size * direction + obj.get_position()
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            direction= Vector(0,1).rotated(obj.body.angle)
            print(direction)

            target_pos= obj.get_position() + (direction * tile_size)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
                print(gamectx.object_manager.get_by_id(oid).get_data_value("type"))
            
            obj.set_data_value("action",
                {
                    'type':'grab',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                })
            return []

        event = DelayedEvent(grab_event_fn, 
            execution_step=0, 
            data={})
        events.append(event)

    elif "DROP" in actions_set:
        def grab_event_fn(event: DelayedEvent, data: Dict[str, Any]):

            obj.set_last_change(cur_tick)
            # new_pos = tile_size * direction + obj.get_position()
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            direction= Vector(0,1).rotated(obj.body.angle)
            print(direction)

            target_pos= obj.get_position() + (direction * tile_size)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            if len(gamectx.physics_engine.space.get_objs_at(target_coord))==0:
                # gamectx.content.
                pass
            
            obj.set_data_value("action",
                {
                    'type':'drop',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                })
            return []

        event = DelayedEvent(grab_event_fn, 
            execution_step=0, 
            data={})
        events.append(event)

    elif "ATTACK" in actions_set:
        def event_fn(event: DelayedEvent, data: Dict[str, Any]):
            obj.set_last_change(cur_tick)
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            direction= Vector(0,1).rotated(obj.body.angle)
            print(direction)

            target_pos= obj.get_position() + (direction * tile_size)
            target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
            for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
                print(gamectx.object_manager.get_by_id(oid).get_data_value("type"))
            
            obj.set_data_value("action",
                {
                    'type':'attack',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                })
            return []
        event = DelayedEvent(event_fn, 
            execution_step=0, 
            data={})

        events.append(event)
    elif "MOVE" in actions_set:
        def move_event_fn(event: DelayedEvent, data: Dict[str, Any]):
            direction = data['direction']
            angle_update = data['angle_update']
            direction = direction * velocity_multiplier
            obj.set_last_change(cur_tick)
            ticks_in_action = int(1 * gamectx.content.speed_factor())
            action_complete_time = cur_tick + ticks_in_action
            obj.set_data_value("action_completion_time",action_complete_time)
            body:Body = obj.get_body()
            new_pos = tile_size * direction + body.position
            obj.set_data_value("action",
                {
                    'type':'walk',
                    'start_tick':clock.get_tick_counter(),
                    'ticks': ticks_in_action,
                    'step_size': tile_size/ticks_in_action,
                    'start_position': body.position,
                    'direction': direction
                })

            obj.update_position(new_pos)
            if angle_update is not None:
                body.angle = angle_update
            return []

        event = DelayedEvent(move_event_fn, 
            execution_step=0, 
            data={'direction':direction,'angle_update':angle_update})
        events.append(event)

    return events


def input_event_callback_fpv(input_event: InputEvent, player) -> List[Event]:

    events= []
    tile_size = gamectx.physics_engine.config.tile_size
    keys = set(input_event.input_data['inputs'])

    obj = gamectx.object_manager.get_by_id(player.get_object_id())
    if obj is None:
        return events
    gamectx.content.get_observation(obj)

    rotation_multiplier = obj.get_data_value('rotation_multiplier')
    velocity_multiplier = obj.get_data_value('velocity_multiplier')

    obj_orientation_diff = 0
    if 1 in keys:
        obj_orientation_diff = math.pi/2

    if 4 in keys:
        obj_orientation_diff = -math.pi/2

    # Object Movement
    direction:Vector = Vector.zero()

    if 23 in keys:
        direction = Vector(0, 1)

    if 19 in keys:
        direction = Vector(0, -1)

    if 31 in keys:
        events.append(ViewEvent(player.get_id(), 100))

    if 10 in keys:
        print("Adding admin_event ...TODO!!")

    def move_event_fn(event: DelayedEvent, data: Dict[str, Any]):
        direction = data['direction']
        orientation_diff = obj_orientation_diff * rotation_multiplier
        direction = direction * velocity_multiplier
        obj.set_last_change(clock.get_time())
        body:Body = obj.get_body()
        angle = body.angle
        direction = direction.rotated(angle)
        new_pos = tile_size * direction + body.position
        obj.update_position(new_pos)
        body.angle = angle + orientation_diff
        return []

    movement_event = False
    if movement_event:

        event = DelayedEvent(move_event_fn, execution_step=0, data={'direction':direction})
        events.append(event)

    return events
