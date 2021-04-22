

class AssetBundle:

    def __init__(self, 
            image_assets, 
            sound_assets, 
            get_image_id_fn=lambda obj,angle : obj.image_id_default, 
            get_view_position_fn=lambda obj : obj.get_position()):
        self.image_assets = image_assets
        self.sound_assets = sound_assets
        self.get_image_id_fn = get_image_id_fn
        self.get_view_position_fn = get_view_position_fn
