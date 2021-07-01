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



# Used for looking for memory leaks
# Source: https://stackoverflow.com/questions/449560/how-do-i-determine-the-size-of-an-object-in-python
import sys
from types import ModuleType, FunctionType
from gc import get_referents

# Custom objects know their class.
# Function objects seem to know way too much, including modules.
# Exclude modules as well.
BLACKLIST = type, ModuleType, FunctionType


def getsize(obj):
    """sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size

import sys
from numbers import Number
from collections import deque
from collections.abc import Set, Mapping
ZERO_DEPTH_BASES = (str, bytes, Number, range, bytearray)


def getsizewl(obj_0):
    """Recursively iterate to sum size of object & members."""
    _seen_ids = set()
    def inner(obj):
        obj_id = id(obj)
        if obj_id in _seen_ids:
            return 0
        _seen_ids.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, ZERO_DEPTH_BASES):
            pass # bypass remaining control flow and return
        elif isinstance(obj, (tuple, list, Set, deque)):
            size += sum(inner(i) for i in obj)
        elif isinstance(obj, Mapping) or hasattr(obj, 'items'):
            size += sum(inner(k) + inner(v) for k, v in getattr(obj, 'items')())
        # Check for custom object instances - may subclass above too
        if hasattr(obj, '__dict__'):
            size += inner(vars(obj))
        if hasattr(obj, '__slots__'): # can have __slots__ with __dict__
            size += sum(inner(getattr(obj, s)) for s in obj.__slots__ if hasattr(obj, s))
        return size
    return inner(obj_0)