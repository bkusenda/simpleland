
from ..common import Body, Vector
from .. import gamectx

def vec_to_coord(v):
    tile_size = gamectx.content.config['tile_size']
    return (int(v.x / tile_size), int(v.y / tile_size))


def coord_to_vec(coord):
    tile_size = gamectx.content.config['tile_size']
    return Vector(float(coord[0] * tile_size), float(coord[1] * tile_size))
