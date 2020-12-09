
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
from simpleland.game import Game
from simpleland.client import GameClient
from simpleland.registry import load_game_def, get_game_content
import time
from typing import Dict, Any
# AGENT_KEYMAP = [0,17,5,23,19,1,4]


keymap = [23,1,4]

class SimpleLandEnv:

    def __init__(self, 
            resolution=(30,30), 
            game_id="g1", 
            hostname = 'localhost', 
            port = 10001, 
            dry_run=False,
            agent_map={},
            physics_tick_rate = 60,
            game_tick_rate = 60,
            sim_timestep = 0.01):

        self.game_def = get_game_def(
            game_id=game_id,
            enable_server=True, 
            port=port,
            remote_client=False,
            physics_tick_rate=physics_tick_rate,
            game_tick_rate = game_tick_rate,
            sim_timestep=sim_timestep)

        self.content = get_game_content(self.game_def)

        self.game = Game(
            game_def = self.game_def,
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
                fps=20,
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
                    game=self.game,
                    renderer=renderer,
                    config=player_def.client_config)
            self.game.add_local_client(client)
            self.agent_clients[agent_id]=client

        self.dry_run = dry_run
  
        self.action_space = spaces.Discrete(len(keymap))
        self.observation_space = spaces.Box(0, 255, (resolution[0], resolution[1],3))
        logging.info("Ob space: {}".format(self.observation_space))
        self.action_freq = 10
        self.step_counter = 0
        
        self.ob = None
        self.safe_mode = True
        self.running = True
        self.server=None

        if self.game_def.server_config.enabled:        
            self.server = GameUDPServer(
                conn = (self.game_def.server_config.hostname, self.game_def.server_config.port), 
                handler=UDPHandler,
                game=self.game, 
                config = self.game_def.server_config)

            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            print("Server started at {} port {}".format(self.game_def.server_config.hostname, self.game_def.server_config.port))

    def step(self, actions):

        # get actions from agents
        
        if self.step_counter % self.action_freq == 0:
            for agent_id, action in actions.items():
                client = self.agent_clients[agent_id]
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
            
        self.game.run_step()

        obs = {}
        dones = {}
        rewards = {}
        infos ={}

        if self.step_counter % self.action_freq ==0:
            for agent_id,client in self.agent_clients.items():
                ob = client.renderer.get_observation()
                reward, done = client.content.get_step_info(
                        player= client.player,
                        game=client.game)
                obs[agent_id] = ob
                dones[agent_id] = done
                rewards[agent_id] = reward
                infos[agent_id] = {}
        self.step_counter +=1

        return obs,rewards,dones,infos

    def render(self, mode=None):
        if self.dry_run:
            return self.observation_space.sample()

        # TODO: add rendering for observer window
        for agent_id,client in self.agent_clients.items():
            return client.renderer.frame_cache
        # img = self.game_client.renderer.renderer.render_frame()
        # return img

    def reset(self) -> Dict[str,Any]:
        self.obs, _, _, _ = self.step({})
        return self.ob

    def close(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()


class SimpleLandEnvSingle(gym.Env):

    def __init__(self):
        self.agent_id = "1"
        self.env_main = SimpleLandEnv(agent_map={self.agent_id:{}})

    def reset(self):
        obs = self.env_main.reset()
        return obs.get(self.agent_id)

    def step(self,action):
        obs = self.env_main.step({self.agent_id:action})
        return obs[self.agent_id]

    def close(self):
        self.env_main.close()

if __name__ == "__main__":
    agent_map = {str(i):{} for i in range(10)}
    
    env = SimpleLandEnv(agent_map=agent_map)
    env.reset()
    done_agents = set()
    while(True):
        actions = {agent_id:env.action_space.sample() for agent_id in agent_map.keys()}
        obs, rewards, dones, infos = env.step(actions)
        # print(rewards)
        # all_done = True
        # for agent_id, done in dones.items():
        #     if not done:
        #         all_done=False
        # if all_done is True:
        #     env.reset()





