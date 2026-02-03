# systems/beacon_system.py
from __future__ import annotations
import random
import math
import pygame


class BeaconSystem:
    """Temporary anchor beacon that occasionally appears.

    While active, boids can use beacon.pos as their 'anchor' to regroup.
    It is designed as a pacing tool (creates "moments") without adding new controls.
    """

    def __init__(self):
        self.active = False
        self.pos = pygame.Vector2(0, 0)
        self.radius = 26.0

        self._cooldown = self._roll_cd()
        self._life = 0.0
        self._life_total = 0.0
        self._pulse = 0.0

    def _roll_cd(self) -> float:
        return random.uniform(16.0, 28.0)

    def _roll_life(self) -> float:
        return random.uniform(6.5, 9.0)

    def is_active(self) -> bool:
        return self.active

    def update(self, dt: float, camera_scroll_x: float, screen_w: int, screen_h: int):
        self._pulse += dt

        if not self.active:
            self._cooldown -= dt
            if self._cooldown <= 0.0:
                # Spawn slightly ahead so player can react
                x = camera_scroll_x + random.uniform(screen_w * 0.70, screen_w * 0.95)
                y = random.uniform(90, screen_h - 90)
                self.pos.update(x, y)
                self.active = True
                self._life_total = self._roll_life()
                self._life = self._life_total
            return

        self._life -= dt
        if self._life <= 0.0:
            self.active = False
            self._cooldown = self._roll_cd()

    def draw(self, surf: pygame.Surface, camera):
        if not self.active:
            return

        sx, sy = camera.world_to_screen(self.pos.x, self.pos.y)
        cx, cy = int(sx), int(sy)

        # Subtle pulsing rings
        t01 = max(0.0, min(1.0, self._life / max(1e-6, self._life_total)))
        alpha_core = int(210 * (0.55 + 0.45 * (1.0 - t01)))
        alpha_ring = int(140 * (0.55 + 0.45 * (1.0 - t01)))

        pulse = 0.5 + 0.5 * math.sin(self._pulse * 7.2)
        r_core = int(self.radius + 2 * pulse)

        pad = 120
        tmp = pygame.Surface((pad, pad), pygame.SRCALPHA)
        cc = pad // 2

        pygame.draw.circle(tmp, (120, 245, 255, alpha_core), (cc, cc), r_core)
        pygame.draw.circle(tmp, (120, 245, 255, alpha_ring), (cc, cc), int(r_core + 14), 2)
        pygame.draw.circle(tmp, (120, 245, 255, int(alpha_ring * 0.65)), (cc, cc), int(r_core + 30), 2)

        surf.blit(tmp, (cx - cc, cy - cc))
