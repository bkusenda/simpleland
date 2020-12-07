
import argparse
import json
import logging
import math
import random
import socketserver
import struct
import threading
import time
from multiprocessing import Queue
from typing import Any, Dict, Tuple

import lz4.frame
import numpy as np
import pymunk
from pyinstrument import Profiler
from pymunk import Vec2d

from simpleland.common import (SimClock, Body, Camera, Circle, Clock,
                               Line, Polygon, Shape, Space,
                               Vector, TimeLoggingContainer)

from simpleland.object import GObject
from simpleland.config import ServerConfig
from simpleland.content import Content
from simpleland.event import PeriodicEvent, SoundEvent
from simpleland.game import Game, StateDecoder, StateEncoder
from simpleland.itemfactory import ItemFactory, ShapeFactory
from simpleland.object_manager import GObjectManager
from simpleland.physics_engine import PhysicsEngine
from simpleland.player import  Player
from simpleland.renderer import Renderer
from simpleland.utils import gen_id
from simpleland.client import GameClient

LATENCY_LOG_SIZE = 100

class ClientInfo:
    """
    Stores Client session info 
    """

    def __init__(self, client_id):
        self.id = client_id
        self.last_snapshot_time_ms = 0
        self.latency_history = [None for i in range(LATENCY_LOG_SIZE)]
        self.player_id = None
        self.conn_info = None
        self.request_counter = 0
        self.unconfirmed_messages = set()

    def add_latency(self, latency: float):
        self.latency_history[self.request_counter % LATENCY_LOG_SIZE] = latency
        self.request_counter += 1

    def avg(self):
        vals = [i for i in self.latency_history if i is not None]
        return math.fsum(vals)/len(vals)

    def get_id(self):
        return self.id


class GameRunner:
    """
    Runs server game loop
    """

    def __init__(self,
                content: Content,
                game: Game,
                client_only_mode=False):

        self.game = game
        self.content = content
        self.clients = {}
        self.local_clients = []
        self.client_only_mode = client_only_mode

    def add_local_client(self,client):
        self.local_clients.append(client)
        

    def get_client(self, client_id) -> ClientInfo:
        client = self.clients.get(client_id, None)
        if client is None:
            client = ClientInfo(client_id)
            self.clients[client.id] = client
        return client
    
    def get_player(self, client, player_type):
        """
        Get existing player or create new one
        """
        if client.player_id is None:
            player = self.content.new_player(self.game, player_type=player_type)
            client.player_id = player.get_id()
        else:
            player = self.game.player_manager.get_player(client.player_id)
        return player

    def run_step(self):
        for client in self.local_clients:
            client.run_step()

        if self.client_only_mode:
            self.game.run_event_processing()
        else:
            self.game.run_pre_event_processing()
            self.game.run_event_processing()
            self.game.run_pre_physics_processing()
            self.game.run_physics_processing()
        self.game.tick()
        self.game.cleanup()

    def run(self):
        while self.game.game_state == "RUNNING":
            self.run_step()


class UDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        game_runner: GameRunner = self.server.game_server
        config:ServerConfig = self.server.config

        # Process Request data
        request_st = lz4.frame.decompress(self.request[0]).decode('utf-8').strip()
        try:
            request_data = json.loads(request_st, cls=StateDecoder)
        except Exception as e:
            print(request_st)
            raise e

        request_info = request_data['info']

        request_message = request_info['message']
        client = game_runner.get_client(request_info['client_id'])
        player = game_runner.get_player(client, player_type = request_info['player_type'])

        snapshots_received = request_info['snapshots_received']

        # simulate missing parts
        skip_remove = False  # random.random() < 0.01

        for t in snapshots_received:
            if t in client.unconfirmed_messages:
                if skip_remove:
                    print("Skipping remove confirmation")
                    continue
                else:
                    client.unconfirmed_messages.remove(t)

        # Load events from client
        all_events_data = []
        for event_dict in request_data['items']:
            all_events_data.extend(event_dict)

        if len(all_events_data) > 0:
            game_runner.game.event_manager.load_snapshot(all_events_data)

        if len(client.unconfirmed_messages) < config.max_unconfirmed_messages_before_new_snapshot:
            snapshot_timestamp, snapshot = game_runner.game.create_snapshot(client.last_snapshot_time_ms)
        else:
            print("Too many unconfirmed, packets full update required")
            snapshot_timestamp, snapshot = game_runner.game.create_snapshot_for_client(0)
            client.unconfirmed_messages.clear()
        client.unconfirmed_messages.add(snapshot_timestamp)

        # Build response data
        response_data = {}
        response_data['info'] = {
            'server_time_ms': game_runner.game.clock.get_exact_time(),
            'message': "UPDATE",
            'client_id': client.get_id(),
            'player_id': player.get_id(),
            'snapshot_timestamp': snapshot_timestamp}
        response_data['snapshot'] = snapshot

        # Convert response to json then compress and send in chunks
        response_data_st = json.dumps(response_data, cls=StateEncoder)
        response_data_st = bytes(response_data_st, 'utf-8')
        response_data_st = lz4.frame.compress(response_data_st)

        chunk_size = config.outgoing_chunk_size
        chunks = math.ceil(len(response_data_st)/chunk_size)
        socket = self.request[1]
        for i in range(chunks+1): # TODO: +1 ??? why
            header = struct.pack('ll', i+1, chunks)
            data_chunk = header + response_data_st[i*chunk_size:(i+1)*chunk_size]
            current_thread = threading.current_thread()
            # Simulate packet loss
            # if random.random() < 0.01:
            #     print("random skip chunk")
            #     continue
            socket.sendto(data_chunk, self.client_address)

        client.last_snapshot_time_ms = snapshot_timestamp


class GameUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):

    def __init__(self, conn, handler, game_runner, config):
        socketserver.UDPServer.__init__(self, conn, handler)
        self.game_server = game_runner
        self.config = config


from simpleland.environment import load_environment, get_env_content

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # Server
    parser.add_argument("--enable_server",  action="store_true", help="Accepts remote clients")
    
    # Client
    parser.add_argument("--enable_client",  action="store_true", help="Run Client")
    parser.add_argument("--remote_client",   action="store_true", help="client uses server")

    parser.add_argument("--resolution", default="640x480", help="resolution eg, [f,640x480]")
    parser.add_argument("--hostname", default=None, help="hostname or ip, default is localhost")
    parser.add_argument("--client_id", default=gen_id(), help="user id, default is random")
    parser.add_argument("--render_shapes", action='store_true', help="render actual shapes")
    parser.add_argument("--disable_textures", action='store_true', help="don't show images")
    parser.add_argument("--fps", default=60, type=int,help="fps")    
    parser.add_argument("--player_type", default=0, help="Player type (0=default, 1=observer)")

    # used for both client and server
    parser.add_argument("--port", default=10001, help="the port the server is running on")   

    # Game Options
    parser.add_argument("--enable_profiler", action="store_true", help="Enable Performance profiler")
    parser.add_argument("--physics_tick_rate", default=60, type=int,help="physics_tick_rate: approx physics updates per second (physics accuracy is controlled via sim_timestep)")
    parser.add_argument("--sim_timestep", default=0.01, type=float,help="sim_timestep, lower (eg 0.01) = more accurate, higher (eg 0.1) = less accurate but faster")
    parser.add_argument("--game_tick_rate", default=60, type=int,help="game_tick_rate")
    
    parser.add_argument("--env_id", default="g1", help="id of environment")

    args = parser.parse_args()

    if args.enable_server and args.enable_client and args.remote_client:
        print("Error: Server and Remote Client cannot be started from the same process. Please run seperately.")
        exit(1)


    profiler = None
    if args.enable_profiler:
        print("Profiling Enabled..")
        profiler = Profiler()
        profiler.start()


    env_def = load_environment(args.env_id)

    env_def.physics_config.tick_rate = args.physics_tick_rate

    # Get resolution
    if args.resolution == 'f':
        import pygame
        pygame.init()
        infoObject = pygame.display.Info()
        resolution = (infoObject.current_w, infoObject.current_h)
    else:
        res_string = args.resolution.split("x")
        resolution = (int(res_string[0]), int(res_string[1]))

    env_def.client_config.player_type = args.player_type
    env_def.client_config.client_id = args.client_id
    env_def.client_config.server_hostname = args.hostname
    env_def.client_config.server_port = args.port
    env_def.client_config.frames_per_second = args.fps
    env_def.client_config.is_remote =  args.remote_client
    env_def.game_config.tick_rate = args.game_tick_rate
    env_def.physics_config.sim_timestep = args.sim_timestep
    
    env_def.renderer_config.resolution = resolution

    env_def.renderer_config.render_shapes = args.render_shapes
    env_def.renderer_config.disable_textures = args.disable_textures
    print(env_def)

    game = Game(
        physics_config=env_def.physics_config,
        config=env_def.game_config)


    # Load Content
    # TODO: load from file
    content = get_env_content(env_def)
    client_only_mode=not args.enable_server and args.remote_client
    if not client_only_mode:
        print("Loading Game Content.")
        content.load(game)

    runner = GameRunner(content=content,game=game,client_only_mode=client_only_mode)

    if args.enable_client:
        renderer = Renderer(
            env_def.renderer_config,
            asset_bundle=content.get_asset_bundle())

        client = GameClient(
                content=content,
                game=game,
                renderer=renderer,
                config=env_def.client_config)

        runner.add_local_client(client)


    server = None
    try:
        if args.enable_server:        
            server = GameUDPServer(
                ("0.0.0.0", args.port), UDPHandler,
                game_runner=runner, config = env_def.server_config)

            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            print("Server started at {} port {}".format("0.0.0.0", args.port))

        runner.run()
    finally:
        if args.enable_server:
            server.shutdown()
            server.server_close()

        if args.enable_profiler:
            profiler.stop()
            print(profiler.output_text(unicode=True, color=True))
        exit()
        