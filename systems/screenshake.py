# systems/screenshake.py
import random

class ScreenShake:
    def __init__(self):
        self.t = 0.0
        self.strength = 0.0

    def kick(self, strength: float, duration: float):
        self.strength = max(self.strength, strength)
        self.t = max(self.t, duration)

    def update(self, dt: float):
        if self.t > 0.0:
            self.t -= dt
        else:
            self.strength = 0.0

    def offset(self):
        if self.t <= 0.0:
            return 0, 0
        s = self.strength
        return random.uniform(-s, s), random.uniform(-s, s)
