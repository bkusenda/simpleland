from .common import Base

class PhysicsConfig(Base):
    def __init__(self):
        self.velocity_multiplier = 15.0
        self.default_max_velocity = 10
        self.default_min_velocity = 0.3
        self.orientation_multiplier = 4
        self.space_damping = .3
        self.steps_per_second = 60
        self.clock_multiplier = 1
        self.tick_rate = 60

class RendererConfig(Base):

    def __init__(self):
        self.show_object_shapes = True
        self.render_delay_in_ms = 25
        self.resolution = (640,480)
        self.format='RGB'
        self.save_observation=True
        self.render_shapes = False
        self.show_console = True
        self.disable_textures = False
        self.sdl_audio_driver = None #'dsp'
        self.sdl_video_driver = None #'dummy'
        self.sound_enabled = True
        self.render_to_screen = True


class ClientConfig(Base):
    def __init__(self):
        self.frames_per_second = 60
        self.is_human = True
        self.observer_only = False
        self.client_id = None
        self.server_hostname = None
        self.server_port = None

class ServerConfig(Base):
    def __init__(self):
        self.outgoing_chunk_size = 4000
        self.max_unconfirmed_messages_before_new_snapshot = 10

class GameConfig(Base):

    def __init__(self):
        self.move_speed = 1
        self.keep_moving = 0
        self.clock_factor = 1.0
        self.tick_rate = 60

class ContentConfig(Base):

    def __init__(self, id, data):
        self.id = id
        self.data = data