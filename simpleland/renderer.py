from simpleland.utils import TickPerSecCounter
from typing import Dict, Any

import pygame
from .object import GObject
from .common import Vector, Line, Circle, Polygon, Rectangle
from .object_manager import GObjectManager
from PIL import Image
import numpy as np
import os

from .config import RendererConfig
from .asset_bundle import AssetBundle
from .player import Player
from . import gamectx
import math
import time
import pkg_resources
import logging


def scale(vec,vec2):
    return Vector(vec.x * vec2.x, vec.y* vec2.y)

def to_pygame(p, surface):
    """Convenience method to convert pymunk coordinates to pygame surface
    local coordinates.

    Note that in case positive_y_is_up is False, this function wont actually do
    anything except converting the point to integers.
    """

    return int(p[0]), surface.get_height() - int(p[1])


class Renderer:

    def __init__(self, config: RendererConfig, asset_bundle: AssetBundle):
        if config.sdl_audio_driver:
            os.environ['SDL_AUDIODRIVER'] = config.sdl_audio_driver
        if config.sdl_video_driver:
            os.environ["SDL_VIDEODRIVER"] = config.sdl_video_driver
        self.asset_bundle = asset_bundle
        self.config:RendererConfig = config
        self.format = config.format
        self._display_surf = None
        self.resolution = self.width, self.height = config.resolution
        self.aspect_ratio = (self.width * 1.0) / self.height

        self.initialized = False
        self.frame_cache = None
        self.debug=config.debug_render_bodies

        # These will be source object properties eventually
        self.view_height = 60000.0
        self.view_width = self.view_height * self.aspect_ratio
        logging.info(f"{self.view_width} by {self.view_width}")
        self.center = Vector.zero()

        self.images = {}
        self.sounds = {}

        # FPS Counter
        self.fps_counter = TickPerSecCounter(2)
        self.log_info = None

    def set_log_info(self,log_info):
        self.log_info = log_info

    def load_sounds(self):
        if self.config.sound_enabled:
            for k,path in self.asset_bundle.sound_assets.items():
                sound = pygame.mixer.Sound(pkg_resources.resource_filename(__name__,path))
                sound.set_volume(0.06)
                self.sounds[k] = sound

    def load_images(self):
        self.images = {}
        for k, path in self.asset_bundle.image_assets.items():
            image = pygame.image.load(pkg_resources.resource_filename(__name__,path)).convert_alpha()
            # image = pygame.transform.scale(image,(200,200))
            self.images[k] = image
            print(k)
            print(image)

    def play_sounds(self, sound_ids):
        if self.config.sound_enabled:
            for sid in sound_ids:
                self.sounds[sid].play()

    def get_image_by_id(self, image_id):
        return self.images.get(image_id)

    def update_view(self, view_height):
        self.view_height = max(view_height, 0.001)
        self.view_width = self.view_height * self.aspect_ratio

    def initialize(self):
        if self.config.sound_enabled:
            pygame.mixer.pre_init(  44100, -16, 2, 1024)
        pygame.init()

        self._display_surf = pygame.display.set_mode(self.resolution)  # , pygame.HWSURFACE | pygame.DOUBLEBUF)
        self.load_sounds()
        self.load_images()
        self.initialized = True

    def render_to_console(self, lines, x, y, fsize=18, spacing=12, color=(180, 180, 180)):
        font = pygame.font.SysFont(None, fsize)
        for i, l in enumerate(lines):
            font.render(l, False, (0, 0, 0))
            self._display_surf.blit(font.render(l, True, color), (x, y + spacing * i))

    def _draw_line(self,
                  obj: GObject,
                  line: Line,
                  color,
                  screen_factor,
                  screen_view_center,
                  angle,
                  center):
        obj_pos = obj.get_body().position
        obj_location1 = (obj_pos + line.a.rotated(obj.get_body().angle) - center)
        obj_location1 = obj_location1.rotated(-angle)
        p1 = scale(screen_factor,(obj_location1 + screen_view_center))
        p1 = to_pygame(p1, self._display_surf)

        obj_location2 = (obj_pos + line.b.rotated(obj.get_body().angle) - center)
        obj_location2 = obj_location2.rotated(-angle)
        p2 = scale(screen_factor, (obj_location2 + screen_view_center))
        p2 = to_pygame(p2, self._display_surf)

        pygame.draw.line(self._display_surf,
                         color,
                         p1,
                         p2,
                         1)

    def _draw_circle(self,
                    obj: GObject,
                    circle: Circle,
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

    def _draw_polygon(self,
                     obj: GObject,
                     shape: Polygon,
                     color,
                     screen_factor,
                     screen_view_center,
                     angle,
                     center):
        body = obj.get_body()
        obj_pos = body.position

        body_angle =body.angle
        verts = shape.get_vertices()
        new_verts = []
        for v in verts:
            obj_location = (obj_pos + v.rotated(body_angle) - center)
            obj_location = obj_location.rotated(-angle)
            p = scale(screen_factor,(obj_location + screen_view_center))
            p = to_pygame(p, self._display_surf)
            new_verts.append(p)
        pygame.draw.polygon(self._display_surf,
                color,
                new_verts,
                0)

    def _draw_rect(self,
                     obj: GObject,
                     shape: Rectangle,
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
            p = scale(screen_factor,(obj_location + screen_view_center))
            p = to_pygame(p, self._display_surf)
            new_verts.append(p)
        pygame.draw.polygon(self._display_surf,
                color,
                new_verts,
                0)

    def _draw_object(self, center, obj, angle, screen_factor, screen_view_center, color=None):

        

        image_id = obj.get_data_value("image")
        image_used = image_id is not None and not self.config.disable_textures
        if image_used:
            body_angle = obj.get_body().angle
            obj_pos = obj.get_body().position
            
            # TODO: fix, main_shape will not always have radius
            body_w, body_h = obj.get_image_dims()
            image = self.get_image_by_id(image_id)
            if image is not None:
                image_size = int(body_w*screen_factor[0]),int(body_h*screen_factor[1])
                
                if image_size[0]> 5000:
                    print("zoom out/ to close {}".format(image_size))
                
                image = pygame.transform.scale(image,image_size)  
                image = pygame.transform.rotate(image,((body_angle-angle) * 57.2957795)%360)
                rect = image.get_rect()

                image_loc = scale(screen_factor, ((obj_pos- center).rotated(-angle)  + screen_view_center))
                image_loc = to_pygame(image_loc, self._display_surf)
                rect.center = image_loc
                self._display_surf.blit(image,rect)
            else:
                image_used= False

        if not image_used or self.config.render_shapes:
            for i, shape in enumerate(obj.get_shapes()):
                if color is None:
                    if i == 1:
                        color = (100, 200, 200)
                    else:
                        color = (255, 50, 50)

                if type(shape) == Line:
                    self._draw_line(obj,
                                shape,
                                color,
                                screen_factor,
                                screen_view_center,
                                angle = angle,
                                center = center)
                elif type(shape) == Circle:
                    self._draw_circle(obj,
                                    shape,
                                    color,
                                    screen_factor,
                                    screen_view_center,
                                    angle = angle,
                                    center = center)
                elif type(shape) == Polygon:
                    self._draw_polygon(obj,
                                    shape,
                                    color,
                                    screen_factor,
                                    screen_view_center,
                                    angle = angle,
                                    center=center)


    def draw_grid_line(self,p1,p2,center,screen_view_center,color,screen_factor):
        p1 = (p1 - center)
        # print(p1)
        # print(screen_factor)
        # print(screen_view_center)

        p1 = scale(screen_factor, (p1 + screen_view_center))
        p1 = to_pygame(p1, self._display_surf)

        p2 = (p2 - center)
        p2 = scale(screen_factor, (p2 + screen_view_center))
        p2 = to_pygame(p2, self._display_surf)

        pygame.draw.line(self._display_surf,
                color,
                to_pygame(p1,self._display_surf),
                to_pygame(p2,self._display_surf),
                1)



    def _draw_grid(self, center, angle, screen_factor, screen_view_center, color = (50, 50, 50), size = 20, view_type=0):
        line_num = int(self.view_width/size) + 1

        x = int(center.x/size) * size 
        y = int(center.y/size) * size 


        y_start = y - size * line_num/2 

        for line in range(line_num):
            y_pos = y_start + size * line
            p1 = Vector(float(x-self.view_width),float(y_pos))
            p2 = Vector(float(x+self.view_width),float(y_pos))
            self.draw_grid_line(p1,p2,center,screen_view_center,color,screen_factor)

        x_start = x - size * line_num/2 
        for line in range(line_num):
            x_pos = x_start + size * line
            p1 = Vector(float(x_pos),float(y+self.view_height))
            p2 = Vector(float(x_pos),float(y-self.view_height))
            self.draw_grid_line(p1,p2,center,screen_view_center,color,screen_factor)


    # TODO: Clean this up
    def process_frame(self,
                    render_time,
                    player:Player,
                    additional_data: Dict[str, Any]={}):

        if not self.initialized:
            self.initialize()

        if player is None:
            return
        object_manager = gamectx.object_manager
        # import pdb;pdb.set_trace()
        self._display_surf.fill((0, 0, 0))

        if self.debug:
            import pymunk.pygame_util
            draw_options = pymunk.pygame_util.DrawOptions(self._display_surf)
            gamectx.physics_engine.space.debug_draw(draw_options)

        camera = player.get_camera()
        # TODO: make max customizeable 
        self.update_view(max(camera.get_distance(),1))

        view_obj:GObject = None
        center = Vector(self.view_width/2,self.view_height/2)
        angle=0
        if self.config.view_type == 0:
            view_obj = object_manager.get_by_id(player.get_object_id(), render_time)
            if view_obj is not None:
                center = view_obj.get_body().position
                angle = view_obj.get_body().angle
        elif self.config.view_type == 1:
            center_obj = object_manager.get_by_id(player.get_object_id(), render_time)
            if center_obj is not None:
                center = center_obj.get_body().position

        center = center - camera.position_offset
        screen_factor = Vector(self.width / self.view_width, self.height / self.view_height)
        screen_view_center = Vector(self.view_width, self.view_height) / 2.0

        obj_list_sorted_by_depth= object_manager.get_objects_for_timestamp_by_depth(render_time)
        if self.config.draw_grid:
            self._draw_grid(center, angle, screen_factor, screen_view_center, size=self.config.grid_size, view_type= self.config.view_type)
        for depth, render_obj_dict in enumerate(obj_list_sorted_by_depth):
            obj:GObject
            for k, obj in render_obj_dict.items():
                if not obj.enabled:
                    continue
                if view_obj is not None and k == view_obj.get_id():
                    continue
                # elif abs((center - obj.get_body().position).length) > camera.get_distance() and obj.get_data_value('type') != 'static':
                #     continue
                self._draw_object(center, obj, angle, screen_factor, screen_view_center, obj.shape_color)
            if view_obj is not None and view_obj.enabled and depth == view_obj.depth:
                self._draw_object(center, view_obj, angle, screen_factor, screen_view_center, view_obj.shape_color)
            

        if self.config.show_console:
            console_info = ["FPS:{}".format(self.fps_counter.avg())]
            if self.log_info is not None:
                console_info.append(self.log_info)
            self.render_to_console(console_info, self. config.resolution[0]-100, 5)

    def render_frame(self):
        self.fps_counter.tick()
        if self.config.save_observation:
            self.get_last_frame()
        frame = self.frame_cache
        self.frame_cache = None
        if self.config.render_to_screen:
            pygame.display.flip()
        return frame

    def get_last_frame(self):

        img_st = pygame.image.tostring(self._display_surf, self.format)
        data = Image.frombytes(self.format, self.config.resolution, img_st)
        np_data = np.array(data)

        # cache
        self.frame_cache = np_data
        return np_data

