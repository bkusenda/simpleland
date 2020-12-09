from typing import List
from ..event import InputEvent, Event
from ..game import Game
from ..common import Vector

def input_event_callback(input_event: InputEvent, game: Game) -> List[Event]:

    # for event in pygame.event.get():
    #     # print("%s" % event.type)
    #     if event.type == pygame.QUIT:
    #         admin_event = SLAdminEvent('QUIT')
    #         events.append(admin_event)
    #         print("Adding admin_event (via pygame_event) %s" % admin_event)
    #     elif event.type == pygame.MOUSEBUTTONDOWN:
    #         # print("here %s" % event.button)
    #         if event.button == 4:
    #             view_event = SLViewEvent(player.get_object_id(), 1, SLVector.zero())
    #             events.append(view_event)
    #         elif event.button == 5:
    #             view_event = SLViewEvent(player.get_object_id(), -1, SLVector.zero())
    #             events.append(view_event)
    keys = set(input_event.input_data['inputs'])
    # if len(keys) > 0 and isinstance(keys[0],str):
    #     print(keys)
    #     keys = [int(k) for k in keys]


    player = game.player_manager.get_player(input_event.player_id)
    if player is None:
        return []
    t, obj = game.object_manager.get_latest_by_id(player.get_object_id())
    if obj is None:
        return []

    move_speed = 0.10
    obj_orientation_diff = 0
    if 1 in keys:
        obj_orientation_diff = 1

    if 4 in keys:
        obj_orientation_diff = -1

    # Object Movement
    force = 1
    direction = Vector.zero()
    if 23 in keys:
        direction += Vector(0, 1)

    if 19 in keys:
        direction += Vector(0, -.3)

    # if 1 in keys:
    #     direction += Vector(-1, 0)

    # if 4 in keys:
    #     direction += Vector(1., 0)

    if 10 in keys:
        print("Adding admin_event ...TODO!!")

    mag = direction.length
    if mag != 0:
        # direction = ((1.0 / mag) * force * direction)
        obj.set_data_value("image", "1_thrust")
    else:
        direction = Vector.zero()
        obj.set_data_value("image", "1")

    orientation_diff = obj_orientation_diff * move_speed

    direction = direction * 10
    obj.set_last_change(game.clock.get_time())
    body = obj.get_body()

    direction = direction.rotated(body.angle)
    body.apply_impulse_at_world_point(direction, body.position)
    body.angular_velocity += orientation_diff

    if body.angular_velocity > 3:
        body.angular_velocity = 3
    elif body.angular_velocity < -3:
        body.angular_velocity = -3
    return []
