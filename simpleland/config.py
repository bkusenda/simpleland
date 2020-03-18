
from .common import SLBase

class PhysicsConfig(SLBase):
    def __init__(self):
        self.velocity_multiplier = 15.0
        self.default_max_velocity = 10
        self.default_min_velocity = 0.3
        self.orientation_multiplier = 4
        self.space_damping = .3
        self.steps_per_second = 60
        self.clock_multiplier = 1
        self.tick_rate = 60

class RendererConfig(SLBase):

    def __init__(self):
        self.show_object_shapes = True
        self.render_delay_in_ms = 25
        self.resolution = (640,480)
        self.format='RGB'
        self.save_observation=False
        self.render_shapes = False
        self.show_console = True
        self.disable_textures = False

class ClientConfig(SLBase):
    def __init__(self):
        self.frames_per_second = 60

class ServerConfig(SLBase):
    def __init__(self):
        self.outgoing_chunk_size = 4000
        self.max_unconfirmed_messages_before_new_snapshot = 10

class GameConfig(SLBase):

    def __init__(self):
        self.move_speed = 1
        self.keep_moving = 0
        self.clock_factor = 1.0
        self.tick_rate = 60


class ConfigManager(SLBase):

    def __init__(self):
        """
        TODO: support loading from file
        """
        self.physics_config = PhysicsConfig()
        self.server_config = ServerConfig()
        self.renderer_config = RendererConfig()
        self.client_config = ClientConfig()
        self.game_config = GameConfig()
        self.content_config = {}
