from .config import ContentConfig, ServerConfig, GameConfig, ClientConfig, PhysicsConfig, RendererConfig

import importlib.util
from .environments import g1, g2
from .content import Content
from typing import Dict, Any
import pprint
class EnvironmentDefinition:

    def __init__(self,
                content_id: str,
                content_config: Dict[str,Any],
                server_config: ServerConfig,
                client_config: ClientConfig,
                renderer_config: RendererConfig,
                physics_config: PhysicsConfig,
                game_config: GameConfig,
                ):

        self.physics_config = physics_config
        self.server_config = server_config
        self.renderer_config = renderer_config
        self.client_config = client_config
        self.game_config = game_config
        self.content_config = content_config
        self.content_id = content_id

    def __repr__(self) -> str:
        return pprint.pformat(self.__dict__)


# Init Registries
content_classes = {}
env_registry = {}


def load_environment(env_id)->EnvironmentDefinition:
    env_def = env_registry.get(env_id)()
    return env_def

def get_env_content(env_def:EnvironmentDefinition) -> Content:
    return content_classes.get(env_def.content_id)(env_def.content_config)
     # spec = importlib.util.spec_from_file_location("Content", "environment/{}.py".format(name))
    # foo = importlib.util.module_from_spec(spec)
    # spec.loader.exec_module(foo)
    # foo.MyClass()

# ****************************************
# REGISTER CONTENT BELOW
# ****************************************


# g1
content_classes['g1'] = g1.GameContent
content_classes['g2'] = g2.GameContent


def build_env_g1():
    env = EnvironmentDefinition(
        server_config=ServerConfig(),
        client_config=ClientConfig(),
        content_id = "g1",
        content_config={},
        renderer_config=RendererConfig(),
        physics_config=PhysicsConfig(),
        game_config=GameConfig())
    return env

def build_env_g2():
    env = EnvironmentDefinition(
        server_config=ServerConfig(),
        client_config=ClientConfig(),
        content_id = "g2",
        content_config={},
        renderer_config=RendererConfig(),
        physics_config=PhysicsConfig(),
        game_config=GameConfig())
    return env

env_registry['g1'] = build_env_g1
env_registry['g2'] = build_env_g2


