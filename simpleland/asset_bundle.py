

class AssetBundle:

    def __init__(self, 
            image_assets, 
            sound_assets, 
            music_assets,
            tilemaploader):
        self.image_assets = image_assets
        self.sound_assets = sound_assets
        self.music_assets = music_assets
        self.tilemaploader = tilemaploader
