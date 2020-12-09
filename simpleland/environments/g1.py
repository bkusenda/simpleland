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
        done = False
        reward = 0
        if player is not None:
            obj_id = player.get_object_id()
            tt, obj = game.object_manager.get_latest_by_id(obj_id)
            
            if obj is not None:
                reward = obj.get_data_value("energy")
                if reward <= 0:
                    done = True
                    reward = 0
                else:
                    reward = 1

            else:
                done = True
                    
            if done:
                reward = -100
        return reward, done

    def get_random_pos(self):
        return Vector(
            random.random() * self.config['space_size'] - (self.config['space_size']/2),
            random.random() * self.config['space_size'] - (self.config['space_size']/2))

    def load(self, game: Game):
        print("Starting Game")

        food_energy = 20

        # Create Wall
        wall = ItemFactory.border(Body(body_type=pymunk.Body.STATIC),
                                    Vector(0, 0),
                                    size=self.config['space_size']/2 )
        wall.set_data_value("type", "static")
        game.add_object(wall)

        # Create some Large Recangls
        for i in range(0):
            o = GObject(Body(body_type=pymunk.Body.STATIC))
            o.set_position(position=self.get_random_pos())
            o.set_data_value("energy", 30)
            o.set_data_value("type", "wall")
            o.set_data_value("image", "lava1")
            o.set_last_change(game.clock.get_time())
            o.get_body().angle = random.random() * 360
            ShapeFactory.attach_rectangle(o, 10, 3)
            game.add_object(o)

        # Create some Astroids
        for i in range(5):
            o = GObject(Body(mass=5, moment=1),depth=0)
            o.set_position(position=self.get_random_pos())
            o.set_data_value("energy", 30)
            o.set_data_value("type", "astroid")
            o.set_data_value("image", "astroid2")
            o.set_last_change(game.clock.get_time())
            
            o.get_body().angle = random.random() * 360
            # ShapeFactory.attach_rectangle(o, 2, 2)
            #ShapeFactory.attach_poly(o, size=10,num_sides=40)
            ShapeFactory.attach_circle(o, 2, collision_type=1)

            game.add_object(o)



        # for i in range(4):
        #     o = SLObject(SLBody(body_type=pymunk.Body.STATIC))
        #     o.set_position(position=self.get_random_pos())
        #     o.set_data_value("energy", food_energy)
        #     o.set_data_value("type", "food")
        #     o.set_data_value("image", "energy1")

        #     o.set_last_change(game.clock.get_time())
        #     SLShapeFactory.attach_circle(o, 1)
        #     game.add_object(o)


        def new_food_event_callback(event: PeriodicEvent, data: Dict[str, Any], om: GObjectManager):

            player_locations = []
            for p in game.player_manager.players_map.values():
                t, o = game.object_manager.get_latest_by_id(p.get_object_id())
                if o is not None:
                    player_locations.append(o.get_body().position)


            for i in range(0, 5): #random.randint(0, 3)
                food_counter = self.data.get('food_counter',0)
                if food_counter > 6:
                    continue
                o = GObject(Body(body_type=pymunk.Body.KINEMATIC))
                
                too_close = True
                food_pos = None
                while(too_close):
                    too_close = False
                    food_pos = self.get_random_pos()
                    for l in player_locations:
                        if (food_pos - l).length < 0.3:
                            too_close = True
                            break
                o.set_position(position=food_pos)
                o.set_data_value("energy", food_energy)
                o.set_data_value("type", "food")
                o.set_data_value("image", "energy1")
                o.set_last_change(game.clock.get_time())
                o.get_body().angle = random.random() * 360
                self.data['food_counter'] = food_counter +1

                ShapeFactory.attach_circle(o, 1)
                game.add_object(o)
            return [], False
        new_food_event = PeriodicEvent(new_food_event_callback, execution_interval=1000)
        game.event_manager.add_event(new_food_event)

        # TODO, move to standard event callback
        def collision_callback(arbiter: pymunk.Arbiter, space, data):
            food_objs = []
            player_objs = []
            for s in arbiter.shapes:
                s: Shape = s
                # if s.collision_type == 0:
                #     return False
                t, o = game.object_manager.get_latest_by_id(s.get_object_id())
                if o is None:
                    return False
                if o.get_data_value("type") == "food":
                    food_objs.append(o)
                elif o.get_data_value("type") == "player":
                    player_objs.append(o)

            if len(food_objs) == 1 and len(player_objs) == 1:
                food_energy = food_objs[0].get_data_value('energy')
                player_energy = player_objs[0].get_data_value('energy')
                player_objs[0].set_data_value("energy",
                                              player_energy + food_energy)
                player_objs[0].set_last_change(game.clock.get_time())
                food_counter = self.data.get('food_counter',0)
                self.data['food_counter'] = food_counter -1
                game.remove_object(food_objs[0])
                sound_event = SoundEvent(
                    creation_time=game.clock.get_time(),
                    sound_id="bleep2")
                game.event_manager.add_event(sound_event)

                return False
            else:
                return True
                # self.game.object_manager.remove_by_id(food_objs[0].get_id())
        game.physics_engine.set_collision_callback(collision_callback,1 ,1)


        def collision_callback_0(arbiter: pymunk.Arbiter, space, data):

            return False

        game.physics_engine.set_collision_callback(collision_callback_0,1 ,0)


        def pre_physics_callback(game: Game):
            new_events = []
            players_alive = False
            for k, p in game.player_manager.players_map.items():
                # print(p.get_object_id())
                if p.get_object_id() is None:
                    continue
                t, o = game.object_manager.get_latest_by_id(p.get_object_id())
                if o is None or o.is_deleted:
                    continue
                if o.get_data_value("energy") <= 0:
                    print("Player is dead")
                    lives_used = p.get_data_value("lives_used", 0)
                    p.set_data_value("lives_used", lives_used+1)
                    game.remove_object(o)

                    # Delete and create event
                    def event_callback(event: DelayedEvent, data: Dict[str, Any], om: GObjectManager):
                        self.new_player(game, player_id=data['player_id'])
                        print("New Player Created")
                        return []

                    new_ship_event = DelayedEvent(
                        func=event_callback,
                        execution_time=game.clock.get_time() + 200,
                        data={'player_id': p.get_id()})

                    new_events.append(new_ship_event)
                else:
                    players_alive = True
                    # Response
            #Reset if no more players
            # if not players_alive:
            #     for o in game.object_manager.get_objects_latest().values():
            #         if o.get_data_value("type") == 'food':


            return new_events
        game.set_pre_physics_callback(pre_physics_callback)
        game.set_input_event_callback(input_event_callback)

        print("Loading Game Complete")

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

        create_time = game.clock.get_time()
        player_object = GObject(Body(mass=8, moment=30),
                                 camera=Camera(distance=10))
        player_object.set_position(position=self.get_random_pos())

        player_object.set_data_value("type", "player")
        player_object.set_data_value("energy", 100)
        player_object.set_data_value("image", "1")
        player_object.set_data_value("player_id", player.get_id())

        # SLShapeFactory.attach_rectangle(player_object, 2,2)
        ShapeFactory.attach_circle(player_object, radius=1)

        player.attach_object(player_object)
        game.add_object(player_object)
        game.add_player(player)
        print("PLayer Obj {}".format(player_object.get_id()))

        def event_callback(event: PeriodicEvent, data: Dict[str, Any], om: GObjectManager):
            t, obj = om.get_latest_by_id(data['obj_id'])
            if obj is None or obj.is_deleted:
                return [], True
            new_energy = max(obj.get_data_value("energy") - 1, 0)
            #     # om.remove_by_id(obj.get_id())
            #     return [], False
            print("Energy: {}".format(new_energy))
            obj.set_data_value('energy', new_energy)
            obj.set_last_change(game.clock.get_time())
            return [], False

        decay_event = PeriodicEvent(
            event_callback,
            execution_interval=2000,
            data={'obj_id': player_object.get_id()})

        game.event_manager.add_event(decay_event)
        return player

    def post_process_frame(self, render_time, game: Game, player: Player, renderer: Renderer):
        if player is not None:
            lines = []
            lines.append("Lives Used: {}".format(player.get_data_value("lives_used", 0)))

            obj = game.object_manager.get_by_id(player.get_object_id(), render_time)
            if obj is not None:
                lines.append("Current Energy: {}".format(obj.get_data_value("energy", 0)))

            if renderer.config.show_console:
                renderer.render_to_console(lines, x=5, y=5)

                if obj is None:
                    renderer.render_to_console(['You Died'], x=50, y=50, fsize=50)
