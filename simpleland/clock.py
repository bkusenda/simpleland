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
    
    def __init__(self, start_time= 0):
        self.start_time = start_time
        self.tick_time = 0
        self.pygame_clock = pygame.time.Clock()

    def _current_time(self):
        return self.tick_time

    def get_start_time(self):
        return self.start_time
    
    def tick(self,tick_rate=None):
        if tick_rate: 
            self.pygame_clock.tick(tick_rate)
        self.tick_time +=1
        return self.tick_time

    def get_time(self):
        return self.tick_time

    def get_tick_counter(self):
        return self.tick_time

    def set_absolute_time(self,time):
        self.tick_time = time

    def get_exact_time(self):
        return self.tick_time


clock = StepClock()