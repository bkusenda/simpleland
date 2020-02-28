
import socket
import sys

import logging
from typing import Tuple

import numpy as np

from simpleland.common import (SLObject, SLVector, SLShape, SLCamera, SLBody)
from simpleland.core import SLPhysicsEngine
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer

from pymunk import Vec2d
import pymunk

import os
import json


def receive_data(sock):
    done = False
    all_data = ""
    while not done:
        data, server = sock.recvfrom(10000)
        data_parts = data.decode("utf-8").split("<<<")
        all_data += data_parts[1]
        header = data_parts[0].split(",")
        chunk_num = int(header[0])
        chunks = int(header[1])
        if chunk_num == chunks:
            done = True
    return all_data

def send_request(request_data , server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        data_st = json.dumps(request_data, cls=StateEncoder) + "\n"
        # Send data
        sent = sock.sendto(data_st.encode("utf-8"), 
            server_address)
        data = receive_data(sock)
    finally:
        sock.close()
    return json.loads(data, cls=StateDecoder)


def start_game(resolution):

    # Create a UDP socket
    server_address = ('localhost', 10000)

    # Create Player
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    # os.environ["SDL_VIDEODRIVER"] = "dummy"

    # Create Renderer
    renderer = SLRenderer(resolution)
    renderer.on_init()

    game = SLGame()
    game.start()

    player = None
    step_counter = 0

    while game.game_state == "RUNNING":
        
        response = send_request({
                'player_id': "" if player is None else player.uid, 
                'event_manager': game.event_manager.get_snapshot()},
            server_address)
        game.event_manager.clear()
        game.load_game_snapshot(response['game_snapshot'])

        if player is None:
            player = SLHumanPlayer.build_from_dict(response['player'])
            game.add_player(player)

        
        # Get Input From Players
        game.check_game_events()
        game.event_manager.add_events(game.player_manager.pull_events())
        game.event_manager.add_events(game.physics_engine.pull_events())
        game.physics_engine.apply_events(game.event_manager,game.object_manager,remove_processed=False)
        game.physics_engine.update(game.object_manager)


        # game.check_game_events()
        # game.physics_engine.apply_events(game.event_manager, game.object_manager)
        # game.physics_engine.update(game.event_manager, game.object_manager)
        # print(game.event_manager.get_snapshot())

        # Render
        renderer.process_frame(player.get_object_id(),game.object_manager)
        renderer.render_frame()
        
        step_counter += 1



    # # Run Game
    # game.run(player.get_object_id(), renderer=renderer, max_steps=None)




def main():
    start_game(resolution=(640, 480))


if __name__ == "__main__":
    main()
