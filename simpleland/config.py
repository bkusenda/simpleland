from .common import Base
import pprint
from typing import Dict, Any



class PhysicsConfig(Base):
    def __init__(self):
        self.velocity_multiplier = 200.0
        self.default_max_velocity = 500
        self.default_min_velocity = 10
        self.orientation_multiplier = 4
        self.space_dampening = .5
        self.steps_per_second = 60
        self.clock_multiplier = 1
        self.tick_rate = 60
        self.sim_timestep=0.02
        self.player_angular_vel_max = 3

class RendererConfig(Base):

    def __init__(self):
        self.render_delay_in_ms = 0
        self.resolution = (640,480)
        self.format='RGB'
        self.save_observation=True
        self.render_shapes = False
        self.show_console = True
        self.disable_textures = False
        self.sdl_audio_driver = None # 'dsp'
        self.sdl_video_driver = None #'dummy'
        self.sound_enabled = True
        self.render_to_screen = True 
        self.draw_grid = False
        self.grid_size = 20
        self.view_type = 0
        self.debug_render_bodies = False

def __repr__(self) -> str:
    return pprint.pformat(self.__dict__)

class ClientConfig(Base):
    def __init__(self):
        self.enabled=True
        self.is_remote = True
        self.frames_per_second = 60
        self.is_human = True
        self.player_type = 0
        self.client_id = None
        self.server_hostname = None
        self.server_port = None
        

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)

class ServerConfig(Base):
    def __init__(self):
        self.enabled=False
        self.outgoing_chunk_size = 4000
        self.max_unconfirmed_messages_before_new_snapshot = 10
        self.hostname="localhost"
        self.port = 10001

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)

class GameConfig(Base):

    def __init__(self):
        self.move_speed = 1
        self.keep_moving = 0
        self.tick_rate = 60
        self.client_only_mode=False

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)
        
class ContentConfig(Base):

    def __init__(self, id, data):
        self.id = id
        self.data = data

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)


class PlayerDefinition:

    def __init__(self):
        self.client_config = ClientConfig()
        self.renderer_config = RendererConfig()

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)

class GameDef:

    def __init__(self,
                content_id: str,
                content_config: Dict[str,Any]
                ):

        self.physics_config = PhysicsConfig()
        self.server_config = ServerConfig()
        self.game_config = GameConfig()
        self.content_config = content_config
        self.content_id = content_id
        

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)