from typing import Dict, Any

import pygame

from .common import SLVector, SLObject, SLLine, SLCircle, SLPolygon
from .object_manager import SLObjectManager
from PIL import Image
import numpy as np


def to_pygame(p, surface):
    """Convenience method to convert pymunk coordinates to pygame surface
    local coordinates.

    Note that in case positive_y_is_up is False, this function wont actually do
    anything except converting the point to integers.
    """

    return int(p[0]), surface.get_height() - int(p[1])


class SLRenderer:

    def __init__(self, resolution=(640, 480), format='RGB', save_observation=False):
        self.format = format
        self._running = True
        self._display_surf = None
        self.size = self.width, self.height = resolution
        self.resolution = resolution
        self.aspect_ratio = (self.width * 1.0) / self.height
        self.initialized = False
        self.frame_cache = None
        self.save_observation = save_observation

        # These will be source object properties eventually
        self.view_height = 30.0
        self.view_width = self.view_height * self.aspect_ratio
        self.center = SLVector.zero()
        self.image_assets = {}
        self.load_assets()
        self.resize_images()
        self.render_shapes = False

    def load_assets(self):
        self.image_assets['1'] = pygame.image.load(r'assets/redfighter0006.png')
        self.image_assets['2'] = pygame.image.load(r'assets/ship2.png')
        self.image_assets['energy1'] = pygame.image.load(r'assets/energy1.png') 
        self.image_assets['astroid1'] = pygame.image.load(r'assets/astroid1.png') 
        self.image_assets['astroid2'] = pygame.image.load(r'assets/astroid2.png') 

    def resize_images(self):
        new_assets = {}
        for k, v in self.image_assets.items():
            new_assets[k] = pygame.transform.scale(v,(50,50))
        self.image_assets = new_assets

    def update_view(self, view_height):
        self.view_height = max(view_height, 0.001)
        self.view_width = self.view_height * self.aspect_ratio

    def on_init(self):
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size)  # , pygame.HWSURFACE | pygame.DOUBLEBUF)
        self.initialized = True

    def render_to_console(self, lines, x, y, fsize=18, spacing=12, color=(180, 180, 180)):
        font = pygame.font.SysFont(None, fsize)
        for i, l in enumerate(lines):
            self._display_surf.blit(font.process_frame(l, True, color), (x, y + spacing * i))

    def draw_line(self,
                  obj: SLObject,
                  line: SLLine,
                  color,
                  screen_factor,
                  screen_view_center,
                  angle,
                  center):
        obj_pos = obj.get_body().position.rotated(obj.get_body().angle)
        obj_location1 = (obj_pos + line.a - center)
        obj_location1 = obj_location1.rotated(angle)
        p1 = screen_factor * (obj_location1 + screen_view_center)
        p1 = to_pygame(p1, self._display_surf)

        obj_location2 = (obj_pos + line.b - center)
        obj_location2 = obj_location2.rotated(angle)
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
                    display_angle,
                    angle,
                    center):
        obj_pos = obj.get_body().position + circle.offset # Doesn't work with offset
        obj_location = (obj_pos - center)
        obj_location = obj_location.rotated(angle)
        p = screen_factor * (obj_location + screen_view_center)
        p = to_pygame(p, self._display_surf)
        size = int(circle.radius * screen_factor[0])
        pygame.draw.circle(self._display_surf,
                           color,
                           p,
                           size,
                           1)
        # image_size = int(circle.radius)            
        # image = pygame.transform.scale(self.ship_image,(size*4,size*4))
        # image = pygame.transform.rotate(image,display_angle)
        # image_loc = (p[0],p[1] - 40)
        # self._display_surf.blit(image,image_loc)

    def draw_polygon(self,
                     obj: SLObject,
                     shape: SLPolygon,
                     color,
                     screen_factor,
                     screen_view_center,
                     angle,
                     display_angle,
                     center):
        obj_pos = obj.get_body().position

        verts = shape.get_vertices()
        new_verts = []
        for v in verts:
            obj_location = (obj_pos + v - center)
            obj_location = obj_location.rotated(angle)
            p = screen_factor * (obj_location + screen_view_center)
            p = to_pygame(p, self._display_surf)
            new_verts.append(p)
        pygame.draw.polygon(self._display_surf,
                color,
                new_verts,
                1)

    def draw_object(self, center, obj, angle, screen_factor, screen_view_center, display_angle, color=None):

        color = (255, 50, 50)

        body_angle = obj.get_body().angle

        image_id = obj.get_data_value("image")
        image_used = image_id is not None and image_id in self.image_assets
        if image_used:
            obj_pos = obj.get_body().position
            image = self.image_assets[image_id].copy()
            image = pygame.transform.scale(image,(50,50))

            image = pygame.transform.rotate(image,angle * 57.2957795)

            offset = SLVector(1.20,-1.30).rotated(-angle) 

            image_loc = screen_factor *((obj_pos- center - offset).rotated(angle)  + screen_view_center)
            image_loc = to_pygame(image_loc, self._display_surf)
            self._display_surf.blit(image,image_loc)

        if not image_used or self.render_shapes:
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
                                angle,
                                center)
                elif type(shape) == SLCircle:
                    self.draw_circle(obj,
                                    shape,
                                    color,
                                    screen_factor,
                                    screen_view_center,
                                    display_angle,
                                    angle,
                                    center)
                elif type(shape) == SLPolygon:
                    self.draw_polygon(obj,
                                    shape,
                                    color,
                                    screen_factor,
                                    screen_view_center,
                                    angle = angle,
                                    display_angle=body_angle,
                                    center=center)

    # TODO: Clean this up
    def process_frame(self,
                    render_time,
                    obj_id:str,
                    object_manager: SLObjectManager,
                    additional_data: Dict[str, Any]={},
                    show_console=False):
        # import pdb;pdb.set_trace()

        if not self.initialized:
            self.on_init()
        self._display_surf.fill((0, 0, 0))
        console_log = []
        view_obj = object_manager.get_by_id(obj_id, render_time)
        #t, view_obj = object_manager.get_latest_by_id(obj_id)
        #print(view_obj)
        if view_obj == None:
            print(object_manager.objects[obj_id].timestamps)
            raise Exception("No View Object {} at render_time {}".format(obj_id,render_time))
            
        self.update_view(view_obj.get_camera().get_distance())
        center = view_obj.get_body().position
        angle = view_obj.get_body().angle

        screen_factor = SLVector(self.width / self.view_width, self.height / self.view_height)

        screen_view_center = SLVector(self.view_width, self.view_height) / 2.0

        self.draw_object(center, view_obj, 0, screen_factor, screen_view_center,angle)
        render_obj_dict = object_manager.get_objects_for_timestamp(render_time)
        for k, obj in render_obj_dict.items():
            if k == view_obj.get_id():
                continue
            elif abs((center - obj.get_body().position).length) > 20 and obj.get_data_value('type') != 'static':
                continue
            self.draw_object(center, obj, angle, screen_factor, screen_view_center, display_angle=angle)

        if show_console:
            console_log.append("object orientation: %s" % angle)
            console_log.append("     actual center: %s" % center)
            console_log.append("     screen center: %s" % screen_view_center)
            console_log.append("     screen factor: %s" % screen_factor)
            console_log.append("            center: %s" % center)
            console_log.append("   %s" % additional_data.get())

            self.render_to_console(console_log, 0, 0)

    def render_frame(self):
        if self.save_observation and self.frame_cache is None:
            self.get_observation()
        frame = self.frame_cache
        self.frame_cache = None
        pygame.display.flip()
        return frame

    def get_observation(self):

        img_st = pygame.image.tostring(self._display_surf, self.format)
        data = Image.frombytes(self.format, self.resolution, img_st)
        np_data = np.array(data)

        # cache
        self.frame_cache = np_data
        return np_data

    def quit(self):
        pygame.quit()
