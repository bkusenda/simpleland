import gym
import numpy as np
import math
import pybullet as p
# from simple_driving.resources.car import Car
# from simple_driving.resources.plane import Plane
# from simple_driving.resources.goal import Goal
import matplotlib.pyplot as plt

import pybullet as p
import os
import math
import pybullet as p
import os
from pyinstrument import Profiler

import time

cur_path = os.path.dirname(__file__)

print(__file__)
class Goal:
    def __init__(self, client, base):
        f_name = os.path.join(cur_path, 'assets/goal.urdf')
        p.loadURDF(fileName=f_name,
                   basePosition=[base[0], base[1], 0],
                   physicsClientId=client)

class Car:
    def __init__(self, client):
        self.client = client
        f_name = os.path.join(cur_path, 'assets/car.urdf')
        self.car = p.loadURDF(fileName=f_name,
                              basePosition=[0, 0, 0.1],
                              physicsClientId=client)

        # Joint indices as found by p.getJointInfo()
        self.steering_joints = [0, 2]
        self.drive_joints = [1, 3, 4, 5]
        # Joint speed
        self.joint_speed = 0
        # Drag constants
        self.c_rolling = 0.2
        self.c_drag = 0.01
        # Throttle constant increases "speed" of the car
        self.c_throttle = 20

    def get_ids(self):
        return self.car, self.client

    def apply_action(self, action):
        # Expects action to be two dimensional
        throttle, steering_angle = action

        # Clip throttle and steering angle to reasonable values
        throttle = min(max(throttle, 0), 1)
        steering_angle = max(min(steering_angle, 0.6), -0.6)

        # Set the steering joint positions
        p.setJointMotorControlArray(self.car, self.steering_joints,
                                    controlMode=p.POSITION_CONTROL,
                                    targetPositions=[steering_angle] * 2,
                                    physicsClientId=self.client)

        # Calculate drag / mechanical resistance ourselves
        # Using velocity control, as torque control requires precise models
        friction = -self.joint_speed * (self.joint_speed * self.c_drag +
                                        self.c_rolling)
        acceleration = self.c_throttle * throttle + friction
        # Each time step is 1/240 of a second
        self.joint_speed = self.joint_speed + 1/30 * acceleration
        if self.joint_speed < 0:
            self.joint_speed = 0

        # Set the velocity of the wheel joints directly
        p.setJointMotorControlArray(
            bodyUniqueId=self.car,
            jointIndices=self.drive_joints,
            controlMode=p.VELOCITY_CONTROL,
            targetVelocities=[self.joint_speed] * 4,
            forces=[1.2] * 4,
            physicsClientId=self.client)

    def get_observation(self):
        # Get the position and orientation of the car in the simulation
        pos, ang = p.getBasePositionAndOrientation(self.car, self.client)
        ang = p.getEulerFromQuaternion(ang)
        ori = (math.cos(ang[2]), math.sin(ang[2]))
        pos = pos[:2]
        # Get the velocity of the car
        vel = p.getBaseVelocity(self.car, self.client)[0][0:2]

        # Concatenate position, orientation, velocity
        observation = (pos + ori + vel)
        return observation
    

import pybullet as p
import os


class Plane:
    def __init__(self, client):
        f_name = os.path.join(cur_path, 'assets','plane.urdf')
        p.loadURDF(fileName=f_name,
                   basePosition=[0, 0, 0],
                   physicsClientId=client)
    
class SimpleDrivingEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self):
        self.action_space = gym.spaces.box.Box(
            low=np.array([0, -.6], dtype=np.float32),
            high=np.array([1, .6], dtype=np.float32))
        self.observation_space = gym.spaces.box.Box(
            low=np.array([-10, -10, -1, -1, -5, -5, -10, -10], dtype=np.float32),
            high=np.array([10, 10, 1, 1, 5, 5, 10, 10], dtype=np.float32))
        self.np_random, _ = gym.utils.seeding.np_random()

        self.client = p.connect(p.DIRECT)
        # Reduce length of episodes for RL algorithms
        p.setTimeStep(1/30, self.client)

        self.car = None
        self.goal = None
        self.done = False
        self.prev_dist_to_goal = None
        self.rendered_img = None
        self.render_rot_matrix = None
        self.reset()

    def step(self, action):
        # Feed action to the car and get observation of car's state
        self.car.apply_action(action)
        p.stepSimulation()
        car_ob = self.car.get_observation()

        # Compute reward as L2 change in distance to goal
        dist_to_goal = math.sqrt(((car_ob[0] - self.goal[0]) ** 2 +
                                  (car_ob[1] - self.goal[1]) ** 2))
        reward = max(self.prev_dist_to_goal - dist_to_goal, 0)
        self.prev_dist_to_goal = dist_to_goal

        # Done by running off boundaries
        if (car_ob[0] >= 10 or car_ob[0] <= -10 or
                car_ob[1] >= 10 or car_ob[1] <= -10):
            self.done = True
        # Done by reaching goal
        elif dist_to_goal < 1:
            self.done = True
            reward = 50

        ob = np.array(car_ob + self.goal, dtype=np.float32)
        return ob, reward, self.done, dict()

    def seed(self, seed=None):
        self.np_random, seed = gym.utils.seeding.np_random(seed)
        return [seed]

    def reset(self):
        p.resetSimulation(self.client)
        p.setGravity(0, 0, -10)
        # Reload the plane and car
        Plane(self.client)
        self.car = Car(self.client)

        # Set the goal to a random target
        x = (self.np_random.uniform(5, 9) if self.np_random.randint(2) else
             self.np_random.uniform(-5, -9))
        y = (self.np_random.uniform(5, 9) if self.np_random.randint(2) else
             self.np_random.uniform(-5, -9))
        self.goal = (x, y)
        self.done = False

        # Visual element of the goal
        Goal(self.client, self.goal)

        # Get observation to return
        car_ob = self.car.get_observation()

        self.prev_dist_to_goal = math.sqrt(((car_ob[0] - self.goal[0]) ** 2 +
                                           (car_ob[1] - self.goal[1]) ** 2))
        return np.array(car_ob + self.goal, dtype=np.float32)

    def render(self, mode='human'):
        if self.rendered_img is None:
            self.rendered_img = plt.imshow(np.zeros((100, 100, 4)))

        # Base information
        car_id, client_id = self.car.get_ids()
        proj_matrix = p.computeProjectionMatrixFOV(fov=80, aspect=1,
                                                   nearVal=0.01, farVal=100)
        pos, ori = [list(l) for l in
                    p.getBasePositionAndOrientation(car_id, client_id)]
        pos[2] = 0.2

        # Rotate camera direction
        rot_mat = np.array(p.getMatrixFromQuaternion(ori)).reshape(3, 3)
        camera_vec = np.matmul(rot_mat, [1, 0, 0])
        up_vec = np.matmul(rot_mat, np.array([0, 0, 1]))
        view_matrix = p.computeViewMatrix(pos, pos + camera_vec, up_vec)

        # Display image
        frame = p.getCameraImage(100, 100, view_matrix, proj_matrix)[2]
        frame = np.reshape(frame, (100, 100, 4))
        self.rendered_img.set_data(frame)
        plt.draw()
        plt.pause(.00001)

    def close(self):
        p.disconnect(self.client)


if __name__ == "__main__":
    agent_map = {str(i):{} for i in range(1)}
    
    env = SimpleDrivingEnv()
    profiler = Profiler()
    profiler.start()    
    start_time = time.time()
    total_steps = 100000
    env.reset()
    for i in range(0,total_steps):
        ob,reward,done,info = env.step(env.action_space.sample())
        if done:
            env.reset()
    steps_per_sec = total_steps/(time.time()-start_time)
    print(f"steps_per_sec {steps_per_sec}")
    profiler.stop()
    print(profiler.output_text(unicode=True, color=True))