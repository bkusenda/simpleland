from typing import Dict, Any

import pygame

from .common import SLVector, SLObject, SLLine, SLCircle, SLPolygon
from .object_manager import SLObjectManager
from PIL import Image
import numpy as np
import os

from .config import RendererConfig
from .asset_manager import AssetManager
from .player import SLPlayer
from .game import SLGame
import time

def to_pygame(p, surface):
    """Convenience method to convert pymunk coordinates to pygame surface
    local coordinates.

    Note that in case positive_y_is_up is False, this function wont actually do
    anything except converting the point to integers.
    """

    return int(p[0]), surface.get_height() - int(p[1])


class SLRenderer:

    def __init__(self, config: RendererConfig, asset_manager: AssetManager):
        # os.environ['SDL_AUDIODRIVER'] = 'dsp'
        # os.environ["SDL_VIDEODRIVER"] = "dummy"
        self.asset_manager = asset_manager
        self.config = config
        self.format = config.format
        self._display_surf = None
        self.size = self.width, self.height = config.resolution
        self.aspect_ratio = (self.width * 1.0) / self.height
        self.initialized = False
        self.frame_cache = None

        # These will be source object properties eventually
        self.view_height = 60.0
        self.view_width = self.view_height * self.aspect_ratio
        self.center = SLVector.zero()
        self.initialize()
        self.update_audio()
        self.update_images()

        self.frames_to_count = 2
        self.frame_counter = [0 for i in range(self.frames_to_count)]
        self.last_spot = 0

    def count_frame(self):
        spot = int(time.time()) % self.frames_to_count
        if spot != self.last_spot:
            self.frame_counter[spot]=1
            self.last_spot = spot
        else:
            self.frame_counter[spot]+=1

    def avg_fps(self):
        return sum([v for i, v in enumerate(self.frame_counter) if self.last_spot != i])/(self.frames_to_count -1)

    def update_audio(self):
        for k,v in self.asset_manager.sound_assets.items():
            v.set_volume(0.06)

    def update_images(self):
        new_assets = {}
        for k, v in self.asset_manager.image_assets.items():
            print("current size {}".format(v.get_rect().size))

            new_assets[k] = pygame.transform.scale(v,(200,200))
        self.asset_manager.image_assets = new_assets

    def play_sounds(self, sound_ids):
        for sid in sound_ids:
            self.asset_manager.sound_assets[sid].play()

    def get_image_by_id(self, image_id):
        return self.asset_manager.image_assets.get(image_id)

    def update_view(self, view_height):
        self.view_height = max(view_height, 0.001)
        self.view_width = self.view_height * self.aspect_ratio

    def initialize(self):
        pygame.mixer.pre_init(  44100, -16, 2, 1024)
        pygame.init()
        self.asset_manager.load_assets()
        self._display_surf = pygame.display.set_mode(self.size)  # , pygame.HWSURFACE | pygame.DOUBLEBUF)
        self.initialized = True

    def render_to_console(self, lines, x, y, fsize=18, spacing=12, color=(180, 180, 180)):
        font = pygame.font.SysFont(None, fsize)
        for i, l in enumerate(lines):
            font.render(l, False, (0, 0, 0))
            self._display_surf.blit(font.render(l, True, color), (x, y + spacing * i))

    def draw_line(self,
                  obj: SLObject,
                  line: SLLine,
                  color,
                  screen_factor,
                  screen_view_center,
                  angle,
                  center):
        obj_pos = obj.get_body().position
        obj_location1 = (obj_pos + line.a.rotated(obj.get_body().angle) - center)
        obj_location1 = obj_location1.rotated(-angle)
        p1 = screen_factor * (obj_location1 + screen_view_center)
        p1 = to_pygame(p1, self._display_surf)

        obj_location2 = (obj_pos + line.b.rotated(obj.get_body().angle) - center)
        obj_location2 = obj_location2.rotated(-angle)
        p2 = screen_factor * (obj_location2 + screen_view_center)
        p2 = to_pygame(p2, self._display_surf)

        pygame.draw.line(self._display_surf,
                         color,
                         p1,
                         p2,
                         1)

    def draw_circle(self,
                    obj: SLObject,
                    circle: SLCircle,
                    color,
                    screen_factor,
                    screen_view_center,
                    angle,
                    center):
        obj_pos = obj.get_body().position + circle.offset # TODO: Doesn't work with offset
        obj_location = (obj_pos - center)
        obj_location = obj_location.rotated(-angle)
        p = screen_factor * (obj_location + screen_view_center)
        p = to_pygame(p, self._display_surf)
        size = int(circle.radius * screen_factor[0])
        pygame.draw.circle(self._display_surf,
                           color,
                           p,
                           size,
                           1)

    def draw_polygon(self,
                     obj: SLObject,
                     shape: SLPolygon,
                     color,
                     screen_factor,
                     screen_view_center,
                     angle,
                     center):
        obj_pos = obj.get_body().position

        body_angle =obj.get_body().angle
        verts = shape.get_vertices()
        new_verts = []
        for v in verts:
            obj_location = (obj_pos + v.rotated(body_angle) - center)
            obj_location = obj_location.rotated(-angle)
            p = screen_factor * (obj_location + screen_view_center)
            p = to_pygame(p, self._display_surf)
            new_verts.append(p)
        pygame.draw.polygon(self._display_surf,
                color,
                new_verts,
                1)

    def draw_object(self, center, obj, angle, screen_factor, screen_view_center, color=None):

        color = (255, 50, 50)

        image_id = obj.get_data_value("image")
        image_used = image_id is not None and not self.config.disable_textures
        if image_used:
            body_angle = obj.get_body().angle
            obj_pos = obj.get_body().position
            body_w, body_h = obj.get_body().size
            image = self.get_image_by_id(image_id)
            image_size = int(body_w*screen_factor[0]),int(body_h*screen_factor[1])
            
            if image_size[0]> 5000:
                print("zoom out/ to close {}".format(image_size))
            
            image = pygame.transform.scale(image,image_size)  
            image = pygame.transform.rotate(image,((body_angle-angle) * 57.2957795)%360)
            rect = image.get_rect()

            image_loc = screen_factor * ((obj_pos- center).rotated(-angle)  + screen_view_center)
            image_loc = to_pygame(image_loc, self._display_surf)
            rect.center = image_loc
            self._display_surf.blit(image,rect)

        if not image_used or self.config.render_shapes:
            for i, shape in enumerate(obj.get_shapes()):
                if i == 1:
                    color = (100, 200, 200)
                else:
                    color = (255, 50, 50)

                if type(shape) == SLLine:
                    self.draw_line(obj,
                                shape,
                                color,
                                screen_factor,
                                screen_view_center,
                                angle = angle,
                                center = center)
                elif type(shape) == SLCircle:
                    self.draw_circle(obj,
                                    shape,
                                    color,
                                    screen_factor,
                                    screen_view_center,
                                    angle = angle,
                                    center = center)
                elif type(shape) == SLPolygon:
                    self.draw_polygon(obj,
                                    shape,
                                    color,
                                    screen_factor,
                                    screen_view_center,
                                    angle = angle,
                                    center=center)

    # TODO: Clean this up
    def process_frame(self,
                    render_time,
                    player:SLPlayer,
                    game: SLGame,
                    additional_data: Dict[str, Any]={}):
        if player is None:
            return
        object_manager = game.object_manager
        # import pdb;pdb.set_trace()
        self._display_surf.fill((0, 0, 0))
        console_log = []
        view_obj = object_manager.get_by_id(player.get_object_id(), render_time)
        if view_obj == None:
            return

        # TODO: make max customizeable 
        self.update_view(max(view_obj.get_camera().get_distance(),1))
        center = view_obj.get_body().position
        angle = view_obj.get_body().angle

        screen_factor = SLVector(self.width / self.view_width, self.height / self.view_height)

        screen_view_center = SLVector(self.view_width, self.view_height) / 2.0

        self.draw_object(center, view_obj, angle, screen_factor, screen_view_center)
        render_obj_dict = object_manager.get_objects_for_timestamp(render_time)
        for k, obj in render_obj_dict.items():
            if k == view_obj.get_id():
                continue
            elif abs((center - obj.get_body().position).length) > view_obj.get_camera().get_distance() and obj.get_data_value('type') != 'static':
                continue
            self.draw_object(center, obj, angle, screen_factor, screen_view_center)

        if self.config.show_console:
            self.render_to_console(["FPS:{}".format(self.avg_fps())], self. config.resolution[0]-100, 5)


    def render_frame(self):
        self.count_frame()
        if self.config.save_observation and self.config.frame_cache is None:
            self.get_observation()
        frame = self.frame_cache
        self.frame_cache = None
        pygame.display.flip()
        return frame

    def get_observation(self):

        img_st = pygame.image.tostring(self._display_surf, self.format)
        data = Image.frombytes(self.format, self.config.resolution, img_st)
        np_data = np.array(data)

        # cache
        self.frame_cache = np_data
        return np_data

    def quit(self):
        pygame.quit()
