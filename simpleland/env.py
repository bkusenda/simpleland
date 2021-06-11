
import logging
from simpleland.registry import load_game_content, GameDef
import gym
from gym import spaces
import logging
from simpleland.runner import get_game_def, get_player_def, UDPHandler, GameUDPServer
from simpleland.event import InputEvent
import threading

from simpleland.player import  Player
from simpleland.renderer import Renderer
from simpleland.utils import gen_id
from simpleland import gamectx
from simpleland.client import GameClient
from simpleland.registry import load_game_def, load_game_content
import time
from typing import Dict, Any
# AGENT_KEYMAP = [0,17,5,23,19,1,4]
import numpy as np
from simpleland.utils import merged_dict
from pyinstrument import Profiler
from simpleland.clock import clock

# keymap = [23,1,4]

class SimplelandEnv:

    def __init__(self, 
            resolution=(1280,720), 
            game_id="survival_grid", 
            hostname = 'localhost', 
            port = 10001, 
            dry_run=False,
            agent_map={'1':{},'2':{}},
            tick_rate = 0,
            enable_server = False,
            view_type=0,
            render_shapes=False,
            player_type = 1,
            content_config = {}):
        
        game_def = get_game_def(
            game_id=game_id,
            enable_server=enable_server, 
            port=port,
            remote_client=False,
            tick_rate = tick_rate)

        game_def.content_config = merged_dict(
            game_def.content_config,
            content_config)
        self.content = load_game_content(game_def)

        gamectx.initialize(
            game_def = game_def,
            content=self.content)

        # Build Clients
        self.agent_map = agent_map
        self.agent_clients = {}

        # PISTARLAB REQUIREMENTS
        self.players= list(self.agent_map.keys())
        self.num_players = len(self.players)
        self.possible_players = self.players
        self.max_num_players = self.num_players

        player_def = None
        for agent_id, agent_info in agent_map.items():
            player_def = get_player_def(
                enable_client=True,
                client_id = agent_id,
                remote_client=False,
                hostname=hostname,
                port = port,
                resolution = resolution,
                fps=tick_rate,
                render_shapes=render_shapes,
                player_type=player_type,
                is_human=False,
                view_type=view_type)

            # Render config changes
            player_def.renderer_config.sdl_audio_driver = 'dsp'
            # player_def.renderer_config.render_to_screen = False
            # player_def.renderer_config.sdl_video_driver = 'dummy'
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
  
        # TODO: make different for each client
        self.action_spaces = {agent_id:self.content.get_action_space() for agent_id in self.agent_clients.keys()}
        self.observation_spaces = {agent_id:self.content.get_observation_space() for agent_id in self.agent_clients.keys()}
        
        logging.info("Ob spaces: {}".format(self.observation_spaces))
        self.step_counter = 0
        
        self.ob = None
        self.safe_mode = True
        self.running = True
        self.server=None
        self.first_start = True


        if game_def.server_config.enabled:        
            self.server = GameUDPServer(
                conn = (game_def.server_config.hostname, game_def.server_config.port), 
                handler=UDPHandler,
                config = game_def.server_config)

            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            logging.info("Server started at {} port {}".format(game_def.server_config.hostname, game_def.server_config.port))

    def step(self, actions):

        # get actions from agents
        for agent_id, action in actions.items():
            client:GameClient = self.agent_clients[agent_id]
            if self.dry_run:
                return self.observation_spaces[agent_id], 1, False, None
            if client.player is not None:
                event = InputEvent(
                    player_id  = client.player.get_id(), 
                    input_data = {
                        'pressed':[self.content.keymap[action]],
                        'keydown':[self.content.keymap[action]],
                        'keyup':[self.content.keymap[action]],
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
  
        for agent_id,client in self.agent_clients.items():
            ob, reward, done, info = self.content.get_step_info(player= client.player)
            if ob is None:
                continue
            obs[agent_id] = ob
            dones[agent_id] = done
            rewards[agent_id] = reward
            infos[agent_id] = info

        dones['__all__']= self.content.reset_required()
    
        self.step_counter +=1

        return obs,rewards,dones,infos

    def stats(self,player_id=None) :
        return {'step_counter':self.step_counter}

    def runtime_config(self) :
        return {'hi':self.step_counter}

    def runtime_config_update(self):
        return True, "msg"

    def render(self, mode=None, player_id=None):
        # TODO: add rendering for observer window
        if player_id is None:
            for agent_id,client in self.agent_clients.items():
                if self.dry_run:
                    return self.observation_spaces[agent_id].sample()
                client.render(force=True)
                return client.get_rgb_array()
        else:
            client = self.agent_clients[player_id]
            if self.dry_run:
                return self.observation_spaces[player_id].sample()
            client.render(force=True)
            return client.get_rgb_array()

    def reset(self) -> Dict[str,Any]:
        self.content.reset()
        self.obs, _, _, _ = self.step({})
        return self.obs

    def close(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

class SimplelandEnvSingle(gym.Env):

    def __init__(self,
            content_config={},
            render_shapes=True,
            player_type=1,
            view_type=1,
            tick_rate=10000):
        logging.info("Starting SL v21")
        self.agent_id = "1"
        self.env_main = SimplelandEnv(
            agent_map={self.agent_id:{}},
            enable_server=False,
            tick_rate=tick_rate,
            content_config=content_config,
            view_type=view_type,
            player_type=player_type,
            render_shapes=render_shapes)
        self.observation_space = self.env_main.observation_spaces[self.agent_id]
        self.action_space = self.env_main.action_spaces[self.agent_id]

    def reset(self):
        obs = self.env_main.reset()
        return obs.get(self.agent_id)

    def step(self,action):
        obs,rewards,dones,infos = self.env_main.step({self.agent_id:action})
        ob, reward, done, info = obs[self.agent_id],rewards[self.agent_id],dones[self.agent_id],infos[self.agent_id]            
        return ob, reward, done, info

    def close(self):
        self.env_main.close()

    def render(self,mode=None):
        return self.env_main.render(mode=mode)

import time
import argparse
if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--render", action="store_true", help="Render")
    parser.add_argument("--mem_profile", action="store_true")
    parser.add_argument("--time_profile", action="store_true")
    parser.add_argument("--agent_count", default=1, type=int, help="Number test of agents")

    args =  parser.parse_args()

    agent_map = {str(i):{} for i in range(args.agent_count)}
    debug = False
    time_profile = args.time_profile
    mem_profile = args.mem_profile
    render = args.render
    if mem_profile:
        import tracemalloc
        tracemalloc.start()
    env = SimplelandEnv(agent_map=agent_map,dry_run=False)
    done_agents = set()
    start_time = time.time()
    max_steps = 20000
    profiler = None
    if time_profile:
        profiler = Profiler()
        profiler.start()
    dones = {"__all__":True}
    episode_count = 0
    actions = {}

    for i in range(0,max_steps):
        if dones.get('__all__'):
            obs = env.reset()
            rewards, dones, infos = {}, {'__all__':False},{}
            episode_count+=1
        else:
            obs, rewards, dones, infos = env.step(actions)
        
        if debug:
            actions={}
            for id, ob in obs.items():
                if render:
                    env.render(player_id=id)  
                logging.info(f"Player: {id}")
                logging.info(obs[id])
                if len(rewards)> 0:
                    logging.info(rewards[id])
                    logging.info(dones[id])
                    logging.info(infos[id])
                logging.info(f"Episode {episode_count} Game Step:{clock.get_time()}")
                logging.info("----------")
                action = env.action_spaces[id].sample() #input()
                logging.info(action)
                # time.sleep(.1)
                try:
                    action = int(action)
                except:
                    action = None
                actions[id]=action
        else:
            if render:
                env.render()  
            actions = {agent_id:env.action_spaces[agent_id].sample() for agent_id in env.obs.keys()}
        if mem_profile and (env.step_counter % 10000 == 0):
            current, peak = tracemalloc.get_traced_memory()
            logging.info(f"Current memory usage is {current / 10**6}MB; Peak was {peak / 10**6}MB")

    if mem_profile:
        current, peak = tracemalloc.get_traced_memory()
        logging.info(f"Current memory usage is {current / 10**6}MB; Peak was {peak / 10**6}MB")
        tracemalloc.stop()    
    steps_per_sec = max_steps/(time.time()-start_time)
    logging.info(f"steps_per_sec {steps_per_sec}")
    if time_profile:
        profiler.stop()
        logging.info(profiler.output_text(unicode=True, color=True,show_all=True))





