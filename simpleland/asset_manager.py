import pygame

class AssetManager:

    def __init__(self):
        self.image_assets={}
        self.sound_assets={}

    def load_assets(self):
        self.image_assets['1'] = pygame.image.load(r'assets/redfighter0006.png')
        self.image_assets['2'] = pygame.image.load(r'assets/ship2.png')
        self.image_assets['energy1'] = pygame.image.load(r'assets/energy1.png') 
        self.image_assets['astroid1'] = pygame.image.load(r'assets/astroid1.png') 
        self.image_assets['astroid2'] = pygame.image.load(r'assets/astroid2.png') 
        self.sound_assets['bleep1'] = pygame.mixer.Sound('assets/sounds/bleep.wav')
        self.sound_assets['bleep2'] = pygame.mixer.Sound('assets/sounds/bleep2.wav')
