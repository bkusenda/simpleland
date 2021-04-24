from .common import Base, Vector
class Camera(Base):

    def __init__(self,follow_obj_id=None, distance: float = 30, angle=0, position_offset = Vector(0,0), view_type=0,center=None):
        self.follow_obj_id = follow_obj_id
        self.distance = distance  # zoom
        self.angle = angle
        self.position_offset = position_offset
        self.view_type =view_type
        self.center = center
        

    def get_distance(self):
        return self.distance

    def get_angle(self):
        angle = self.angle
        if self.view_type == 0:
            obj = self.get_follow_object()
            if obj:
                angle+= obj.angle
        return angle

    def set_follow_object(self, obj):
        self.follow_obj_id = obj.get_id()

    def get_follow_object(self):
        from . import gamectx

        return gamectx.object_manager.get_by_id(self.follow_obj_id)

    def get_center(self):
        if self.center is not None:
            return self.center - self.position_offset
        obj = self.get_follow_object()
        if obj:
            return obj.get_view_position()
        else:
            return Vector(0,0)

    def get_view_type(self):
        return self.view_type
        
