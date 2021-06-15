
from ..common import Vector2
from .. import gamectx

def vec_to_coord(v):
    tile_size = gamectx.content.config['tile_size']
    return (int(v.x / tile_size), int(v.y / tile_size))


def coord_to_vec(coord):
    tile_size = gamectx.content.config['tile_size']
    return Vector2(float(coord[0] * tile_size), float(coord[1] * tile_size))

def normalize_angle(angle):
    angle = angle % 360
    if angle < 225 and angle >= 135 :
        angle = 180
    elif angle >= 45 and angle < 135:
        angle = 90
    elif angle < 315 and angle >= 225:
        angle = 270
    elif angle >= 315 or angle <45:
        angle = 0
    return angle

def angle_to_sprite_direction(angle):
    direction = "down"
    angle = angle % 360
    if angle < 225 and angle >= 135 :
        direction = "up"
    elif angle >= 45 and angle < 135:
        direction = "left"
    elif angle < 315 and angle >= 225:
        direction = "right"
    elif angle >= 315 or angle <45:
        direction = "down"
    return direction


# def direction_to_angle(direction):
#     angle = 0
#     if direction == "down":
#         angle = 180
#     elif direction == "left":
#         angle = 90
#     elif direction == "right":
#         angle = 270
#     elif direction == "up":
#         angle = 0
#     return angle

def normalized_direction(orig_direction):
    direction = orig_direction.normalize()
    updated_x = 0
    updated_y = 0
    if abs(direction.x) > abs(direction.y):
        updated_y = 0
        if direction.x > 0.5:
            updated_x = 1.0
        elif direction.x < -0.5:
            updated_x = -1.0
        else:
            updated_x = 0
    else:
        updated_x = 0
        if direction.y >= 0.5:
            updated_y = 1.0
        elif direction.y < -0.5:
            updated_y = -1.0
        else:
            updated_y = 0
    return Vector2(updated_x,updated_y)
