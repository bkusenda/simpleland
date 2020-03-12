
from .common import SLBase

class PhysicsConfig(SLBase):
    def __init__(self):
        self.velocity_multiplier = 12.0
        self.default_max_velocity = 10
        self.default_min_velocity = 0.3
        self.orientation_multiplier = 2
        self.space_damping = 0.4
        self.steps_per_second = 60
        self.clock_multiplier = 1

class GameConfig(SLBase):

    def __init__(self):
        self.move_speed = 1
        self.keep_moving = 0
        self.clock_factor = 1.0