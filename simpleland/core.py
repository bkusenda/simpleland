import json
from simpleland.physics_engine import PymunkPhysicsEngine
from typing import List, Set
from uuid import UUID


from .common import (Body, Circle, Clock, Line
                     , Polygon, Space, StepClock, Vector, SimClock)
from .object import (GObject, ExtendedGObject)

# from .renderer import SLRenderer
from .utils import gen_id
from .config import GameDef, GameConfig, PhysicsConfig
import math
LATENCY_LOG_SIZE = 100

class ClientInfo:
    """
    Stores Client session info 
    """

    def __init__(self, client_id):
        self.id = client_id
        self.last_snapshot_time_ms = 0
        self.latency_history = [None for i in range(LATENCY_LOG_SIZE)]
        self.player_id = None
        self.conn_info = None
        self.request_counter = 0
        self.unconfirmed_messages = set()

    def add_latency(self, latency: float):
        self.latency_history[self.request_counter % LATENCY_LOG_SIZE] = latency
        self.request_counter += 1

    def avg(self):
        vals = [i for i in self.latency_history if i is not None]
        return math.fsum(vals)/len(vals)

    def get_id(self):
        return self.id

    def __repr__(self):
        return "Client: id: {}, player_id: {}".format(self.id,self.player_id)



class GameContext:
    """
    
    """

    def __init__(self):

        self.game_def:GameDef = None
        self.config:GameConfig = None
        self.physics_config:PhysicsConfig = None
        self.clock = None

        self.object_manager = None
        self.physics_engine = None
        self.player_manager = None
        self.event_manager = None
        self.state = None
        self.step_counter = 0
        self.last_position_lookup = {}

        self.tick_rate = None
        self.id = gen_id()
        self.pre_event_callback = lambda : []
        self.pre_physics_callback = lambda : []
        self.input_event_callback = lambda event: []
        self.post_physics_callback  = lambda : []
        self.clients = {}
        self.local_clients = []
        self.data = {}

    def reset_data(self):
        self.data = {}

    def initialize(self, 
            game_def:GameDef = None,
            content = None):
        self.game_def = game_def

        self.config = game_def.game_config
        self.physics_config = game_def.physics_config

        from .event_manager import EventManager
        from .object_manager import GObjectManager
        from .player_manager import PlayerManager
        from .physics_engine import GridPhysicsEngine, PymunkPhysicsEngine

        self.object_manager = GObjectManager(200)
        print(self.physics_config.engine)
        if self.physics_config.engine == 'pymunk':
            self.clock = SimClock()
            self.physics_engine = PymunkPhysicsEngine(self.clock, self.physics_config)
        else:
            self.clock = StepClock()
            self.physics_engine = GridPhysicsEngine(self.clock, self.physics_config)
        
        self.player_manager = PlayerManager()
        self.event_manager = EventManager()
        self.state = "RUNNING"
        self.tick_rate = self.config.tick_rate
        self.step_counter = 0
        self.last_position_lookup = {}

        self.content = content
        if not self.config.client_only_mode:
            print("Loading Game Content.")
            content.load()

    def get_content(self):
        return self.content

    def get_time_scale(self):
        return 60.0/self.config.tick_rate

    def add_local_client(self,client):
        self.local_clients.append(client)
        
    def get_client(self, client_id) -> ClientInfo:
        client = self.clients.get(client_id, None)
        if client is None:
            client = ClientInfo(client_id)
            self.clients[client.id] = client
        return client

    def get_player(self, client, player_type):
        """
        Get existing player or create new one
        """
        if client.player_id is None:
            player = self.content.new_player(player_id=None, player_type=player_type)
            client.player_id = player.get_id()
        else:
            player = self.player_manager.get_player(client.player_id)
        return player

    def change_game_state(self, new_state):
        gamectx_state = new_state

    def set_input_event_callback(self, callback):
        self.input_event_callback = callback

    def set_pre_event_callback(self, callback):
        self.pre_event_callback = callback

    def set_pre_physics_callback(self, callback):
        self.pre_physics_callback = callback

    def set_post_physics_callback(self, callback):
        self.post_physics_callback = callback

    def create_snapshot(self,last_update_timestamp):
        snapshot_timestamp = self.clock.get_time()
        om_snapshot = self.object_manager.get_snapshot_update(last_update_timestamp)
        pm_snapshot = self.player_manager.get_snapshot() # TODO, updates since
        em_snapshot = self.event_manager.get_snapshot_for_client(last_update_timestamp)
        return snapshot_timestamp, {
            'om':om_snapshot,
            'pm':pm_snapshot,
            'em': em_snapshot,
            'timestamp':snapshot_timestamp,
            }
    
    def load_snapshot(self,snapshot):
        snapshot_timestamp = snapshot['timestamp']
        if 'om' in snapshot:
            self.object_manager.load_snapshot_from_data(
                snapshot_timestamp,
                snapshot['om'])
        if 'pm' in snapshot:
            self.player_manager.load_snapshot(snapshot['pm'])
        if 'em' in snapshot:
            self.event_manager.load_snapshot(snapshot['em'])

    def run_pre_event_processing(self):
        """
        TODO: redo callbacks, use function overrides instead
        """
        if self.pre_event_callback is not None:
            events = self.pre_event_callback()
            self.event_manager.add_events(events)

    def run_event_processing(self):
        from .event import (Event, AdminEvent, MechanicalEvent,
                            PeriodicEvent, ViewEvent, SoundEvent, DelayedEvent, InputEvent,PositioningUpdateEvent)
        new_events = []
        events_to_remove = []
        events_to_process = list(self.event_manager.get_events())
        for e in events_to_process:
            result_events = []
            if type(e) == AdminEvent:
                e: AdminEvent = e
                if e.value == 'QUIT':
                    self.change_game_state("QUITING")
                    events_to_remove.append(e)
            elif type(e) == InputEvent:
                result_events = self.input_event_callback(e)
                events_to_remove.append(e)
            elif type(e) == ViewEvent:
                result_events = self._process_view_event(e)
                events_to_remove.append(e)

            elif type(e) == DelayedEvent:
                e: DelayedEvent = e
                result_events, delete_event = e.run(self.object_manager)
                if delete_event:
                    events_to_remove.append(e)
            elif type(e) == PeriodicEvent:
                e: PeriodicEvent = e
                result_events, remove_event = e.run(self.object_manager)
                # NOT REMOVED
                if remove_event:
                    events_to_remove.append(e)

            new_events.extend(result_events)

        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())

        self.event_manager.add_events(new_events)

    def run_pre_physics_processing(self):
        if self.pre_physics_callback is not None:
            events = self.pre_physics_callback()
            self.event_manager.add_events(events)

    def run_post_physics_processing(self):
        if self.post_physics_callback is not None:
            events = self.post_physics_callback()
            self.event_manager.add_events(events)

    def run_physics_processing(self): 
        self.physics_engine.update()
        if self.config.track_updates:
            # TODO: Not efficient
            # Check for changes in position or angle and log change time
            new_position_lookup = {}
            for k,o in self.object_manager.get_objects_latest().items():
                body = o.get_body()
                angle = body.angle
                position = body.position
                current_position = {'angle':angle,'position':position}

                last_position = self.last_position_lookup.get(k,None)
                if last_position is not None:
                    if ((last_position['angle'] != current_position['angle'] ) or
                    (last_position['position'] != current_position['position'])):
                        o.set_last_change(self.clock.get_time())
                new_position_lookup[k] = current_position
            self.last_position_lookup = new_position_lookup
    
    def tick(self):
        self.clock.tick(self.tick_rate)     

    def add_player(self, player):
        self.player_manager.add_player(player) 

    def add_object(self,obj):
        obj.set_last_change(self.clock.get_time())
        self.object_manager.add(self.clock.get_time(), obj)
        self.physics_engine.add_object(obj)

    def remove_object(self,obj:GObject):
        # Marks as deleted, but not removed completely
        obj.delete()
        obj.set_last_change(self.clock.get_time())
        self.physics_engine.remove_object(obj)
        self.object_manager.remove_by_id(obj.get_id())
        for p in self.player_manager.players_map.values():
            if obj.get_id() == p.get_object_id():
                p.control_obj_id = None
    
    def remove_all_objects(self):
        for o in list(self.object_manager.get_objects_latest().values()):
            if not o.is_deleted:
                self.remove_object(o)

    def remove_all_events(self):
        self.event_manager.clear()
    
    def cleanup(self):
        for o in list(self.object_manager.get_objects_latest().values()):
            if o.is_deleted and o.get_last_change() < (self.clock.get_time() - 10000):
                self.object_manager.remove_by_id(o.get_id())

    def get_sound_events(self,render_time):
        from .event import (Event, AdminEvent, MechanicalEvent,
                            PeriodicEvent, ViewEvent, SoundEvent, DelayedEvent, InputEvent)
        events_to_remove = []
        sound_ids = []
        for e in self.event_manager.get_events():
            if e.is_client_event and not e.is_realtime_event:
                result_events = []
                if type(e) == SoundEvent:
                    e:SoundEvent = e
                    sound_ids.append(e.sound_id)
                    events_to_remove.append(e)
        
        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())
        return sound_ids
    

    def _process_view_event(self, e):
        # TODO: use callback instead
        player = self.player_manager.get_player(e.player_id)
        player.get_camera().distance += e.distance_diff
        return []

    def process_client_step(self):
        for client in self.local_clients:
            client.run_step()

    def render_client_step(self):
        for client in self.local_clients:
            client.render()

    def wait_for_input(self):
        import pygame
        import sys

        wait=True
        while wait:
            pygame.event.clear()
            event = pygame.event.wait()
            wait = True
            if event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_ESCAPE) or (event.type == pygame.QUIT):
                    pygame.quit()
                    sys.exit()
                else:
                    wait = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                wait = False

    def run_step(self):
        if self.config.client_only_mode:
            self.run_event_processing()
        else:
            self.run_pre_event_processing()
            self.run_event_processing()
            self.run_pre_physics_processing()
            self.run_physics_processing()
            self.run_post_physics_processing()

        self.tick()
        self.step_counter +=1

        # TODO: Slow, do we need to run every step?
        # only needed for net play
        # self.cleanup()

    def run(self):
        done = True
        while self.state == "RUNNING":
            if done:
                self.content.reset()
            self.process_client_step()
            self.run_step()
            self.render_client_step()
            if self.config.wait_for_user_input:
                for player in self.player_manager.players_map.values():
                    observation, reward, done, info = self.content.get_step_info(player)
                    print(f"Player: {player.get_id()}")
                    # print(observation)
                    print(reward)
                    print(done)
                    print(info)
                    print("----------")
                self.wait_for_input()

                
                    



gamectx = GameContext()
