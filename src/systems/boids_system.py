# systems/boids_system.py
from __future__ import annotations
import random
import pygame


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class BoidsSystem:
    """
    Boids steering:
      - cohesion
      - alignment
      - separation
      - goal (anchor seeking)
      - optional: avoid drone a bit (pressure)
      - mood mods:
          cohesion/align/sep/goal multipliers
          speed multiplier
          jitter
          PANIC flee from last threat position
    """

    def __init__(self, boids):
        self.boids = boids
        self.debug = False

        # neighborhood
        self.neighbor_radius = 70.0
        self.separation_radius = 26.0

        # base speeds/forces
        self.base_max_speed = 140.0
        self.max_force = 260.0

        # weights (tweakable)
        self.w_cohesion = 0.70
        self.w_alignment = 0.55
        self.w_separation = 1.05
        self.w_goal = 0.85
        self.w_bounds = 0.90

        # "player interaction" / pressure
        self.w_drone_avoid = 0.0  # set >0 if you want boids to avoid drone strongly

        # mood mods (set externally)
        self.mood_mods = None

    def set_mood_mods(self, mods: dict):
        self.mood_mods = mods

    # -------- Steering helpers --------
    def _limit(self, v: pygame.Vector2, max_len: float) -> pygame.Vector2:
        if v.length_squared() > max_len * max_len:
            return v.normalize() * max_len
        return v

    def _seek(self, boid, target: pygame.Vector2, max_speed: float) -> pygame.Vector2:
        desired = target - boid.pos
        if desired.length_squared() <= 1e-6:
            return pygame.Vector2()
        desired = desired.normalize() * max_speed
        steer = desired - boid.vel
        return self._limit(steer, self.max_force)

    def _flee(self, boid, danger: pygame.Vector2, max_speed: float) -> pygame.Vector2:
        desired = boid.pos - danger
        if desired.length_squared() <= 1e-6:
            return pygame.Vector2()
        desired = desired.normalize() * max_speed
        steer = desired - boid.vel
        return self._limit(steer, self.max_force)

    # -------- Main update --------
    def update(self, dt: float, drone_pos: pygame.Vector2, drone_vel: pygame.Vector2,
               anchor: pygame.Vector2, world_y_min: float, world_y_max: float):

        if not self.boids:
            return

        mods = self.mood_mods or {}
        coh_m = mods.get("cohesion", 1.0)
        ali_m = mods.get("alignment", 1.0)
        sep_m = mods.get("separation", 1.0)
        goal_m = mods.get("goal", 1.0)
        spd_m = mods.get("speed", 1.0)
        jitter = mods.get("jitter", 0.0)
        state = mods.get("state", "CALM")
        threat_pos = mods.get("threat_pos", None)
        threat_recent = mods.get("threat_recent", False)

        nR2 = self.neighbor_radius * self.neighbor_radius
        sR2 = self.separation_radius * self.separation_radius

        for b in self.boids:
            # base max_speed can be per boid; here we override each frame
            max_speed = self.base_max_speed * spd_m

            # neighbors
            center = pygame.Vector2()
            avg_vel = pygame.Vector2()
            sep = pygame.Vector2()
            count = 0

            for other in self.boids:
                if other is b:
                    continue
                d = other.pos - b.pos
                d2 = d.length_squared()
                if d2 <= nR2:
                    center += other.pos
                    avg_vel += other.vel
                    count += 1
                    if d2 <= sR2 and d2 > 1e-6:
                        sep -= d.normalize() / max(1e-6, (d.length() / self.separation_radius))

            force = pygame.Vector2()

            if count > 0:
                center /= count
                avg_vel /= count

                # cohesion: go toward local center
                cohesion_force = self._seek(b, center, max_speed)
                # alignment: match velocity
                alignment_force = avg_vel - b.vel
                alignment_force = self._limit(alignment_force, self.max_force)
                # separation: push away
                separation_force = self._limit(sep * max_speed, self.max_force)

                force += cohesion_force * (self.w_cohesion * coh_m)
                force += alignment_force * (self.w_alignment * ali_m)
                force += separation_force * (self.w_separation * sep_m)

            # goal seek (anchor)
            force += self._seek(b, anchor, max_speed) * (self.w_goal * goal_m)

            # optional: avoid drone slightly
            if self.w_drone_avoid > 0.0:
                away = self._flee(b, drone_pos, max_speed)
                force += away * self.w_drone_avoid

            # PANIC: flee from last threat
            if state == "PANIC" and threat_pos is not None and threat_recent:
                force += self._flee(b, threat_pos, max_speed) * 1.25

            # jitter: tiny random steering (bigger in panic)
            if jitter > 0.0:
                rnd = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                force += rnd * (55.0 * jitter)

            # bounds (keep within vertical playfield)
            if b.pos.y < world_y_min + 10:
                force += pygame.Vector2(0, 140) * self.w_bounds
            elif b.pos.y > world_y_max - 10:
                force += pygame.Vector2(0, -140) * self.w_bounds

            # integrate
            b.vel += self._limit(force, self.max_force) * dt
            b.vel = self._limit(b.vel, max_speed)
            b.pos += b.vel * dt
