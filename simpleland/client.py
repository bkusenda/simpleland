
import argparse
import json
import logging
import math
import os
import random
import socket
import struct
import sys
import threading
import time
from multiprocessing import Queue
from typing import Tuple

import lz4.frame
import numpy as np
import pymunk
from pyinstrument import Profiler
from pymunk import Vec2d

from simpleland.common import (SimClock, Body, Camera, Clock, \
                               Shape, Vector, TimeLoggingContainer)
from simpleland.object import GObject
from simpleland.config import ClientConfig, GameConfig
from simpleland.content import Content
from simpleland.game import Game, StateDecoder, StateEncoder
from simpleland.itemfactory import ItemFactory, ShapeFactory
from simpleland.physics_engine import PhysicsEngine
from simpleland.player import Player, get_input_events
from simpleland.renderer import Renderer
from simpleland.utils import gen_id
from simpleland.event import InputEvent
import gym

HEADER_SIZE = 16
LATENCY_LOG_SIZE = 10000

def receive_data(sock):
    done = False
    all_data = b''
    while not done:
        sock.settimeout(1.0)
        data, server = sock.recvfrom(4096)
        chunk_num, chunks = struct.unpack('ll', data[:HEADER_SIZE])
        all_data += data[HEADER_SIZE:]
        if chunk_num == chunks:
            done = True
    return lz4.frame.decompress(all_data).decode('utf-8')


def send_request(request_data, server_address):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        data_st = json.dumps(request_data, cls=StateEncoder)
        # Send data
        sent = sock.sendto(lz4.frame.compress(bytes(data_st, 'utf-8')),
                           server_address)
        data = receive_data(sock)
    except Exception as e:
        print(e)
        return None
    finally:
        sock.close()
    return json.loads(data, cls=StateDecoder)


class ClientConnector:
    # TODO, change to client + server connection

    def __init__(self, config:ClientConfig):
        self.config = config
        self.incomming_buffer: Queue = Queue()  # event buffer
        self.outgoing_buffer: Queue = Queue()  # state buffer
        self.running = True
        self.client_id = self.config.client_id

        self.latency_log = [None for i in range(LATENCY_LOG_SIZE)]
        self.last_latency_ms = None
        self.request_counter = 0
        self.absolute_server_time = None

        self.clock = SimClock()  # clock for controlling network tick speed
        self.ticks_per_second = 64
        self.last_received_snapshots = []

    def add_network_info(self, latency: int, success: bool):
        self.latency_log[self.request_counter % LATENCY_LOG_SIZE] = {'latency': latency, 'success': success}

    def get_avg_latency(self):
        vals = [i for i in self.latency_log if i is not None]
        return math.fsum(vals['latency'])/len(vals)

    def get_success_rate(self):
        vals = [i for i in self.latency_log if i is not None]
        success = sum([1 for v in vals if v['success']])
        return success/len(vals)

    def create_request(self):
        request_info = {
            'client_id': "" if self.client_id is None else self.client_id,
            'last_latency_ms': self.last_latency_ms,
            'snapshots_received': self.last_received_snapshots,
            'player_type': self.config.player_type,
            'message': "UPDATE"
        }

        # Get items:
        outgoing_items = []
        done = False
        while (not done):
            if self.outgoing_buffer.qsize() == 0:
                done = True
                break
            outgoing_item = self.outgoing_buffer.get()
            if outgoing_item is None or len(outgoing_item) == 0:
                done = True
            else:
                outgoing_items.append(outgoing_item)

        start_time = time.time() * 1000
        response = send_request({
            'info': request_info,
            'items': outgoing_items},
            server_address = (self.config.server_hostname,self.config.server_port))
        last_latency_ms = (time.time() * 1000) - start_time

        if response is None:
            print("Packet loss or error occurred")
            self.add_network_info(last_latency_ms, False)
        else:
            # Log latency
            self.add_network_info(last_latency_ms, True)
            response_info = response['info']
            self.last_received_snapshots = [response_info['snapshot_timestamp']]

            # set clock
            self.absolute_server_time = (time.time()*1000) - float(response_info['server_time_ms']) - last_latency_ms

            self.client_id = response_info['client_id']
            if response_info['message'] == 'UPDATE':
                self.incomming_buffer.put(response)
            self.request_counter += 1
        self.clock.tick(self.ticks_per_second)

    def start_connection(self, callback=None):
        print("Starting connection to server")

        while self.running:
            self.create_request()


class GameClient:

    def __init__(self,
                 content: Content,
                 game: Game,
                 renderer: Renderer,
                 config: ClientConfig):

        self.config = config
        self.game = game
        self.content = content
        self.render_delay_in_ms = 60  # tick gap + latency
        self.frames_per_second = config

        self.server_info_history = TimeLoggingContainer(100)
        self.player: Player = None  # TODO: move to history data managed for rendering consistency
        self.step_counter = 0
        self.renderer = renderer

        self.connector = ClientConnector(config= config)
        #TODO, separate process instead?
        self.connector_thread = threading.Thread(target=self.connector.start_connection, args=())
        self.connector_thread.daemon = True
        self.connector_thread.start()

    def load_response_data(self):
        done = False
        while (not done):
            if self.connector.incomming_buffer.qsize() == 0:
                incomming_data = None
            else:
                incomming_data = self.connector.incomming_buffer.get()
            if incomming_data is None:
                done = True
                break
            else:
                self.game.load_snapshot(incomming_data['snapshot'])
                self.server_info_history.add(
                    incomming_data['info']['snapshot_timestamp'],
                    incomming_data['info'])

    def run_step(self):
        if self.connector.absolute_server_time is not None:
            self.game.clock.set_absolute_time(self.connector.absolute_server_time)

        render_time = max(0, self.game.clock.get_time() - self.render_delay_in_ms)

        # Get Input Events and put in output buffer
        # TODO: make logic cleaner
        if self.player is not None:
            events = []
            if self.config.is_human:
                input_events = get_input_events(self.player.get_id())
                events.extend(input_events)
            events.extend(self.player.pull_input_events())
            self.game.event_manager.add_events(events)

        event_snapshot = self.game.event_manager.get_snapshot()
        if self.connector.outgoing_buffer.qsize() < 30:
            self.connector.outgoing_buffer.put(event_snapshot)

        # Clear Events after sending to Server
        # TODO: add support for selective removal of events. eg keep local events  like quite request
        self.game.event_manager.clear()

        # Get Game Snapshot
        self.load_response_data()

        server_info_timestamp, server_info = self.server_info_history.get_prev_entry(render_time)
        # Note, loaded immediately rather than at render time. this could be an issue?
        if server_info is not None and server_info['player_id'] is not "":
            self.player = self.game.player_manager.get_player(server_info['player_id'])
            # obj = self.game.get_object_manager().get_by_id(self.player.get_object_id(),render_time)

        self.renderer.process_frame(
            render_time=render_time,
            player=self.player,
            game=self.game)

        self.content.post_process_frame(
            render_time=render_time,
            game=self.game,
            player=self.player,
            renderer=self.renderer)

        self.renderer.render_frame()
        if self.config.is_human:
            self.renderer.play_sounds(self.game.get_sound_events(render_time))
        self.game.run_event_processing()
        self.game.clock.tick(self.config.frames_per_second)
        self.game.cleanup()
        self.step_counter += 1

    def run(self):
        while self.game.game_state == "RUNNING":
            self.run_step()
from simpleland.environment import load_environment, get_env_content, EnvironmentDefinition


class Launcher:

    def __init__(self,env_def:EnvironmentDefinition):
        self.env_def = env_def

        self.game = Game(
            physics_config=env_def.physics_config,
            config=env_def.game_config)

        self.content = get_env_content(env_def)

        self.renderer = Renderer(
            env_def.renderer_config,
            asset_bundle=self.content.get_asset_bundle())
    
    def get_game_client(self):

        return GameClient(
            content=self.content,
            game=self.game,
            renderer=self.renderer,
            config=self.env_def.client_config)

from gym import spaces


# AGENT_KEYMAP = [0,17,5,23,19,1,4]

class SimpleLandEnv(gym.Env):

    def __init__(self,resolution=(30, 30), env_id="g1", client_id = 'agent', hostname = 'localhost', port = 10001, dry_run=False, keymap = [0,23,19,1,4]):
        self.keymap = keymap
        self.env_def = load_environment(env_id)
        self.env_def.client_config.is_human = False
        self.env_def.renderer_config.resolution = resolution
        self.env_def.renderer_config.sdl_audio_driver = 'dsp'
        self.env_def.renderer_config.render_to_screen = True
        # self.config_manager.renderer_config.sdl_video_driver = 'dummy'
        self.env_def.renderer_config.sound_enabled = False
        self.env_def.renderer_config.show_console = False
        self.env_def.client_config.player_type = 0
        self.env_def.client_config.client_id = client_id
        self.env_def.client_config.server_hostname = hostname
        self.env_def.client_config.server_port = port
        self.launcher = Launcher(self.env_def)
        self.connector = None
        self.connector_thread = None
        self.dry_run = dry_run

        if not self.dry_run:
            self.game_client:GameClient = self.launcher.get_game_client()
        else:
            self.game_client:GameClient = None


        self.action_space = spaces.Discrete(5)
        self.observation_space = spaces.Box(0, 255, (resolution[0], resolution[1],3))
        logging.info("Ob space: {}".format(self.observation_space))
        
        self.ob = None
        self.safe_mode = True
        self.running = True


    def step(self, action):
        if self.dry_run:
            return self.observation_space.sample(), 1, False, None
        if self.game_client.player is not None:
            event = InputEvent(
                player_id  = self.game_client.player.get_id(), 
                input_data = {
                    'inputs':{self.keymap[action]:1},
                    'mouse_pos': "",
                    'mouse_rel': "",
                    'focused': ""
                    })
            self.game_client.player.add_event(event)
        # obs, step_reward, done = self.game.manual_player_action_step({int(action)}, self.player.uid)
        self.game_client.run_step()
        self.ob = self.launcher.renderer.get_observation()
        reward, done = self.game_client.content.get_step_info(
            player= self.game_client.player,
            game=self.game_client.game)


        return self.ob, reward, done, None

    def render(self, mode=None):
        if self.dry_run:
            return self.observation_space.sample()
        return self.launcher.renderer.frame_cache
        # img = self.game_client.renderer.renderer.render_frame()
        # return img

    def reset(self):
        done = True
        count = 0
        wait_time = 0.001
        while done: 
            self.ob, reward, done, _ = self.step(0)
            if done:
                count +=1
                time.sleep(count * wait_time)
                if ((count + 1)  % 100) == 0:
                    print("Waiting for game reset {}".format(count))
        return self.ob


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", default="640x480", help="resolution eg, [f,640x480]")
    parser.add_argument("--hostname", default="localhost", help="hostname or ip, default is localhost")
    parser.add_argument("--port", default=10001, help="port")
    parser.add_argument("--client_id", default=gen_id(), help="user id, default is random")
    parser.add_argument("--render_shapes", action='store_true', help="render actual shapes")
    parser.add_argument("--enable_profiler", action="store_true", help="Enable Performance profiler")
    parser.add_argument("--player_type", default=0, help="Player type (0=default, 1=observer)")
    parser.add_argument("--env_id", default="g1", help="id of environment")

    args = parser.parse_args()

    if args.enable_profiler:
        print("Profiling Enabled..")
        profiler = Profiler()
        profiler.start()

    env_def = load_environment(args.env_id)

    

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
    

    env_def.renderer_config.resolution = resolution

    env_def.renderer_config.render_shapes = args.render_shapes

    launcher = Launcher(env_def)

    try:

        game_client = launcher.get_game_client()
        game_client.run()
    except (KeyboardInterrupt, SystemExit):
        if args.enable_profiler:
            profiler.stop()
            print(profiler.output_text(unicode=True, color=True))
        exit()




if __name__ == "__main__":
    main()
