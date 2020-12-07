import time
import uuid

def gen_id() -> str:
    return str(uuid.uuid1())

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
