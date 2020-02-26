import logging
from typing import Tuple

import numpy as np

from simpleland.common import (SLBody, SLObject, SLVector, SLShape, SLCamera)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer

from pymunk import Vec2d
import pymunk

import os

def start_game(resolution):

    # Create Player
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    # os.environ["SDL_VIDEODRIVER"] = "dummy"

    # Create Player
    player_object = SLObject(SLBody(mass=8, moment=30), camera=SLCamera(distance=22))
    player_object.set_position(SLVector(10, 10))
    SLShapeFactory.attach_psquare(player_object, 1)

    player = SLHumanPlayer()
    player.attach_object(player_object)

    # Create Game
    game = SLGame()

        # Create Wall
    wall = SLItemFactory.border(SLBody(body_type=pymunk.Body.STATIC),
                                SLVector(0, 0),
                                size=20)

    # # Create Wall
    # wall = SLItemFactory.border(game.physics_engine.space.static_body,
    #                             SLVector(0, 0),
    #                             size=20)
    # # # Create Box 
    # box = SLItemFactory.box(
    #     body=SLBody(mass=11, moment=1),
    #     position=SLVector(2, 2),
    #     size=1)

    # Create Hostile
    hostile_object = SLObject(SLBody(mass=50, moment=1))
    hostile_object.set_position(position=SLVector(6, 6))
    SLShapeFactory.attach_circle(hostile_object, 1)
    SLShapeFactory.attach_psquare(hostile_object,0.5)




    # Add objects to game
    game.attach_static_objects([wall])
    # game.attach_objects([box])
    game.attach_objects([hostile_object])
    game.attach_objects([player_object])

    # Add Player to game
    game.add_player(player)

    def collision_callback(arbiter:pymunk.Arbiter,space,data):
        for s in arbiter.shapes:
            s:SLShape = s
            o = game.object_manager.get(s.get_object_id())
            o.set_energy(o.get_energy() - 1)
            #print(o.get_snapshot())

    game.physics_engine.enable_collision_detection(collision_callback)

    # Create Renderer
    renderer = SLRenderer(resolution)
    renderer.on_init()

    # Run Game
    game.run(player.get_object(), renderer=renderer, max_steps=None)



def main():
    start_game(resolution=(640, 480))


if __name__ == "__main__":
    main()
