# systems/swarm_power.py
import pygame


class SwarmPower:
    def __init__(self, radius: float, cap_count: int):
        self.radius = float(radius)
        self.cap_count = int(cap_count)

        self.close_count = 0
        self.power01 = 0.0  # 0..1 (smoothed)

    def update(self, dt: float, drone_pos: pygame.Vector2, boids):
        r2 = self.radius * self.radius
        c = 0
        for b in boids:
            if (b.pos - drone_pos).length_squared() <= r2:
                c += 1

        self.close_count = c
        raw = min(1.0, c / max(1, self.cap_count))

        # smooth
        self.power01 += (raw - self.power01) * min(1.0, 8.0 * dt)
