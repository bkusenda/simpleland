import logging
import pkg_resources
import os
import hashlib
from .survival_utils import coord_to_vec
from ..import gamectx

def rand_int_from_coord(x,y,seed=123):
    v =  (x + y * seed ) % 12783723
    h = hashlib.sha1()
    h.update(str.encode(f"{v}"))
    return int(h.hexdigest(),16) % 172837

def get_tile_image_id(x,y,seed):
    v = rand_int_from_coord(x,y,seed) % 3 + 1
    return f"grass{v}"


class Sector:

    def __init__(self, scoord, height,width):
        self.height= height
        self.width = width
        self.scoord = scoord
        self.items = {}

    
    def add(self,coord, info):
        local_items = self.items.get(coord,[])
        local_items.append(info)
        self.items[coord] = local_items


class GameMap:

    def __init__(self,path,map_config):

        self.seed = 123
        self.full_path = pkg_resources.resource_filename(__name__,path)
        self.map_layers = []
        for layer_filename in map_config['layers']:
            with open(os.path.join(self.full_path,layer_filename),'r') as f:
                layer = f.readlines()
                self.map_layers.append(layer)            
        self.index = map_config['index']
        self.tile_size = 16
        self.sector_size = 64
        self.sectors = {}
        self.sectors_loaded = set()
        self.loaded = False
        self.spawn_points = {}

    def get_sector_coord(self,coord):
        if coord is None:
            return 0,0
        return coord[0]//self.sector_size,coord[1]//self.sector_size

    def get_sector_coord_from_pos(self,pos):
        if pos is None:
            return 0,0
        return pos[0]//self.tile_size//self.sector_size,pos[1]//self.tile_size//self.sector_size

    
    def add(self,coord,info):
        scoord = self.get_sector_coord(coord)
        sector:Sector = self.sectors.get(scoord)
        if sector is None:
            logging.debug(f"Creating sector {scoord}")
            sector = Sector(scoord,self.sector_size,self.sector_size)
        sector.add(coord,info)
        self.sectors[scoord] = sector
        return sector
        
    def load_static_layers(self):
        keys = set(self.index.keys())
        for i, lines in enumerate(self.map_layers):
            self.spawn_locations = []
            for ridx, line in enumerate(lines):
                linel = len(line)
                for cidx in range(0,linel,2):
                    key = line[cidx:cidx+2]
                    coord = (cidx//2, ridx)
                    if key in keys:
                        info = self.index.get(key)
                        self.add(coord,info)

    def initialize(self,coord):
        if not self.loaded:
            print("Loading Static Layers")
            self.load_static_layers()
            self.loaded= True
        self.load_sectors_near_coord(self.get_sector_coord(coord))

    def get_neigh_coords(self,scoord) -> set:
        x,y = scoord
        dirs = {
            (x,y+1),
            (x,y-1),
            (x-1,y),
            (x+1,y),
            (x-1,y-1),
            (x+1,y-1),
            (x-1,y+1),
            (x+1,y+1)}
        return dirs

    def load_sectors_near_coord(self,scoord):
        nei_scoords = self.get_neigh_coords(scoord)
        not_loaded_scoords = nei_scoords.difference(self.sectors_loaded)
        if scoord not in self.sectors_loaded:
            print(f"Loading Current sector {scoord}")
            self.load_sector(scoord)
        for new_scoord in not_loaded_scoords:
            print(f"Loading sector {new_scoord}")
            self.load_sector(new_scoord)        

    def load_sector(self,scoord):
        sector:Sector = self.sectors.get(scoord)
        if sector is None:
            coord = scoord[0] * self.sector_size, scoord[1] * self.sector_size
            sector = self.add(coord, info = {'type':'obj','obj':'water1'})
            logging.debug(f"Adding obj at in sector: {scoord} at {coord}" )
        self.sectors_loaded.add(scoord)
        for coord, item_list in sector.items.items():
            for info in item_list:
                self.load_obj_from_info(info,coord)
     

    def add_spawn_point(self,config_id, pos):
        pos_list = self.get_spawn_points(config_id)
        pos_list.append(pos)
        self.spawn_points[config_id] = pos_list

    def get_spawn_points(self,config_id):
        return self.spawn_points.get(config_id,[])

    def load_obj_from_info(self,info,coord):
        config_id = info['obj']
        if info.get('type') == "spawn_point":
            self.add_spawn_point(config_id,coord_to_vec(coord))
        else:
            obj = gamectx.content.create_object_from_config_id(config_id)
            obj.spawn(position=coord_to_vec(coord))      


    def get_layers(self):
        return range(2)
        
    def get_image_by_loc(self,x,y, layer_id):
        if layer_id == 0:
            return get_tile_image_id(x,y,self.seed)
        
        loc_id = rand_int_from_coord(x,y,self.seed)
        if x ==0 and y==0:
            return "baby_tree"
        if x ==2 and y==3:
            return "baby_tree"
        return None