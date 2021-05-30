import time
import pygame

# class SimClock:
    
#     def __init__(self, start_time= None):
#         self.resolution = 1000# milliseconds
#         self.start_time = self._current_time() if start_time is None else start_time
#         self.pygame_clock = Clock()
#         self.tick_time = self.get_exact_time()
#         self.tick_counter = 0

#     def _current_time(self):
#         return time.time() * self.resolution
    
#     def get_start_time(self):
#         return self.start_time
    
#     def tick(self,tick_rate):
#         if tick_rate !=0: 
#             self.pygame_clock.tick(tick_rate)
#         self.tick_time = self.get_exact_time()
#         self.tick_counter +=1
#         return self.tick_time

#     def get_time(self):
#         return self.tick_time

#     def get_tick_counter(self):
#         return self.tick_counter

#     def set_absolute_time(self,time):
#         self.start_time = time
#         self.tick_time = self.get_exact_time()

#     def get_exact_time(self):
#         return self._current_time() - self.start_time



class StepClock:
    
    def __init__(self,tick_rate=0):
        self._start_time = time.time()
        self.tick_time = 0
        self.pygame_clock = pygame.time.Clock()
        self.tick_rate = tick_rate


    def get_start_time(self):
        return self._start_time

    def set_start_time(self,start_time):
        self._start_time=start_time

    def set_tick_rate(self,tick_rate):
        self.tick_rate = tick_rate


    def get_tick_size(self):
        return 1.0 / self.tick_rate

    def get_game_time(self):
        return (time.time()- self._start_time)
    
    def tick(self):
        if self.tick_rate: 
            self.pygame_clock.tick(self.tick_rate)
            self.tick_time  = int(self.get_game_time() * self.tick_rate)
        
        else:
            self.tick_time +=1
        

        return self.tick_time

    def get_time(self):
        return self.tick_time

    def get_tick_counter(self):
        return self.tick_time


    def get_exact_time(self):
        return self.tick_time


clock = StepClock()