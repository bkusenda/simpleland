import gym
import time
from gym.envs.registration import register
import argparse

parser = argparse.ArgumentParser(description=None)
parser.add_argument('-e', '--env', default='soccer', type=str)

args = parser.parse_args()

def main():

    if args.env == 'soccer':
        register(
            id='multigrid-soccer-v0',
            entry_point='gym_multigrid.envs:SoccerGame4HEnv10x15N2',
        )
        env = gym.make('multigrid-soccer-v0')

    else:
        register(
            id='multigrid-collect-v0',
            entry_point='gym_multigrid.envs:CollectGame4HEnv10x10N2',
        )
        env = gym.make('multigrid-collect-v0')

    _ = env.reset()

    nb_agents = len(env.agents)

    while True:
        ac = [env.action_space.sample() for _ in range(nb_agents)]
        obs, _, done, _ = env.step(ac)

        if done:
            break

from pyinstrument import Profiler
from gym_multigrid.envs.soccer_game import SoccerGameEnv
class SoccerGameSmall(SoccerGameEnv):
    def __init__(self):
        super().__init__(size=None,
        height=10,
        width=15,
        goal_pst = [[1,5], [13,5]],
        goal_index = [1,2],
        num_balls=[1],
        agents_index = [1,2],
        balls_index=[0],
        zero_sum=True)
register(
    id='multigrid-soccer-v0',
    entry_point='gym_multigrid.envs:SoccerGame4HEnv10x15N2',
)
env = SoccerGameSmall()#gym.make('multigrid-soccer-v0')
import time
profiler = Profiler()
profiler.start()    
start_time = time.time()
total_steps = 100000
# Test the env.agent_sees() function
env.reset()
nb_agents = len(env.agents)

for i in range(0, total_steps):
    ac = [env.action_space.sample() for _ in range(nb_agents)]
    obs, _, done, _ = env.step(ac)
    if done:
        env.reset()
        

steps_per_sec = total_steps/(time.time()-start_time)

print(f"steps_per_sec {steps_per_sec}")
profiler.stop()
print(profiler.output_text(unicode=True, color=True,show_all=True))