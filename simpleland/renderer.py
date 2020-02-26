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
        obj_pos = obj.get_body().position
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
                    angle,
                    center):
        obj_pos = obj.get_body().position + circle.offset # Doesn't work with offset
        obj_location = (obj_pos - center)
        obj_location = obj_location.rotated(angle)
        p = screen_factor * (obj_location + screen_view_center)
        p = to_pygame(p, self._display_surf)

        pygame.draw.circle(self._display_surf,
                           color,
                           p,
                           int(circle.radius * screen_factor[0]),
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

    def draw_object(self, center, obj, angle, screen_factor, screen_view_center, color=None):

        color = (255, 50, 50)

        body_angle = obj.get_body().angle

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
                                 angle,
                                 center)
            elif type(shape) == SLPolygon:
                self.draw_polygon(obj,
                                  shape,
                                  color,
                                  screen_factor,
                                  screen_view_center,
                                  angle,
                                  center)

    # TODO: Clean this up
    def process_frame(self,
                    view_obj:SLObject,
                    object_manager: SLObjectManager,
                    additional_data: Dict[str, Any]={},
                    show_console=False):

        if not self.initialized:
            self.on_init()
        self._display_surf.fill((0, 0, 0))
        console_log = []


        self.update_view(view_obj.get_camera().get_distance())
        center = view_obj.get_body().position
        angle = view_obj.get_body().angle

        screen_factor = SLVector(self.width / self.view_width, self.height / self.view_height)

        screen_view_center = SLVector(self.view_width, self.view_height) / 2.0

        self.draw_object(center, view_obj, 0, screen_factor, screen_view_center)

        for obj in object_manager.get_all_objects():
            if obj.get_id() == view_obj.get_id():
                continue
            self.draw_object(center, obj, angle, screen_factor, screen_view_center)

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
