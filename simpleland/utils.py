import time
import copy

uid = 0
def gen_id():
    global uid
    uid+=1
    return uid
class TickPerSecCounter:

    def __init__(self,size=2):
        # FPS Counter
        self.size = size
        self.counts = [0 for i in range(self.size)]
        self.last_spot = 0

    def tick(self):
        spot = int(time.time()) % self.size
        if spot != self.last_spot:
            self.counts[spot]=1
            self.last_spot = spot
        else:
            self.counts[spot]+=1

    def avg(self):
        return sum([v for i, v in enumerate(self.counts) if self.last_spot != i])/(self.size -1)


def merged_dict(d1,d2,visheight=0):
    if visheight==0:
        if d1 is None:
            d1 = {}
        d1 = copy.deepcopy(d1)
    if d2 is None:
        return d1
    for k,v in d2.items():
        if k in d1:
            if isinstance(v,dict) and isinstance(d1[k],dict):
                d1[k] = merged_dict(d1[k],v,visheight+1)
            else:
                d1[k] = v
        else:
            d1[k] = v
    return d1