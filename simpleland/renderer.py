from pymunk.vec2d import Vec2d
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
from .player import Camera
from .spritesheet import Spritesheet
from .content import Content

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
        self.sprite_sheets = {}

        # FPS Counter
        self.fps_counter = TickPerSecCounter(2)
        self.log_info = None

        

    def set_log_info(self,log_info):
        self.log_info = log_info

    def load_sounds(self):
        if self.config.sound_enabled:
            pass
            for k,path in self.asset_bundle.sound_assets.items():
                print(f"Loading ")
                sound = pygame.mixer.Sound(pkg_resources.resource_filename(__name__,path))
                sound.set_volume(0.1)
                self.sounds[k] = sound


    def load_images(self):
        self.images = {}
        for k, (path,frame_id) in self.asset_bundle.image_assets.items():
            full_path = pkg_resources.resource_filename(__name__,path)
            if frame_id is None:
                image = pygame.image.load(full_path).convert_alpha()
            else:
                if path not in self.sprite_sheets:
                    self.sprite_sheets[path] = Spritesheet(full_path)
                image = self.sprite_sheets[path].parse_sprite(frame_id)
            self.images[k] = image
                
    def play_sounds(self, sound_ids):
        if self.config.sound_enabled:
            for sid in sound_ids:
                print("PLAYING SOUND")
                self.sounds[sid].play()

    def play_music(self, music_id):
        if self.config.sound_enabled:
            if self.config.sound_enabled:
                path =self.asset_bundle.music_assets[music_id]
                full_path = pkg_resources.resource_filename(__name__,path)
                print(f"Loading Music from: {full_path}")
                pygame.mixer.music.load(full_path)
                pygame.mixer.music.play(-1)

    def get_image_by_id(self, image_id):
        return self.images.get(image_id)

    def update_view(self, view_height):
        self.view_height = max(view_height, 0.001)
        self.view_width = self.view_height * self.aspect_ratio

    def initialize(self):
        if self.config.sound_enabled:
            pygame.mixer.pre_init(44100, -16, 4, 2048)
        pygame.init()

        flags =  pygame.DOUBLEBUF # | pygame.RESIZABLE | pygame.SCALED
        self._display_surf = pygame.display.set_mode(self.resolution,flags)  # ,)
        # self._display_surf = pygame.display.set_mode(self.resolution)  # ,)
        self.load_sounds()
        self.load_images()
        self.play_music("background")
        pygame.key.set_repeat(500,100)

        self.initialized = True

    def render_to_console(self, lines, x, y, fsize=18, spacing=12, color=(180, 180, 180), background_color=None):
        font = pygame.font.SysFont(None, fsize)
        num_lines = len(lines)
        if background_color is not None:
            pygame.draw.rect(self._display_surf, background_color, pygame.Rect(x-3, y-3, self.view_width, y+num_lines*spacing+3))
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
        obj_pos = obj.get_view_position()
        obj_location1 = (obj_pos + line.a.rotated(obj.angle) - center)
        obj_location1 = obj_location1.rotated(-angle)
        p1 = scale(screen_factor,(obj_location1 + screen_view_center))
        p1 = to_pygame(p1, self._display_surf)

        obj_location2 = (obj_pos + line.b.rotated(obj.angle) - center)
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
        obj_pos = obj.get_view_position() + circle.offset # TODO: Doesn't work with offset
        obj_location = (obj_pos - center)
        obj_location = obj_location.rotated(-angle)
        p = scale(screen_factor,(obj_location + screen_view_center))
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
        obj_pos = obj.get_view_position()

        verts = shape.get_vertices()
        new_verts = []
        for v in verts:
            obj_location = (obj_pos + v.rotated(obj.angle) - center)
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
        obj_pos = obj.get_view_position()

        body_angle =obj.angle
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

    def _draw_object(self, center, obj:GObject, angle, screen_factor, screen_view_center, color=None):

        image_id= obj.get_image_id(angle)
        rotate = obj.rotate_sprites
        image_used = image_id is not None and not self.config.disable_textures
        if image_used:
            obj_pos:Vector = obj.get_view_position()
            
            body_angle = obj.angle

            # TODO: fix, main_shape will not always have radius
            # 

            image = self.get_image_by_id(image_id)
            
            if image is not None:
                scale_w, scale_h = 1,1 #obj.get_image_dims()
                body_w, body_h = image.get_size()
                image_size = int(body_w*screen_factor[0] *scale_w)+1,int(body_h*screen_factor[1] *scale_h)+1
                
                if image_size[0]> 5000:
                    image_size = 200,200
                    print("zoom out/ to close {}".format(image_size))

                image = pygame.transform.scale(image,image_size)
                if rotate:  
                    image = pygame.transform.rotate(image,((body_angle-angle) * 57.2957795)%360)
                rect = image.get_rect()

                image_loc = scale(screen_factor, ((obj_pos- center - obj.image_offset).rotated(-angle)  + screen_view_center))
                image_loc = to_pygame(image_loc, self._display_surf)
                rect.center = image_loc
                
                # self._display_surf.blit(image,rect)
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


    def draw_grid_line(self,p1,p2,angle,center,screen_view_center,color,screen_factor):
        p1 = (p1 - center).rotated(angle)
        p1 = scale(screen_factor, (p1 + screen_view_center))
        p1 = to_pygame(p1, self._display_surf)

        p2 = (p2 - center).rotated(angle)
        p2 = scale(screen_factor, (p2 + screen_view_center))
        p2 = to_pygame(p2, self._display_surf)
        pygame.draw.line(self._display_surf,
                color,
                to_pygame(p1,self._display_surf),
                to_pygame(p2,self._display_surf),
                1)


    def _draw_grid(self, center, angle, screen_factor, screen_view_center, color = (50, 50, 50), size = 20, view_type=0):
        line_num = int(self.view_width/size) + 4

        x = int(center.x/size) * size   - size/2
        y = int(center.y/size) * size  - size/2

        y_start = -(y - size * line_num)
        y_center = Vector(center.x,-center.y)
        for line in range(line_num *2):
            y_pos = y_start - size * line
            p1 = Vector(x-self.view_width,y_pos)
            p2 = Vector(x+self.view_width,y_pos)
            self.draw_grid_line(p1,p2,angle,y_center,screen_view_center,color,screen_factor)

        x_start = x - size * line_num 
        for line in range(line_num *2):
            x_pos = x_start + size * line
            p1 = Vector(x_pos,y-self.view_height)
            p2 = Vector(x_pos,y+self.view_height)
            self.draw_grid_line(p1,p2,angle,center,screen_view_center,color,screen_factor)


    def filter_objects_for_rendering(self,objs,camera:Camera):
        center = camera.get_center()
        object_list_depth_sorted = [[], [], [], []]
        for k, o in objs.items():
            o:GObject = o
            if o is not None and not o.is_deleted and o.is_visible():
                within_range = o.get_view_position().get_distance(center) < self.view_width
                if within_range:
                    object_list_depth_sorted[o.depth].append(o)

        # TODO: Need to adjust with angle
        center_bottom = center - Vector(0,100)
        for lst in object_list_depth_sorted:
            lst.sort(key=lambda o: -o.get_position().get_distance(center_bottom))
        return object_list_depth_sorted

    # TODO: Clean this up
    def process_frame(self,
                    render_time,
                    player:Player):
       
        if not self.initialized:
            self.initialize()

        # import pdb;pdb.set_trace()
        self._display_surf.fill((20, 100, 20))

        angle = 0
        camera:Camera = None
        center:Vector = None
        if player:
            camera = player.get_camera()
        else:
            camera = Camera(center=Vector(self.view_width/2,self.view_height/2))

        center = camera.get_center()
        angle = camera.get_angle()
               
        # TODO: Should be handled in camera not renderer 
        self.update_view(max(camera.get_distance(),1))
        
        center = center - camera.position_offset
        screen_factor = Vector(self.width / self.view_width, self.height / self.view_height)
        screen_view_center = Vector(self.view_width, self.view_height) / 2.0

        obj_list_sorted_by_depth= self.filter_objects_for_rendering(gamectx.object_manager.get_objects(),camera)
        if self.config.draw_grid:
            self._draw_grid(center, angle, screen_factor, screen_view_center, size=self.config.tile_size, view_type= self.config.view_type)
        for depth, render_obj_dict in enumerate(obj_list_sorted_by_depth):
            obj:GObject
            for obj in render_obj_dict:
                if not obj.enabled or obj.is_deleted or not obj.is_visible():
                    continue
                self._draw_object(center, obj, angle, screen_factor, screen_view_center, obj.shape_color)
            
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

