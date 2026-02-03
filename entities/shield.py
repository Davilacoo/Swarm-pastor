# entities/shield.py
from __future__ import annotations
import math
import pygame


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


class Shield:
    """Arc (semi-circle style) shield in front of the drone.

    - Hold activate to deploy (want_active=True from input).
    - Drains energy while active, recharges while idle.
    - On bullet hit: consumes extra energy + spawns a small flash (notify_hit).
    - If energy reaches 0 -> drops and enters a short lockout.
    """

    def __init__(self):
        self.active = False

        # energy
        self.max_energy = 100.0
        self.energy = self.max_energy
        self.drain_per_s = 28.0
        self.recharge_per_s = 18.0
        self.hit_cost = 10.0  # extra energy cost per absorbed bullet

        # lockout
        self.lockout_s = 0.75
        self.lockout_t = 0.0

        # geometry / placement
        self.radius = 46.0
        self.offset = 44.0
        self.pos = pygame.Vector2(0, 0)

        # base values (used by temporary bonuses)
        self.base_radius = self.radius
        self.base_drain_per_s = self.drain_per_s
        self.base_recharge_per_s = self.recharge_per_s
        self.base_hit_cost = self.hit_cost

        # arc params
        self.aim_dir = pygame.Vector2(1, 0)
        self.arc_deg = 170.0
        self.arc_rad = math.radians(self.arc_deg)

        # visuals
        self.pulse_t = 0.0
        self.hit_flash = 0.0
        self.last_hit_pos = pygame.Vector2(0, 0)

    def energy_ratio(self) -> float:
        return clamp01(self.energy / self.max_energy) if self.max_energy > 0 else 0.0

    def can_activate(self) -> bool:
        return self.lockout_t <= 0.0 and self.energy > 6.0

    def update(self, dt: float, drone_pos: pygame.Vector2, aim_dir: pygame.Vector2, want_active: bool):
        # timers
        if self.lockout_t > 0.0:
            self.lockout_t = max(0.0, self.lockout_t - dt)

        # normalize aim
        if aim_dir.length_squared() < 1e-6:
            aim_dir = pygame.Vector2(1, 0)
        else:
            aim_dir = aim_dir.normalize()

        self.aim_dir = aim_dir
        self.pos = pygame.Vector2(drone_pos) + self.aim_dir * self.offset

        # activation
        self.active = bool(want_active and self.can_activate())

        # energy
        if self.active:
            self.energy -= self.drain_per_s * dt
            if self.energy <= 0.0:
                self.energy = 0.0
                self.active = False
                self.lockout_t = self.lockout_s
        else:
            self.energy = min(self.max_energy, self.energy + self.recharge_per_s * dt)

        # visuals timers
        self.pulse_t += dt
        self.hit_flash = max(0.0, self.hit_flash - dt * 6.0)

    # ----------------- Arc collision -----------------

    def _point_in_arc(self, point: pygame.Vector2, extra_radius: float = 0.0) -> bool:
        v = point - self.pos
        r = self.radius + extra_radius
        if v.length_squared() > r * r:
            return False

        if v.length_squared() < 1e-6:
            return True

        v_dir = v.normalize()
        dot = self.aim_dir.dot(v_dir)
        dot = max(-1.0, min(1.0, dot))
        ang = math.acos(dot)  # [0, pi]
        return ang <= (self.arc_rad * 0.5)

    def notify_hit(self, hit_pos: pygame.Vector2):
        self.last_hit_pos = pygame.Vector2(hit_pos)
        self.hit_flash = 0.18

    def absorb_enemy_bullet(self, bullet_pos: pygame.Vector2, bullet_radius: float) -> bool:
        if not self.active:
            return False

        ok = self._point_in_arc(bullet_pos, extra_radius=bullet_radius)
        if not ok:
            return False

        # consume extra energy per hit
        self.energy -= self.hit_cost
        self.notify_hit(bullet_pos)
        if self.energy <= 0.0:
            self.energy = 0.0
            self.active = False
            self.lockout_t = self.lockout_s
        return True

    # ----------------- Draw -----------------

    def draw(self, surf: pygame.Surface, camera, color=(120, 245, 255)):
        if not self.active and self.hit_flash <= 0.0:
            return

        # convert to screen
        cx, cy = camera.world_to_screen(self.pos.x, self.pos.y)

        # dynamic alpha
        e = self.energy_ratio()
        base_a = int(80 + 140 * e) if self.active else int(60 * self.hit_flash / 0.18)
        base_a = max(0, min(255, base_a))

        # arc params
        half = self.arc_rad * 0.5
        angle = math.atan2(self.aim_dir.y, self.aim_dir.x)
        start = angle - half
        end = angle + half

        r = int(self.radius)
        temp = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)

        # glow + ring
        pygame.draw.arc(temp, (*color, int(base_a * 0.35)), (2, 2, r * 2, r * 2), start, end, 8)
        pygame.draw.arc(temp, (*color, base_a), (2, 2, r * 2, r * 2), start, end, 4)

        surf.blit(temp, (cx - r - 2, cy - r - 2))

        # hit flash at impact point
        if self.hit_flash > 0.0:
            hx, hy = camera.world_to_screen(self.last_hit_pos.x, self.last_hit_pos.y)
            a = int(255 * (self.hit_flash / 0.18))
            fx = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(fx, (255, 255, 255, a), (20, 20), 6)
            pygame.draw.circle(fx, (*color, int(a * 0.7)), (20, 20), 14, 2)
            surf.blit(fx, (hx - 20, hy - 20))
