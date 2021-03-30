#!/usr/bin/env python3

import random
import numpy as np
import gym
from gym_minigrid.register import env_list
from gym_minigrid.minigrid import Grid, OBJECT_TO_IDX

# Test specifically importing a specific environment
from gym_minigrid.envs import DoorKeyEnv

# Test importing wrappers
from gym_minigrid.wrappers import *
from pyinstrument import Profiler


env = gym.make('MiniGrid-Empty-6x6-v0')


import time
profiler = Profiler()
profiler.start()    
start_time = time.time()
total_steps = 100000
# Test the env.agent_sees() function
env.reset()
for i in range(0, total_steps):
    # env.action_space.sample()
    obs, reward, done, info = env.step(env.action_space.sample())
    if done:
        env.reset()
steps_per_sec = total_steps/(time.time()-start_time)

print(f"steps_per_sec {steps_per_sec}")
profiler.stop()
print(profiler.output_text(unicode=True, color=True,show_all=True))