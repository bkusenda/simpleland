# import numpy as np
# from gym import spaces
# from gym import Env
# from typing import Tuple
# from simpleland.core import SLUniverse, SLVector, SLShapeFactory, SLItemFactory, SLBody, \
#     FollowBehaviour, SLEntity, SLViewer, SLPlayer
# from simpleland.game import SLGame
# from simpleland.physics import SLPymunkPhysicsEngine
# from simpleland.player import SLAgentPlayer
# from simpleland.renderer import SLPyGameRenderer
# import logging

# def join_game(resolution) -> Tuple[SLGame, SLPlayer]:
#     player = SLAgentPlayer(
#         renderer=SLPyGameRenderer(resolution=resolution))

#     physics_engine = SLPymunkPhysicsEngine()

#     player_object = SLEntity(SLBody(mass=8, moment=30), viewer=SLViewer(distance=12))
#     player_object.set_position(SLVector(10, 10))

#     SLShapeFactory.attach_psquare(player_object, 1)

#     box = SLItemFactory.box(
#         body=SLBody(mass=11, moment=1),
#         position=SLVector(2, 2),
#         size=1)

#     # triangle = SLItemFactory.triangle(
#     #     body=SLBody(mass=11, moment=1),
#     #     position=SLVector(4, 4),
#     #     size=1)

#     hostile_object = SLEntity(SLBody(mass=50, moment=1))
#     hostile_object.set_position(position=SLVector(6, 6))
#     hostile_object.attach_behavior(FollowBehaviour(player_object))
#     SLShapeFactory.attach_circle(hostile_object, 1)

#     items = []

#     # for i in range(0, 10):
#     #     pos = SLVector(random.randint(0, 10), random.randint(0, 10))
#     #     item = SLItemFactory.box(body=SLBody(mass=11, moment=1),
#     #                              position=pos,
#     #                              size=1)
#     #
#     #     items.append(item)

#     wall = SLItemFactory.border(physics_engine.space.static_body,
#                                 SLVector(0, 0),
#                                 size=20)

#     universe = SLUniverse(physics_engine)

#     game = SLGame(universe=universe)

#     universe.attach_objects([player_object])
#     universe.attach_objects([box])
#     # universe.attach_objects([triangle])
#     universe.attach_objects([hostile_object])
#     # universe.attach_objects(items)

#     universe.attach_static_objects([wall])

#     player.attach_object(player_object)

#     # ADD logic
#     # TODO Move some where that makes sense, rules?

#     game.universe.physics_engine.add_player_collision_event(player, hostile_object)

#     game.add_player(player)

#     return game, player


# class SimpleLandEnv(Env):

#     def __init__(self, resolution=(100, 100)):
#         import os
#         os.environ["SDL_VIDEODRIVER"] = "dummy"
#         os.environ['SDL_AUDIODRIVER'] = 'dsp'
#         self.resolution = resolution
#         self.game, self.player = join_game(self.resolution)
#         self.action_space = spaces.Discrete(7)
#         self.observation_space = spaces.Box(0, 255, (self.resolution[0], self.resolution[1],3))
#         # if resolution is None:
#         #     self.observation_space = spaces.Box(
#         #         np.array([-np.finfo(np.float32).max, np.finfo(np.float32).max]),
#         #         np.array([-np.finfo(np.float32).max, np.finfo(np.float32).max]), dtype=np.float32)
#         logging.info("TestGameEnv ob space: {}".format(self.observation_space))
        
#         self.ob = None
#         self.safe_mode = True

#     def step(self, action):
#         obs, step_reward, done = self.game.manual_player_action_step({int(action)}, self.player.uid)
#         #self.ob = self.game.universe.get_direction()
#         self.ob = obs
#         if self.player.health <= -1:
#             step_reward = -100
#             done = True
#         else:
#             step_reward = 1

#         return self.ob, step_reward, done, None

#     def render(self, human=True, mode=None):
#         img = self.player.renderer.render_frame()
#         return img

#     def reset(self):
#         self.game.quit()
#         self.game, self.player = join_game(self.resolution)
#         return self.step(0)[0]

#     def quit(self):
#         self.game.quit()


# # import matplotlib.pyplot as plt

# def main():
#     env = SimpleLandEnv(resolution=(30, 30))
#     observation = env.reset()
#     total_reward = 0
#     for t in range(3000):
#         env.render()
#         action = env.action_space.sample()
#         observation, reward, done, info = env.step(action)
#         total_reward += reward
#         if t % 100 == 0:
#             print(reward)
#         if done:
#             print("Episode finished after {} timesteps".format(t + 1))
#             break
#     env.quit()


# if __name__ == "__main__":
#     main()
