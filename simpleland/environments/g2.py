import random
from typing import Dict, Any, Tuple

import pymunk

from ..common import (SimClock, Body, Camera, Circle, Clock, Line,
                     Polygon, Shape, Space, Vector,
                     TimeLoggingContainer)
from ..event import (DelayedEvent, Event,
                            PeriodicEvent, SoundEvent, ViewEvent)
from ..game import Game
from ..itemfactory import ItemFactory, ShapeFactory
from ..object import GObject
from ..object_manager import GObjectManager
from ..player import Player
from ..renderer import Renderer
from ..utils import gen_id
from ..content import Content

from ..asset_bundle import AssetBundle
from .helpers import input_event_callback


def load_asset_bundle():
    image_assets={}
    image_assets['1'] = 'assets/redfighter0006.png'
    image_assets['1_thrust'] = 'assets/redfighter0006_thrust.png'

    image_assets['2'] = 'assets/ship2.png'
    image_assets['energy1'] = 'assets/energy1.png'
    image_assets['astroid2'] = 'assets/astroid1.png'
    image_assets['lava1'] = 'assets/lava1.png'
    
    sound_assets={}
    sound_assets['bleep2'] = 'assets/sounds/bleep2.wav'
    return AssetBundle(image_assets = image_assets,sound_assets = sound_assets)


class GameContent(Content):

    def __init__(self, config):
        super(GameContent,self).__init__(config)
        self.config['space_size'] = 30
        self.asset_bundle = load_asset_bundle()

    def get_asset_bundle(self):
        return self.asset_bundle

    def get_step_info(self,player:Player,game:Game) -> Tuple[float,bool]:
        done = player.get_data_value('round_complete', True)

        reward = 0
        if player is not None:
            obj_id = player.get_object_id()
            tt, obj = game.object_manager.get_latest_by_id(obj_id)
            if obj is not None:
                reward = obj.get_data_value("energy")
        return reward, done

    def load(self, game: Game):
        game.remove_all_events()
        game.remove_all_objects()

        # Add Food
        o = GObject(Body(body_type=pymunk.Body.STATIC))
        o.set_position(position=Vector(0,5))
        o.set_data_value("type", "food")
        o.set_data_value("image", "energy1")
        o.set_last_change(game.clock.get_time())
        ShapeFactory.attach_circle(o, 1)
        game.add_object(o)

        # TODO, move to standard event callback
        def collision_callback(arbiter: pymunk.Arbiter, space, data):
            food_objs = []
            player_objs = []
            for s in arbiter.shapes:
                s: Shape = s
                t, o = game.object_manager.get_latest_by_id(s.get_object_id())
                if o is None:
                    return False
                if o.get_data_value("type") == "food":
                    food_objs.append(o)
                elif o.get_data_value("type") == "player":
                    player_objs.append(o)

            if len(food_objs) == 1 and len(player_objs) == 1:
                player_objs[0].set_data_value('energy', 1)

                return False
            else:
                return True
        game.physics_engine.set_collision_callback(collision_callback)

        game.set_input_event_callback(input_event_callback)

        def pre_physics_callback(game: Game):
            new_events = []
            for k, p in game.player_manager.players_map.items():
                # print(p.get_object_id())
                if p.get_object_id() is None:
                    continue
                t, o = game.object_manager.get_latest_by_id(p.get_object_id())
                if o is None or o.is_deleted:
                    continue
                if o.get_data_value("energy") != 0:
                    print("Game Complete")
                    p.set_data_value('round_complete', True)
                    game.remove_object(o)

                    # Delete and create event
                    def new_game_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
                        self.load(game)
                        self.new_player(game, player_id=p.get_id())
                        return []

                    new_game = DelayedEvent(
                        func=new_game_callback,
                        execution_time=game.clock.get_time() + 200)

                    new_events.append(new_game)

            return new_events
        game.set_pre_physics_callback(pre_physics_callback)

    # Make callback
    def new_player(self, game: Game, player_id=None,player_type=None) -> Player:
        # Create Player
        if player_id is None:
            player_id = gen_id()
        player = game.player_manager.get_player(player_id)

        if player is None:
            player = Player(player_id)
            player.player_type = player_type
        print("playerData: {}".format(player.data))

        rounds = player.get_data_value("rounds",0)
        player.set_data_value('rounds', rounds +1)
        player.set_data_value('round_complete', False)

        create_time = game.clock.get_time()
        player_object = GObject(Body(mass=8, moment=30),
                                 camera=Camera(distance=10))
        player_object.set_position(position=Vector(1,1))

        player_object.set_data_value("type", "player")
        player_object.set_data_value("energy", 0)
        player_object.set_data_value("image", "1")
        player_object.set_data_value("player_id", player.get_id())

        ShapeFactory.attach_circle(player_object, 1)

        player.attach_object(player_object)
        game.add_object(player_object)
        game.add_player(player)
        print("PLayer Obj {}".format(player_object.get_id()))

        # Delete and create event
        def round_end_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
            player_object.set_data_value("energy", -1)
            return []

        round_end_event = DelayedEvent(
            func=round_end_callback,
            execution_time=game.clock.get_time() + 2000)

        game.event_manager.add_event(round_end_event)
        return player

    def post_process_frame(self, render_time, game: Game, player: Player, renderer: Renderer):
        if player is not None:
            lines = []
            lines.append("Rounds: {}".format(player.get_data_value("rounds", 0)))

            obj = game.object_manager.get_by_id(player.get_object_id(), render_time)
            if obj is not None:
                lines.append("Current Energy: {}".format(obj.get_data_value("energy", 0)))

            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)

                if obj is None:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)
