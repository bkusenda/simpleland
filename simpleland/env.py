
from simpleland.registry import get_game_content, GameDef
import gym
from gym import spaces
import logging
from simpleland.runner import get_game_def, get_player_def, UDPHandler, GameUDPServer
from simpleland.event import InputEvent
import threading

from simpleland.player import  Player
from simpleland.renderer import Renderer
from simpleland.utils import gen_id
from . import gamectx
from simpleland.client import GameClient
from simpleland.registry import load_game_def, get_game_content
import time
from typing import Dict, Any
# AGENT_KEYMAP = [0,17,5,23,19,1,4]
import numpy as np


keymap = [23,1,4]

class SimpleLandEnv:

    def __init__(self, 
            resolution=(200,200), 
            game_id="space_ship1", 
            hostname = 'localhost', 
            port = 10001, 
            dry_run=False,
            agent_map={},
            physics_tick_rate = 60,
            game_tick_rate = 2000,
            sim_timestep = 0.01,
            enable_server = True,
            num_feelers = 8):
        # import pygame
        # pygame.init()
        game_def = get_game_def(
            game_id=game_id,
            enable_server=enable_server, 
            port=port,
            remote_client=False,
            physics_tick_rate=physics_tick_rate,
            game_tick_rate = game_tick_rate,
            sim_timestep=sim_timestep)

        game_def.content_config['num_feelers'] = num_feelers
        self.content = get_game_content(game_def)

        gamectx.initialize(
            game_def = game_def,
            content=self.content)

        # Build Clients
        self.agent_map = agent_map
        self.agent_clients = {}
        player_def = None
        for agent_id, agent_info in agent_map.items():
            player_def = get_player_def(
                enable_client=True,
                client_id = agent_id,
                remote_client=False,
                hostname=hostname,
                port = port,
                resolution = resolution,#agent_info['resolution'],
                fps=game_tick_rate,
                player_type=0,
                is_human=False)

            # Render config changes
            player_def.renderer_config.sdl_audio_driver = 'dsp'
            player_def.renderer_config.render_to_screen = True
            # self.config_manager.renderer_config.sdl_video_driver = 'dummy'
            player_def.renderer_config.sound_enabled = False
            player_def.renderer_config.show_console = False

            renderer = Renderer(
                player_def.renderer_config,
                asset_bundle=self.content.get_asset_bundle()
                )

            client = GameClient(
                    renderer=renderer,
                    config=player_def.client_config)
            gamectx.add_local_client(client)
            self.agent_clients[agent_id]=client

        self.dry_run = dry_run
  
        self.action_space = spaces.Discrete(len(keymap))
        # self.observation_space = spaces.Box(0, 255, (resolution[0], resolution[1],3))
        self.observation_space = self.content.get_observation_space()
        logging.info("Ob space: {}".format(self.observation_space))
        self.action_freq = 1
        self.step_counter = 0
        
        self.ob = None
        self.safe_mode = True
        self.running = True
        self.server=None

        if game_def.server_config.enabled:        
            self.server = GameUDPServer(
                conn = (game_def.server_config.hostname, game_def.server_config.port), 
                handler=UDPHandler,
                config = game_def.server_config)

            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            print("Server started at {} port {}".format(game_def.server_config.hostname, game_def.server_config.port))

    def step(self, actions):

        # get actions from agents
        if self.step_counter % self.action_freq == 0:
            for agent_id, action in actions.items():
                client:GameClient = self.agent_clients[agent_id]
                if self.dry_run:
                    return self.observation_space.sample(), 1, False, None
                if client.player is not None:
                    event = InputEvent(
                        player_id  = client.player.get_id(), 
                        input_data = {
                            'inputs':[keymap[action]],
                            'mouse_pos': "",
                            'mouse_rel': "",
                            'focused': ""
                            })
                    client.player.add_event(event)
                    client.run_step()
            
        gamectx.run_step()

        obs = {}
        dones = {}
        rewards = {}
        infos ={}

        if self.step_counter % self.action_freq ==0:
            for agent_id,client in self.agent_clients.items():
                # ob = client.get_observation(type="sensor")
                ob, reward, done, info = client.content.get_step_info(player= client.player)
                obs[agent_id] = ob
                dones[agent_id] = done
                rewards[agent_id] = reward
                infos[agent_id] = info
        self.step_counter +=1

        return obs,rewards,dones,infos

    def render(self, mode=None):
        if self.dry_run:
            return self.observation_space.sample()

        # TODO: add rendering for observer window
        for agent_id,client in self.agent_clients.items():
            client.render(force=True)
            return client.get_rgb_array()
        # img = gamectx_client.renderer.renderer.render_frame()
        # return img

    def reset(self) -> Dict[str,Any]:
        # self.content.load(gamectx)
        self.obs, _, _, _ = self.step({})
        return self.obs

    def close(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

class SimpleLandEnvSingle(gym.Env):

    def __init__(self,frame_skip=0):
        print("Starting SL v19")
        self.agent_id = "1"
        self.env_main = SimpleLandEnv(
            agent_map={self.agent_id:{}},
            enable_server=False,
            game_tick_rate=2000)
        self.observation_space = self.env_main.observation_space
        self.action_space = self.env_main.action_space
        self.frame_skip = frame_skip


    def reset(self):
        obs = self.env_main.reset()
        return obs.get(self.agent_id)

    def step(self,action):
        total_reward = 0
        ob = None
        done = False
        info = {}
        i = 0
        reward_list = []
        ready = False
        while not ready:
            obs,rewards,dones,infos = self.env_main.step({self.agent_id:action})
            ob, reward, done, info = obs[self.agent_id],rewards[self.agent_id],dones[self.agent_id],infos[self.agent_id]
            # TODO: check for obs mode render use image as obs space

            total_reward +=reward
            reward_list.append(reward)
            if done:
                ready = True # if done found, exit loop
            elif ob is None: # if ob is missing, retry
                print("Missing")
                time.sleep(0.01)
                continue
            elif i >= self.frame_skip: # if frames skipped reached, exit loop
                ready = True
            i +=1
        return ob, max(reward_list), done, info

    def close(self):
        self.env_main.close()

    def render(self,mode=None):
        return self.env_main.render(mode=mode)

if __name__ == "__main__":
    agent_map = {str(i):{} for i in range(10)}
    
    env = SimpleLandEnv(agent_map=agent_map)
    env.reset()
    done_agents = set()
    while(True):
        actions = {agent_id:env.action_space.sample() for agent_id in agent_map.keys()}
        obs, rewards, dones, infos = env.step(actions)





