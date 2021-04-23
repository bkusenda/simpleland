import json
from simpleland.physics_engine import PymunkPhysicsEngine
from typing import List, Set, Dict, Any
from uuid import UUID


from .common import (Body, Circle,  Line
                     , Polygon, Space,  Vector)
from .object import (GObject)

# from .renderer import SLRenderer
from .utils import gen_id
from .config import GameDef, GameConfig, PhysicsConfig
import math
LATENCY_LOG_SIZE = 100
from .clock import clock
from .event_manager import EventManager
from .object_manager import GObjectManager
from .player_manager import PlayerManager
from .physics_engine import GridPhysicsEngine, PymunkPhysicsEngine

from .event import (Event, AdminEvent, MechanicalEvent,
            PeriodicEvent, ViewEvent, SoundEvent, DelayedEvent, InputEvent)
from .event import RemoveObjectEvent
import pygame
import sys
from .content import Content


class GameContext:

    def __init__(self):

        self.game_def:GameDef = None
        self.config:GameConfig = None
        self.physics_config:PhysicsConfig = None

        self.object_manager:GObjectManager = None
        self.physics_engine:GridPhysicsEngine = None
        self.player_manager:PlayerManager = None
        self.event_manager:EventManager = None
        self.content:Content=None
        self.state = None
        self.step_counter = 0
        self.last_position_lookup = {}

        self.tick_rate = None
        self.pre_event_callback = lambda : []
        self.input_event_callback = lambda event: []
        self.remote_clients:Dict[str,Any] = {}
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
        self.object_manager = GObjectManager()
        self.physics_engine = GridPhysicsEngine(self.physics_config)
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

    def speed_factor(self):
        if self.tick_rate:
            return self.tick_rate
        else:
            return 1

    def get_content(self):
        return self.content

    def add_local_client(self,client):
        self.local_clients.append(client)
        
    def get_remote_client(self, client_id):
        from .client import RemoteClient
        client = self.remote_clients.get(client_id, None)
        if client is None:
            client = RemoteClient(client_id)
            self.remote_clients[client.id] = client
        return client

    def get_player(self, client, player_type,is_human):
        """
        Get existing player or create new one
        """
        if client.player_id is None:
            player = self.content.new_player(client.id, player_id=None, player_type=player_type, is_human=is_human)
            client.player_id = player.get_id()
        else:
            player = self.player_manager.get_player(client.player_id)
        return player

    def change_game_state(self, new_state):
        self.state = new_state

    def create_snapshot_for_client(self,client):
        from .client import RemoteClient
        client:RemoteClient = client
        snapshot_timestamp = clock.get_time()
        om_snapshot = self.object_manager.get_snapshot_update(client.last_snapshot_time_ms)
        pm_snapshot = self.player_manager.get_snapshot() # TODO, updates since
        eventsnapshot = client.pull_events_snapshot()
        # em_snapshot = self.event_manager.get_snapshot_for_client(client.last_snapshot_time_ms)
        return snapshot_timestamp, {
            'om':om_snapshot,
            'pm':pm_snapshot,
            'em': eventsnapshot,
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
        
        all_new_events = []
        events_to_remove = []
        events_set = set(self.event_manager.get_events())
        while len(events_set)>0:
            e = events_set.pop()
        
            new_events = []
            if type(e) == AdminEvent:
                e: AdminEvent = e
                if e.value == 'QUIT':
                    self.change_game_state("QUITING")
                    events_to_remove.append(e)
            elif type(e) == InputEvent:
                new_events = self.content.process_input_event(e)
                events_to_remove.append(e)
            elif type(e) == ViewEvent:
                new_events = self._process_view_event(e)
                events_to_remove.append(e)
            elif type(e) == RemoveObjectEvent:
                self._process_remove_object_event(e)
                events_to_remove.append(e)
            elif type(e) == DelayedEvent:
                e: DelayedEvent = e
                new_events, remove_event = e.run()
                if remove_event:
                    events_to_remove.append(e)
            elif type(e) == PeriodicEvent:
                e: PeriodicEvent = e
                new_events, remove_event = e.run()
                if remove_event:
                    events_to_remove.append(e)

            # Add to queue to be processed
            for new_e in new_events:
                events_set.add(new_e)
            all_new_events.extend(new_events)

        # Add new events
        self.event_manager.add_events(all_new_events)

        # Remove completed events        
        for e in events_to_remove:
            self.event_manager.remove_event_by_id(e.get_id())
       

    def run_pre_physics_processing(self):
        events = self.content.pre_physics_processing()
        self.event_manager.add_events(events)

    def run_post_physics_processing(self):
        if self.config.track_updates:
            # TODO: Not efficient
            # Check for changes in position or angle and log change time
            new_position_lookup = {}
            for k,o in self.object_manager.get_objects().items():
                body = o.get_body()
                angle = body.angle
                position = body.position
                current_position = {'angle':angle,'position':position}

                last_position = self.last_position_lookup.get(k,None)
                if last_position is not None:
                    if ((last_position['angle'] != current_position['angle'] ) or
                    (last_position['position'] != current_position['position'])):
                        o.set_last_change(clock.get_time())
                new_position_lookup[k] = current_position
            self.last_position_lookup = new_position_lookup
        events = self.content.post_physics_processing()
        self.event_manager.add_events(events)

    def run_physics_processing(self): 
        self.physics_engine.update()

    def tick(self):
        clock.tick(self.tick_rate)     
        

    def add_player(self, player):
        self.player_manager.add_player(player) 

    def add_object(self,obj:GObject):
        
        obj.set_last_change(clock.get_time())
        self.object_manager.add(clock.get_time(), obj)
        self.physics_engine.add_object(obj)

    def add_event(self,e:Event):
        self.event_manager.add_event(e)
        if e.is_client_event:
            for client_id, client in self.remote_clients.items():
                client.add_event(e)
                
    def remove_object(self,obj:GObject):
        self.remove_object_by_id(obj.get_id())
        
    def remove_object_by_id(self,obj_id):
        event = RemoveObjectEvent(object_id =obj_id)
        self.add_event(event)

    def remove_all_objects(self):
        for o in list(self.object_manager.get_objects().values()):
            if not o.is_deleted:
                self.remove_object(o)

    def remove_all_events(self):
        self.event_manager.clear()
    
    def cleanup(self):
        for o in list(self.object_manager.get_objects().values()):
            if o.is_deleted:
                self.object_manager.remove_by_id(o.get_id())

    def get_sound_events(self):
        events_to_remove = []
        sound_ids = []
        for e in self.event_manager.get_events():
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

    def _process_remove_object_event(self,e:RemoveObjectEvent):
        obj = self.object_manager.get_by_id(e.object_id)
        if obj is not None:
            obj.delete()
            obj.set_last_change(clock.get_time())
            self.physics_engine.remove_object(obj)
            self.object_manager.remove_by_id(obj.get_id())
        else:
            print(f"Object not found, not deleting {e.object_id}")
        
        return True

    def process_client_step(self):
        for client in self.local_clients:
            client.run_step()

    def render_client_step(self):
        for client in self.local_clients:
            client.render()

    def wait_for_input(self):

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
  

    def run(self):
        done = True
        while self.state == "RUNNING":
            if done:
                if not self.config.client_only_mode:
                    self.content.reset()
                print("RESETTING")
            self.process_client_step()
            self.run_step()
            self.render_client_step()
            for player in list(self.player_manager.players_map.values()):
                # print(f"Player: {player.get_id()} {player.get_object_id()}")
                observation, reward, done, info = self.content.get_step_info(player)
            if self.config.wait_for_user_input:
                # print(f"Player: {player.get_id()} {player.get_object_id()}")
                # print(observation)
                print(reward)
                print(done)
                print(info)
                print("----------")


                self.wait_for_input()

               



gamectx = GameContext()
