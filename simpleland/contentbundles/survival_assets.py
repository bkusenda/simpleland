from ..asset_bundle import AssetBundle
import math
import random

from typing import List
from .. import gamectx
from ..clock import clock
from ..common import (Vector)


from ..itemfactory import ShapeFactory
from ..object import GObject

from ..player import Player
from ..event import (DelayedEvent)
from .survival_config import TILE_SIZE
from .survival_utils import coord_to_vec

# map_layer_1 = (
#     f"gggggggggggggggggggggggggggggg\n"
#     f"gggggggggggggggggggggggggggggg\n"
#     f"gggggggggggggggggggggggggggggg\n"
#     f"ggwwwggggggggggggggggggggggggg\n"
#     f"gggwwwgggggggggggggggggggggggg\n"
#     f"ggwwwwwwgggggggggggggggggggggg\n"
#     f"ggggwwwggggggggggggggggggggggg\n"
#     f"gggggwwwgggggggggggggggggggggggg\n"
#     f"gggggwwggggggggggggggggggggggg\n"
#     f"gggggwgggggggggggggggggggggggg\n"
#     f"gggggwgggggggggggggggggggg\n"
#     f"gggwwwgggggggggggggggggggggggg\n"
#     f"gggggwwwwwwgggggggggggggggggggggg\n"
#     f"gggggggggwwwggggggggggggggggggggggg\n"
#     f"gggggggggggwwwgggggggggggggggggggggggg\n"
#     f"ggggggggggggwwggggggggggggggggggggggg\n"
#     f"gggggggggggggwgggggggggggggggggggggggg\n"
#     f"gggggggggggggggggggggggggggggg\n"
#     f"gggggggggggggggggggggggggggggg\n"
#     f"gggggggggggggggggggggggggggggg\n"
#     f"\n"

# )
# s

map_layer_2 = (

    f"          rrrrrrrrrrrrrr\n"
    f"  t            t     fffffffr\n"
    f"                   r\n"
    f"    t          t  t   r rr\n"
    f"       f        r         m  r\n"
    f"   t      s     f  s      r\n"
    f"              d           r\n"
    f"      m           \n"

)

map_layers = [map_layer_2]


import hashlib


def rand_int_from_coord(x,y,seed):
    v =  (x + y * seed ) % 12783723
    h = hashlib.sha1()
    h.update(str.encode(f"{v}"))
    return int(h.hexdigest(),16) % 172837

def get_tile_image_id(x,y,seed):
    v = rand_int_from_coord(x,y,seed) % 3 + 1
    return f"grass{v}"


class TileMap:

    def __init__(self,seed = 123):
        self.seed = seed
        
    def get_by_loc(self,x,y):
        if x ==0 and y==0:
            return "baby_tree"
        if x ==2 and y==3:
            return "baby_tree"
        return get_tile_image_id(x,y,self.seed)

class TileMapLoader:

    def __init__(self):
        self.tilemap = None
    
    def get_tilemap(self,name):
        if self.tilemap is None:
            self.tilemap = gamectx.content.tilemap
        return self.tilemap

def load_asset_bundle():
    image_assets = {}

    # player idle
    image_assets['player_idle_down_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "1")
    image_assets['player_idle_down_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "2")
    image_assets['player_idle_down_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "3")
    image_assets['player_idle_down_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "4")
    image_assets['player_idle_down_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "5")
    image_assets['player_idle_down_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_down.png', "6")

    image_assets['player_idle_up_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "1")
    image_assets['player_idle_up_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "2")
    image_assets['player_idle_up_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "3")
    image_assets['player_idle_up_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "4")
    image_assets['player_idle_up_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "5")
    image_assets['player_idle_up_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_up.png', "6")

    image_assets['player_idle_right_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "1")
    image_assets['player_idle_right_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "2")
    image_assets['player_idle_right_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "3")
    image_assets['player_idle_right_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "4")
    image_assets['player_idle_right_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "5")
    image_assets['player_idle_right_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_right.png', "6")

    image_assets['player_idle_left_1'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "1")
    image_assets['player_idle_left_2'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "2")
    image_assets['player_idle_left_3'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "3")
    image_assets['player_idle_left_4'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "4")
    image_assets['player_idle_left_5'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "5")
    image_assets['player_idle_left_6'] = ('assets/tinyadventurepack/Character/Char_one/Idle/Char_idle_left.png', "6")

    # player walk
    image_assets['player_walk_down_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "1")
    image_assets['player_walk_down_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "2")
    image_assets['player_walk_down_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "3")
    image_assets['player_walk_down_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "4")
    image_assets['player_walk_down_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "5")
    image_assets['player_walk_down_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_down.png', "6")

    image_assets['player_walk_up_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "1")
    image_assets['player_walk_up_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "2")
    image_assets['player_walk_up_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "3")
    image_assets['player_walk_up_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "4")
    image_assets['player_walk_up_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "5")
    image_assets['player_walk_up_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_up.png', "6")

    image_assets['player_walk_right_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "1")
    image_assets['player_walk_right_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "2")
    image_assets['player_walk_right_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "3")
    image_assets['player_walk_right_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "4")
    image_assets['player_walk_right_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "5")
    image_assets['player_walk_right_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_right.png', "6")

    image_assets['player_walk_left_1'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "1")
    image_assets['player_walk_left_2'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "2")
    image_assets['player_walk_left_3'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "3")
    image_assets['player_walk_left_4'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "4")
    image_assets['player_walk_left_5'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "5")
    image_assets['player_walk_left_6'] = ('assets/tinyadventurepack/Character/Char_one/Walk/Char_walk_left.png', "6")

    # player attack
    image_assets['player_atk_down_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "1")
    image_assets['player_atk_down_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "2")
    image_assets['player_atk_down_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "3")
    image_assets['player_atk_down_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "4")
    image_assets['player_atk_down_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "5")
    image_assets['player_atk_down_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_down.png', "6")

    image_assets['player_atk_up_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "1")
    image_assets['player_atk_up_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "2")
    image_assets['player_atk_up_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "3")
    image_assets['player_atk_up_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "4")
    image_assets['player_atk_up_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "5")
    image_assets['player_atk_up_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_up.png', "6")

    image_assets['player_atk_right_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "1")
    image_assets['player_atk_right_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "2")
    image_assets['player_atk_right_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "3")
    image_assets['player_atk_right_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "4")
    image_assets['player_atk_right_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "5")
    image_assets['player_atk_right_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_right.png', "6")

    image_assets['player_atk_left_1'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "1")
    image_assets['player_atk_left_2'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "2")
    image_assets['player_atk_left_3'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "3")
    image_assets['player_atk_left_4'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "4")
    image_assets['player_atk_left_5'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "5")
    image_assets['player_atk_left_6'] = ('assets/tinyadventurepack/Character/Char_one/Attack/Char_atk_left.png', "6")

    # skel idle
    image_assets['skel_idle_down_1'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_down.png', "1")
    image_assets['skel_idle_down_2'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_down.png', "2")
    image_assets['skel_idle_down_3'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_down.png', "3")
    image_assets['skel_idle_down_4'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_down.png', "4")
    image_assets['skel_idle_down_5'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_down.png', "5")
    image_assets['skel_idle_down_6'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_down.png', "6")

    image_assets['skel_idle_up_1'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_up.png', "1")
    image_assets['skel_idle_up_2'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_up.png', "2")
    image_assets['skel_idle_up_3'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_up.png', "3")
    image_assets['skel_idle_up_4'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_up.png', "4")
    image_assets['skel_idle_up_5'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_up.png', "5")
    image_assets['skel_idle_up_6'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_up.png', "6")

    image_assets['skel_idle_right_1'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_right.png', "1")
    image_assets['skel_idle_right_2'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_right.png', "2")
    image_assets['skel_idle_right_3'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_right.png', "3")
    image_assets['skel_idle_right_4'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_right.png', "4")
    image_assets['skel_idle_right_5'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_right.png', "5")
    image_assets['skel_idle_right_6'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_right.png', "6")

    image_assets['skel_idle_left_1'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_left.png', "1")
    image_assets['skel_idle_left_2'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_left.png', "2")
    image_assets['skel_idle_left_3'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_left.png', "3")
    image_assets['skel_idle_left_4'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_left.png', "4")
    image_assets['skel_idle_left_5'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_left.png', "5")
    image_assets['skel_idle_left_6'] = ('assets/tinyadventurepack/Skeleton/Idle/Skel_idle_left.png', "6")

    # skel walk
    image_assets['skel_walk_down_1'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_down.png', "1")
    image_assets['skel_walk_down_2'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_down.png', "2")
    image_assets['skel_walk_down_3'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_down.png', "3")
    image_assets['skel_walk_down_4'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_down.png', "4")
    image_assets['skel_walk_down_5'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_down.png', "5")
    image_assets['skel_walk_down_6'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_down.png', "6")

    image_assets['skel_walk_up_1'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_up.png', "1")
    image_assets['skel_walk_up_2'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_up.png', "2")
    image_assets['skel_walk_up_3'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_up.png', "3")
    image_assets['skel_walk_up_4'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_up.png', "4")
    image_assets['skel_walk_up_5'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_up.png', "5")
    image_assets['skel_walk_up_6'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_up.png', "6")

    image_assets['skel_walk_right_1'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_right.png', "1")
    image_assets['skel_walk_right_2'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_right.png', "2")
    image_assets['skel_walk_right_3'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_right.png', "3")
    image_assets['skel_walk_right_4'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_right.png', "4")
    image_assets['skel_walk_right_5'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_right.png', "5")
    image_assets['skel_walk_right_6'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_right.png', "6")

    image_assets['skel_walk_left_1'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_left.png', "1")
    image_assets['skel_walk_left_2'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_left.png', "2")
    image_assets['skel_walk_left_3'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_left.png', "3")
    image_assets['skel_walk_left_4'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_left.png', "4")
    image_assets['skel_walk_left_5'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_left.png', "5")
    image_assets['skel_walk_left_6'] = ('assets/tinyadventurepack/Skeleton/Walk/Skel_walk_left.png', "6")

    # OTHER
    image_assets['grass1'] = ('assets/tinyadventurepack/Other/Misc/Grass.png', None)
    image_assets['grass2'] = ('assets/tinyadventurepack/Other/Misc/Grass2.png', None)
    # image_assets['grass3'] = ('assets/tinyadventurepack/Other/Misc/Grass3.png', None)
    
    image_assets['grass3'] = ('assets/tinyadventurepack/Other/Green_orb.png', None)
    
    image_assets['tree'] = ('assets/tinyadventurepack/Other/Misc/Tree/Tree.png', None)
    image_assets['tree_trunk'] = ('assets/tinyadventurepack/Other/Misc/Tree/Tree_trunk.png', None)
    image_assets['tree_top'] = ('assets/tinyadventurepack/Other/Misc/Tree/Tree_top.png', None)
    image_assets['food'] = ('assets/tinyadventurepack/Other/Red_orb.png', None)
    image_assets['wood'] = ('assets/tinyadventurepack/Other/Misc/Tree/wood.png', None)
    image_assets['baby_tree'] = ('assets/tinyadventurepack/Other/Misc/Tree/baby_tree.png', None)

    image_assets['rock'] = ('assets/tinyadventurepack/Other/Misc/Rock.png', None)
    image_assets['deer'] = ('assets/tinyadventurepack/Other/Misc/deer.png', None)

    sound_assets = {}
    # sound_assets['crunch_eat'] = 'assets/sounds/crunch_eat.wav'
    sound_assets['bleep'] = 'assets/sounds/bleep.wav'
    music_assets = {}
    music_assets['background'] = "assets/music/PianoMonolog.ogg"

    return AssetBundle(
        image_assets=image_assets,
        sound_assets=sound_assets,
        music_assets=music_assets,
        tilemaploader = TileMapLoader())


player_idle_sprites = {
    'down': ['player_idle_down_1', 'player_idle_down_2', 'player_idle_down_3', 'player_idle_down_4', 'player_idle_down_5', 'player_idle_down_6'],
    'up': ['player_idle_up_1', 'player_idle_up_2', 'player_idle_up_3', 'player_idle_up_4', 'player_idle_up_5', 'player_idle_up_6'],
    'left': ['player_idle_left_1', 'player_idle_left_2', 'player_idle_left_3', 'player_idle_left_4', 'player_idle_left_5', 'player_idle_left_6'],
    'right': ['player_idle_right_1', 'player_idle_right_2', 'player_idle_right_3', 'player_idle_right_4', 'player_idle_right_5', 'player_idle_right_6']}

player_walk_sprites = {
    'down': ['player_walk_down_1', 'player_walk_down_2', 'player_walk_down_3', 'player_walk_down_4', 'player_walk_down_5', 'player_walk_down_6'],
    'up': ['player_walk_up_1', 'player_walk_up_2', 'player_walk_up_3', 'player_walk_up_4', 'player_walk_up_5', 'player_walk_up_6'],
    'left': ['player_walk_left_1', 'player_walk_left_2', 'player_walk_left_3', 'player_walk_left_4', 'player_walk_left_5', 'player_walk_left_6'],
    'right': ['player_walk_right_1', 'player_walk_right_2', 'player_walk_right_3', 'player_walk_right_4', 'player_walk_right_5', 'player_walk_right_6']}

player_attack_sprites = {
    'down': ['player_atk_down_1', 'player_atk_down_2', 'player_atk_down_3', 'player_atk_down_4', 'player_atk_down_5', 'player_atk_down_6'],
    'up': ['player_atk_up_1', 'player_atk_up_2', 'player_atk_up_3', 'player_atk_up_4', 'player_atk_up_5', 'player_atk_up_6'],
    'left': ['player_atk_left_1', 'player_atk_left_2', 'player_atk_left_3', 'player_atk_left_4', 'player_atk_left_5', 'player_atk_left_6'],
    'right': ['player_atk_right_1', 'player_atk_right_2', 'player_atk_right_3', 'player_atk_right_4', 'player_atk_right_5', 'player_atk_right_6']}

# Skel
skel_idle_sprites = {
    'down': ['skel_idle_down_1', 'skel_idle_down_2', 'skel_idle_down_3', 'skel_idle_down_4', 'skel_idle_down_5', 'skel_idle_down_6'],
    'up': ['skel_idle_up_1', 'skel_idle_up_2', 'skel_idle_up_3', 'skel_idle_up_4', 'skel_idle_up_5', 'skel_idle_up_6'],
    'left': ['skel_idle_left_1', 'skel_idle_left_2', 'skel_idle_left_3', 'skel_idle_left_4', 'skel_idle_left_5', 'skel_idle_left_6'],
    'right': ['skel_idle_right_1', 'skel_idle_right_2', 'skel_idle_right_3', 'skel_idle_right_4', 'skel_idle_right_5', 'skel_idle_right_6']}
skel_walk_sprites = {
    'down': ['skel_walk_down_1', 'skel_walk_down_2', 'skel_walk_down_3', 'skel_walk_down_4', 'skel_walk_down_5', 'skel_walk_down_6'],
    'up': ['skel_walk_up_1', 'skel_walk_up_2', 'skel_walk_up_3', 'skel_walk_up_4', 'skel_walk_up_5', 'skel_walk_up_6'],
    'left': ['skel_walk_left_1', 'skel_walk_left_2', 'skel_walk_left_3', 'skel_walk_left_4', 'skel_walk_left_5', 'skel_walk_left_6'],
    'right': ['skel_walk_right_1', 'skel_walk_right_2', 'skel_walk_right_3', 'skel_walk_right_4', 'skel_walk_right_5', 'skel_walk_right_6']}



def angle_to_direction(angle):
    angle_num = angle/math.pi
    direction = "down"
    if angle_num < 0.25 and angle_num >= -0.25:
        direction = "up"
    elif angle_num > 0.25 and angle_num <= 0.75:
        direction = "left"
    elif angle_num < -0.25 and angle_num >= -0.75:
        direction = "right"
    elif abs(angle_num) >= 0.75:
        direction = "down"
    return direction

"""
'type': 'idle',
'ticks':6,
'step_size':TILE_SIZE/6,
'start_tick': clock.get_tick_counter(),
'blocking':False

'start_position' used if position changes
"""

"""
OBJECT TYPES
- AnimateObject (can move, fire?, projectile)
- AnimalObject (monster,character)
- PlantObject (grows from seeds)
- ItemObject (collectable, used for crafting, or consumption)
- StaticObject (Rock Wall, Wood Wall, Water, Lava)
- Terrain (Water, ,)

"""

class PhysicalObject(GObject):


    def __init__(self,config={}, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.config = config
        self.type="NA"
        self.image_id_default = None
        self.health = 50
        self.created_tick = 0
        self.animated = True
        self.breakable = True
        self.collision = True

        # Can it be placed in inventory?
        self.collectable = False

        self.default_action_type = "idle"
        self._action = {}

        # Available States
        self.sprites = {}
        self.sprites[self.default_action_type] = None
        self.sprites['spawn'] = None
        self.default_action()
        self.disable()
        ShapeFactory.attach_rectangle(self, width=TILE_SIZE, height=TILE_SIZE)
        gamectx.add_object(self)

    def spawn(self,position):
        self._action = {
            'type': 'spawn',
            'ticks':1,
            'step_size':1,
            'start_tick': clock.get_tick_counter(),
            'blocking':True
        }
        self.health = 50
        self.created_tick = clock.get_tick_counter()
        self.enable()
        self.set_position(position=position)

    def get_action(self):
        cur_tick = clock.get_tick_counter()
        if not self._action.get('continuous',False)  and (cur_tick - self._action.get('start_tick',0) > self._action.get('ticks',1)):
            self.default_action()
        return self._action

    def default_action(self):
        ticks_in_action = 3 * gamectx.content.speed_factor()
        self._action = {
            'type': 'idle',
            'ticks':ticks_in_action,
            'step_size':TILE_SIZE/ticks_in_action,
            'start_tick': clock.get_tick_counter(),
            'blocking':False,
            'continuous':True

        }

    def move(self, direction, new_angle):
        move_speed = 1/3
        direction = direction * 1
        if new_angle is not None and self.angle != new_angle:
            ticks_in_action = gamectx.content.speed_factor()/move_speed
            self.angle = new_angle
            return []
        ticks_in_action = move_speed * gamectx.content.speed_factor()

        new_pos = TILE_SIZE * direction + self.get_position()
        self._action = \
            {
                'type': 'move',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
                'start_position': self.position,
                'blocking':True
            }

        self.update_position(new_pos)

    def get_image_id(self, angle):
        action = self.get_action()
        sprites = self.sprites.get(action['type'])
        if sprites is None:
            sprites = self.sprites.get(self.default_action_type)
        if sprites is None:
            return self.image_id_default

        direction = angle_to_direction(self.angle)

        cur_tick = clock.get_tick_counter()
        # TODO: Need to account for game speed
        action_idx = (cur_tick - action['start_tick'])
        total_sprite_images = len(sprites[direction])
        sprite_idx = int((action_idx/action['ticks']) * total_sprite_images)  % total_sprite_images
        return sprites[direction][sprite_idx]

    def get_view_position(self):
        cur_tick = clock.get_tick_counter()
        action = self.get_action()
        if action.get('start_position') is not None:
            idx = cur_tick - action['start_tick']
            direction = (self.position - action['start_position']).normalized()
            view_position = action['step_size'] * idx * direction + action['start_position']
            return view_position
        return self.get_position()

    def receive_damage(self, attacker_obj, damage):
        self.health -= damage
        if self.health <0:
            self.destroy()

    def destroy(self):
        if self.breakable:
            self.disable()


class AnimateObject(PhysicalObject):


    def __init__(self,player:Player= None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "animate"
        self.player_id=None
        if player is not None:
            self.set_player(player)

        self.rotation_multiplier = 1
        self.velocity_multiplier = 1
        self.walk_speed = 1/3

        self.attack_strength = 1
        self.energy = 100
        self.stamina = 100

        self.next_energy_decay = 0
        self.next_health_gen = 0
        self.next_stamina_gen = 0
        self.attack_speed = .3

        self.reward = 0

        # Visual Range in x and y direction
        self.vision_radius =  self.config.get('vision_radius',2)

        # TODO:
        self.inventory = {}
        self.inventory_capacity = 1
        self.inventory_slots = 1
        self.selected_item = None


    def spawn(self,position:Vector):
        super().spawn(position)
        self.energy = self.config.get('energy_start',100)
        self.health = self.config.get('health_start',100)
        self.stamina = self.config.get('stamina_max',100)
        self.attack_speed = self.config.get('attack_speed',0.3)
        self.walk_speed = self.config.get('walk_speed',0.3)
        self.next_energy_decay = 0
        self.next_health_gen = 0
        self.next_stamina_gen =0

    def set_player(self,player:Player):
        self.player_id = player.get_id()
        if player is not None:
            player.attach_object(self)

    def get_player(self)->Player:
        if self.player_id is None:
            return None
        else:
            return gamectx.player_manager.get_player(self.player_id)

    def get_visible_objects(self) -> List[PhysicalObject]:
        obj_coord = gamectx.physics_engine.vec_to_coord(self.get_position())

        col_min = obj_coord[0] - self.vision_radius
        col_max = obj_coord[0] + self.vision_radius
        row_min = obj_coord[1] - self.vision_radius
        row_max = obj_coord[1] + self.vision_radius
        obj_list = []
        for r in range(row_max, row_min-1, -1):
            for c in range(col_min, col_max+1):
                obj_ids = gamectx.physics_engine.space.get_objs_at((c, r))
                for obj_id in obj_ids:
                    obj_seen = gamectx.object_manager.get_by_id(obj_id)
                    if obj_seen.is_visible() and obj_seen.is_enabled():
                        obj_list.append(obj_seen)

        return obj_list

    def get_item_amount(self, name):
        return self.inventory.get(name,0)

    def modify_inventory(self, name, count):
        self.inventory[name] = self.get_item_amount(name) + count

    def walk(self, direction, new_angle):
        walk_speed = self.walk_speed
        if self.stamina <= 0:
            walk_speed = walk_speed/2
        else:
            self.stamina -= 15

        direction = direction * self.velocity_multiplier
        self.angle = new_angle
            
        ticks_in_action = gamectx.content.speed_factor()/walk_speed

        new_pos = TILE_SIZE * direction + self.get_position()
        self._action = \
            {
                'type': 'walk',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
                'start_position': self.position,
                'blocking':True
            }

        self.update_position(new_pos)

    def grab(self):

        ticks_in_action = int(gamectx.content.speed_factor())

        direction = Vector(0, 1).rotated(self.angle)

        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            target_obj:PhysicalObject = gamectx.object_manager.get_by_id(oid)
            print(target_obj.type)
            if target_obj.collectable:
                gamectx.remove_object(target_obj)
                self.modify_inventory(target_obj.type, 1)

        self._action = \
            {
                'type': 'grab',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action
            }

    def drop(self):
        ticks_in_action = int(gamectx.content.speed_factor())

        direction = Vector(0, 1).rotated(self.angle)

        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)
        oids = gamectx.physics_engine.space.get_objs_at(target_coord)

        if len(oids) == 0 or (len(oids) == 1 and gamectx.object_manager.get_by_id(oids[0]).type == 'grass'):
            if self.get_item_amount("rock") > 0:
                Rock().spawn(target_pos)
                self.modify_inventory("rock", -1)

        self._action = \
            {
                'type': 'drop',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }
        

    def attack(self):
        attack_speed = self.attack_speed

        if self.stamina <= 0:
            attack_speed = attack_speed/2
        else:
            self.stamina -= 15

        ticks_in_action = int(gamectx.content.speed_factor()/attack_speed)
        direction = Vector(0, 1).rotated(self.angle)
        target_pos = self.get_position() + (direction * TILE_SIZE)
        target_coord = gamectx.physics_engine.vec_to_coord(target_pos)

        for oid in gamectx.physics_engine.space.get_objs_at(target_coord):
            obj2: PhysicalObject = gamectx.object_manager.get_by_id(oid)
            obj2.receive_damage(self, self.attack_strength)

        self._action =\
            {
                'type': 'attack',
                'start_tick': clock.get_tick_counter(),
                'ticks': ticks_in_action,
                'step_size': TILE_SIZE/ticks_in_action,
            }

    def update(self):
        cur_time = clock.get_time()
        if cur_time > self.next_energy_decay:
            self.energy = max(0, self.energy - self.config.get('energy_decay',0))
            if self.energy <= 0:
                self.health -=  self.config.get('low_energy_health_penalty',0)
                
            self.next_energy_decay =  cur_time + (self.config.get('energy_decay_period',0) * gamectx.content.speed_factor())

        # Health regen
        if cur_time > self.next_health_gen:
            self.health = min(self.config.get('health_max',0), self.health + self.config.get('health_gen',0))
            self.next_health_gen = cur_time + (self.config.get('health_gen_period',0) * gamectx.content.speed_factor())

        # Stamina regen
        if cur_time > self.next_stamina_gen and self.stamina < self.config.get('stamina_max',50):
            self.stamina = min(self.config.get('stamina_max',10), self.stamina + self.config.get('stamina_gen',5))
            gen_delay = (self.config.get('stamina_gen_period',0) * gamectx.content.speed_factor())
            self.next_stamina_gen = cur_time + gen_delay
        


class Character(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "player"
        self.set_image_id("player_idle_down_1")
        self.sprites={}
        self.sprites['idle'] = player_idle_sprites
        self.sprites['walk'] = player_walk_sprites
        self.sprites['attack'] = player_attack_sprites

        self.next_energy_decay = 0
        self.next_health_gen = 0
        self.attack_strength = 10
        self.health =  40
    


    def update(self):
        super().update()

        p = self.get_player()

        # Check for death
        if self.health <= 0:
            lives_used = p.get_data_value("lives_used", 0)
            lives_used += 1
            p.set_data_value("lives_used", lives_used)
            self.disable()

            def event_fn(event: DelayedEvent, data):
                p.set_data_value("reset_required", True)
                return []
            delay = 10*gamectx.content.speed_factor()
            event = DelayedEvent(event_fn, delay)
            gamectx.add_event(event)

        else:
            p.set_data_value("allow_input", True)


class Monster(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "monster"

        self.set_image_id("skel_idle_down_1")
        self.sprites={}
        self.sprites['idle'] = skel_idle_sprites
        self.sprites['walk'] = skel_walk_sprites
        self.sprites['attack'] = skel_walk_sprites

        self.attack_strength = 10
        self.health =  40

    def update(self):
        super().update()
        if self.get_action().get('blocking',True):
            return

        # TODO: Actions should be processed as event
        for obj in self.get_visible_objects():
            if obj.type == "player":
                orig_direction: Vector = obj.get_position() - self.get_position()
                direction = orig_direction.normalized()
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
                new_angle = Vector(0, 1).get_angle_between(direction)
                if orig_direction.length <= gamectx.content.tile_size:
                    direction = Vector(0, 0)
                else:
                    direction = Vector(updated_x, updated_y)
                if orig_direction.length <= gamectx.content.tile_size and new_angle == self.angle:
                    self.attack()
                else:
                    self.walk(direction, new_angle)


class Deer(AnimateObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "deer"
        self.set_image_id("deer")

        # self.set_image_id("skel_idle_down_1")
        # self.sprites={}
        # self.sprites['idle'] = skel_idle_sprites
        # self.sprites['walk'] = skel_walk_sprites
        # self.sprites['attack'] = skel_walk_sprites

        self.attack_strength = 10
        self.health =  40

    def update(self):
        super().update()
        if self.get_action().get('blocking',True):
            return

        # TODO: Actions should be processed as event
        for obj in self.get_visible_objects():
            if obj.type == "player":
                orig_direction: Vector = obj.get_position() - self.get_position()
                direction = orig_direction.normalized()
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
                new_angle = Vector(0, 1).get_angle_between(direction)
                if orig_direction.length <= gamectx.content.tile_size:
                    direction = Vector(0, 0)
                else:
                    direction = Vector(-updated_x, -updated_y)
                if orig_direction.length <= gamectx.content.tile_size and new_angle == self.angle:
                    self.attack()
                else:
                    self.walk(direction, new_angle)


class Tree(PhysicalObject):


    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.type = "tree"
        self.health =  100
        self.set_visiblity(False)

    def spawn(self,position):
        super().spawn(position=position)
        self.trunk = self.add_tree_trunk()
        self.top = self.add_tree_top()

    def add_tree_trunk(self):
        o = PhysicalObject(depth=1)
        o.type = "part"
        o.set_image_id(f"tree_trunk")
        o.spawn(position=self.get_position())
        o.collision = False
        return o

    def add_tree_top(self):
        o = PhysicalObject(depth=3)
        o.type = "part"
        o.set_image_id(f"tree_top")
        o.set_image_offset(Vector(0, -gamectx.content.tile_size*1.4))
        o.spawn(position=self.get_position())
        o.collision = False
        return o

    def receive_damage(self, attacker_obj, damage):
        super().receive_damage(attacker_obj, damage)
        if self.health <=0:
            gamectx.remove_object(self.top)
            gamectx.remove_object(self.trunk)
            gamectx.remove_object(self)
            Wood().spawn(self.position)
            
        if self.health <20:
            self.top.disable()

        
        
class Wood(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'wood'
        self.set_image_id('wood')
        self.collectable = True
        self.collision = True
        self.breakable = False
        self.set_shape_color(color=(200, 200, 50))

    def spawn(self,position):
        super().spawn(position=position)




class Food(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'food'
        self.set_image_id('food')
        self.set_shape_color(color=(100, 130, 100))
        self.energy = gamectx.content.config['food_energy']
        self.collision = False
        

    def spawn(self,position):
        super().spawn(position=position)
        gamectx.data['food_counter'] = gamectx.data.get('food_counter', 0) + 1




class Rock(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 1
        self.type =  'rock'
        self.collectable = True
        self.set_image_id('rock')
        self.set_shape_color(color=(100, 130, 100))
        self.breakable=False


class Water(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 0
        self.type =  'water'
        self.set_shape_color(color=(30, 30, 150))
        self.breakable=False
        self.collision = False



class Grass(PhysicalObject):

    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.depth = 0
        self.type =  'grass'
        self.set_image_id(f"grass{random.randint(1,3)}")
        self.set_shape_color(color=(100, 130, 100))
        self.breakable=False
        self.collision = False


class WorldMap:

    def __init__(self,map_layers, seed = 123):
        self.seed = seed
        Water().spawn(coord_to_vec((0,0)))
        Water().spawn(coord_to_vec((3,2)))
        Water().spawn(coord_to_vec((2,3)))
        for i, layer in enumerate(map_layers):
            lines = layer.split("\n")
            self.spawn_locations = []
            for ridx, line in enumerate(reversed(lines)):
                for cidx, ch in enumerate(line):
                    coord = (cidx, ridx)
                    if ch == 'r':
                        Rock().spawn(coord_to_vec(coord))
                    elif ch == 'f':
                        gamectx.content.food_locations.append(coord)
                    elif ch == 's':
                        gamectx.content.spawn_locations.append(coord)
                    elif ch == 'g':
                        Grass().spawn(coord_to_vec(coord))
                    elif ch == 't':
                        Tree().spawn(coord_to_vec(coord))
                    elif ch == 'w':
                        Water().spawn(coord_to_vec(coord))
                    elif ch == 'm':
                        Monster(config=gamectx.content.config.get('monster_config',{})).spawn(coord_to_vec(coord))
                    elif ch == 'd':
                        Deer().spawn(coord_to_vec(coord))
                    elif ch == 'a':
                        AnimateObject().spawn(coord_to_vec(coord))
                        

    # def get_object_at(self,coord):
    #     # used seed + coord to get object type
