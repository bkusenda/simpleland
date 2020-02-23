import logging
from typing import Tuple

import numpy as np

from simpleland.common import (FollowBehaviour, SLBody, SLObject, SLPoint,
                               SLViewer)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer

import os
def start_game(resolution):

    # Create Player
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    # os.environ["SDL_VIDEODRIVER"] = "dummy"


    player_object = SLObject(SLBody(mass=8, moment=30), viewer=SLViewer(distance=22))
    player_object.set_position(SLPoint(10, 10))

    SLShapeFactory.attach_psquare(player_object, 1)

    box = SLItemFactory.box(
        body=SLBody(mass=11, moment=1),
        position=SLPoint(2, 2),
        size=1)

    # triangle = SLItemFactory.triangle(
    #     body=SLBody(mass=11, moment=1),
    #     position=SLPoint(4, 4),
    #     size=1)

    hostile_object = SLObject(SLBody(mass=50, moment=1))
    hostile_object.set_position(position=SLPoint(6, 6))
    hostile_object.attach_behavior(FollowBehaviour(player_object))
    SLShapeFactory.attach_circle(hostile_object, 1)

    items = []

    # for i in range(0, 10):
    #     pos = SLPoint(random.randint(0, 10), random.randint(0, 10))
    #     item = SLItemFactory.box(body=SLBody(mass=11, moment=1),
    #                              position=pos,
    #                              size=1)
    #
    #     items.append(item)

    game = SLGame()


    wall = SLItemFactory.border(game.physics_engine.space.static_body,
                                SLPoint(0, 0),
                                size=20)

    game.attach_objects([player_object])
    game.attach_objects([box])
    # universe.attach_objects([triangle])
    game.attach_objects([hostile_object])
    # universe.attach_objects(items)

    game.attach_static_objects([wall])

    player = SLHumanPlayer()
    player.attach_object(player_object)

    # ADD logic
    # TODO Move some where that makes sense, rules?

    game.physics_engine.add_player_collision_event(player, hostile_object)

    game.add_player(player)
    renderer = SLRenderer(resolution)
    renderer.on_init()

    game.run(player.get_object(), renderer=renderer)


def main():
    start_game(resolution=(640, 480))


if __name__ == "__main__":
    main()
