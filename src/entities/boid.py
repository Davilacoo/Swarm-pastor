import pygame
import random
import math
from pathlib import Path
from core.settings import BOID_MAX_SPEED, BOID_MAX_FORCE


def _limit(vec: pygame.Vector2, m: float) -> pygame.Vector2:
    if vec.length_squared() > m * m:
        v = vec.copy()
        v.scale_to_length(m)
        return v
    return vec


class Boid:
    # --- class-level cache (load ONCE for all boids) ---
    _sprite_scaled = None
    _sprite_loaded = False
    _visual_width = 50  # <<< cambia esto si los quieres más grandes (ej: 18, 22)

    @classmethod
    def _load_sprite_once(cls):
        if cls._sprite_loaded:
            return
        cls._sprite_loaded = True

        project_root = Path(__file__).resolve().parents[1]
        img_path = project_root / "assets" / "sprites" / "boid.png"

        try:
            img = pygame.image.load(str(img_path)).convert_alpha()

            # scale keeping aspect ratio by width
            w, h = img.get_size()
            scale = cls._visual_width / float(w)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            cls._sprite_scaled = pygame.transform.smoothscale(img, (new_w, new_h))
        except Exception:
            cls._sprite_scaled = None

    def __init__(self, x, y):
        Boid._load_sprite_once()

        self.pos = pygame.Vector2(x, y)

        angle = random.uniform(0, 2 * math.pi)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(40, 90)
        self.acc = pygame.Vector2(0, 0)

        self.max_speed = BOID_MAX_SPEED
        self.max_force = BOID_MAX_FORCE

        # fallback drawing radius (if no sprite)
        self.radius = 4

        # wander noise
        self.noise_phase = random.uniform(0, 2 * math.pi)

    def apply_force(self, f: pygame.Vector2):
        self.acc += f

    def integrate(self, dt: float):
        self.vel += self.acc * dt
        if self.vel.length_squared() > self.max_speed * self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        self.pos += self.vel * dt
        self.acc.update(0, 0)

    def clamp_world_y(self, y_min, y_max):
        if self.pos.y < y_min:
            self.pos.y = y_min
            self.vel.y *= -0.6
        elif self.pos.y > y_max:
            self.pos.y = y_max
            self.vel.y *= -0.6

    def draw(self, screen, camera, debug=False):
        x, y = camera.world_to_screen(self.pos.x, self.pos.y)

        spr = Boid._sprite_scaled
        if spr is not None:
            # OPTIONAL: rotate to face velocity
            if self.vel.length_squared() > 2:
                angle = -self.vel.angle_to(pygame.Vector2(1, 0))
                img = pygame.transform.rotozoom(spr, angle, 1.0)
            else:
                img = spr

            r = img.get_rect(center=(int(x), int(y)))
            screen.blit(img, r)
        else:
            pygame.draw.circle(screen, (230, 230, 255), (int(x), int(y)), self.radius)

        if debug and self.vel.length_squared() > 0:
            v = self.vel.normalize()
            pygame.draw.line(screen, (100, 220, 120), (x, y), (x + v.x * 12, y + v.y * 12), 2)
