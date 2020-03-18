
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

from simpleland.common import (SimClock, SLBody, SLCamera, SLCircle, SLClock,
                               SLLine, SLObject, SLPolygon, SLShape, SLSpace,
                               SLVector, TimeLoggingContainer)
from simpleland.config import ConfigManager, ServerConfig
from simpleland.content_manager import ContentManager
from simpleland.event_manager import SLPeriodicEvent, SLSoundEvent
from simpleland.game import SLGame, StateDecoder, StateEncoder
from simpleland.itemfactory import SLItemFactory, SLShapeFactory
from simpleland.object_manager import SLObjectManager
from simpleland.physics_engine import SLPhysicsEngine
from simpleland.player import SLAgentPlayer, SLHumanPlayer, SLPlayer
from simpleland.renderer import SLRenderer
from simpleland.utils import gen_id

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


class GameServer:
    """
    Runs server game loop
    """

    def __init__(self,
                 config: ServerConfig,
                 content_manager: ContentManager,
                 game: SLGame):

        self.config = config
        self.game = game
        self.content_manager = content_manager
        self.clients = {}

    def get_client(self, client_id) -> ClientInfo:
        client = self.clients.get(client_id, None)
        if client is None:
            client = ClientInfo(client_id)
            self.clients[client.id] = client
        return client

    def get_player(self, client):
        """
        Get existing player or create new one
        """
        if client.player_id is None:
            player = self.content_manager.new_player(self.game)
            client.player_id = player.get_id()
        else:
            player = self.game.player_manager.get_player(client.player_id)
        return player

    def run(self):
        """
        Server Game Loop
        """
        while self.game.game_state == "RUNNING":
            self.game.run_pre_event_processing()
            self.game.run_event_processing()
            self.game.run_pre_physics_processing()
            self.game.run_physics_processing()
            self.game.tick()


class UDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        game_server: GameServer = self.server.game_server

        # Process Request data
        request_st = lz4.frame.decompress(self.request[0]).decode('utf-8').strip()
        try:
            request_data = json.loads(request_st, cls=StateDecoder)
        except Exception as e:
            print(request_st)
            raise e

        request_info = request_data['info']

        request_message = request_info['message']
        client = game_server.get_client(request_info['client_id'])
        player = game_server.get_player(client)

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
            game_server.game.event_manager.load_snapshot(all_events_data)

        if len(client.unconfirmed_messages) < game_server.config.max_unconfirmed_messages_before_new_snapshot:
            snapshot_timestamp, snapshot = game_server.game.create_snapshot(client.last_snapshot_time_ms)
        else:
            print("To many unconfirmed, packets full update required")
            snapshot_timestamp, snapshot = game_server.game.create_snapshot_for_client(0)
            client.unconfirmed_messages.clear()
        client.unconfirmed_messages.add(snapshot_timestamp)

        # Build response data
        response_data = {}
        response_data['info'] = {
            'server_time_ms': game_server.game.clock.get_exact_time(),
            'message': "UPDATE",
            'client_id': client.get_id(),
            'player_id': player.get_id(),
            'snapshot_timestamp': snapshot_timestamp}
        response_data['snapshot'] = snapshot

        # Convert response to json then compress and send in chunks
        response_data_st = json.dumps(response_data, cls=StateEncoder)
        response_data_st = bytes(response_data_st, 'utf-8')
        response_data_st = lz4.frame.compress(response_data_st)

        chunk_size = game_server.config.outgoing_chunk_size
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

    def __init__(self, conn, handler, game_server):
        socketserver.UDPServer.__init__(self, conn, handler)
        self.game_server = game_server


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=10001, help="port")
    parser.add_argument("--enable_profiler", action="store_true", help="Enable Performance profiler")

    args = parser.parse_args()

    HOST, PORT = "0.0.0.0", args.port

    if args.enable_profiler:
        print("Profiling Enabled..")
        profiler = Profiler()
        profiler.start()

    config_manager = ConfigManager()
    # TODO: load from file

    game = SLGame(
        physics_config=config_manager.physics_config,
        config=config_manager.game_config)

    content_manager = ContentManager(
        config=config_manager.content_config)

    content_manager.load(game)

    game_server = GameServer(
        config=config_manager.server_config,
        content_manager=content_manager,
        game=game)

    server = GameUDPServer(
        (HOST, PORT), UDPHandler,
        game_server=game_server)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True

    try:
        server_thread.start()
        print("Server started at {} port {}".format(HOST, PORT))
        game_server.run()

    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        server.server_close()
        if args.enable_profiler:
            profiler.stop()
            print(profiler.output_text(unicode=True, color=True))
        exit()
        