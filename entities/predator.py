import pygame
import random
import math
from pathlib import Path


class Predator:
    # States
    SEARCH = "SEARCH"
    HUNT = "HUNT"
    ATTACK = "ATTACK"
    EVADE = "EVADE"

    # Kinds
    GRAB = "GRAB"
    SHOOT = "SHOOT"
    KAMIKAZE = "KAMIKAZE"

    # ---- sprite cache (class-level) ----
    _sprites_loaded = False
    _sprite_scaled = {
        GRAB: None,
        SHOOT: None,
        KAMIKAZE: None,
    }
    _visual_width = {
        GRAB: 100,
        SHOOT: 100,
        KAMIKAZE: 100,
    }

    @classmethod
    def _project_root(cls):
        return Path(__file__).resolve().parents[1]

    @classmethod
    def _load_sprites_once(cls):
        if cls._sprites_loaded:
            return
        cls._sprites_loaded = True

        root = cls._project_root()
        mapping = {
            cls.GRAB: root / "assets" / "sprites" / "predator_grab.png",
            cls.SHOOT: root / "assets" / "sprites" / "predator_shoot.png",
            cls.KAMIKAZE: root / "assets" / "sprites" / "predator_kamikaze.png",
        }

        for kind, path in mapping.items():
            try:
                img = pygame.image.load(str(path)).convert_alpha()
                w, h = img.get_size()
                target_w = cls._visual_width[kind]
                scale = target_w / float(w)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                cls._sprite_scaled[kind] = pygame.transform.smoothscale(img, (new_w, new_h))
            except Exception:
                cls._sprite_scaled[kind] = None
                print(f"[WARN] Missing predator sprite: {path}")

    def __init__(self, x, y, kind: str):
        Predator._load_sprites_once()

        self.pos = pygame.Vector2(x, y)
        a = random.uniform(0, 2 * math.pi)
        self.vel = pygame.Vector2(math.cos(a), math.sin(a)) * 90

        self.kind = kind
        self.state = Predator.SEARCH
        self.target = None

        # Base physics
        self.max_speed = 230.0
        self.max_force = 520.0


        self.carrying = None
        self.shoot_timer = 0.0


        # Timers
        self.retarget_time = 0.0
        self.attack_timer = 0.0
        self.shoot_cd = 0.0

        # Hit flash
        self.flash_t = 0.0

        # Stats by kind
        if self.kind == Predator.GRAB:
            self.hp = 2
            self.radius = 12
        elif self.kind == Predator.SHOOT:
            self.hp = 2
            self.radius = 12
        else:  # KAMIKAZE
            self.hp = 1
            self.radius = 13
            self.max_speed = 270.0

    def on_hit(self):
        self.flash_t = 0.10

    def _limit(self, v: pygame.Vector2, m: float) -> pygame.Vector2:
        if v.length_squared() > m * m:
            v = v.copy()
            v.scale_to_length(m)
        return v

    def steer_towards(self, desired_vel: pygame.Vector2) -> pygame.Vector2:
        force = desired_vel - self.vel
        return self._limit(force, self.max_force)

    def integrate(self, dt: float):
        if self.vel.length_squared() > self.max_speed * self.max_speed:
            self.vel.scale_to_length(self.max_speed)
        self.pos += self.vel * dt

        if self.shoot_cd > 0:
            self.shoot_cd -= dt

        if self.flash_t > 0:
            self.flash_t -= dt

    def _get_sprite(self):
        return Predator._sprite_scaled.get(self.kind, None)

    def fallback_color(self):
        if self.kind == Predator.GRAB:
            return (255, 110, 110)
        if self.kind == Predator.SHOOT:
            return (255, 180, 110)
        return (200, 120, 255)

    def draw(self, screen, camera, debug=False):
        x, y = camera.world_to_screen(self.pos.x, self.pos.y)

        spr = self._get_sprite()
        if spr is not None:
            if self.vel.length_squared() > 3:
                angle = -self.vel.angle_to(pygame.Vector2(1, 0))
                img = pygame.transform.rotozoom(spr, angle, 1.0)
            else:
                img = spr
            r = img.get_rect(center=(int(x), int(y)))
            screen.blit(img, r)

            if debug:
                pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), self.radius, 1)
        else:
            pygame.draw.circle(screen, self.fallback_color(), (int(x), int(y)), self.radius)
            pygame.draw.circle(screen, (20, 20, 20), (int(x), int(y)), self.radius, 2)

        # hit flash ring (works for sprites too)
        if self.flash_t > 0:
            pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), self.radius + 3, 2)

        if debug:
            font = pygame.font.SysFont("consolas", 14)
            label = font.render(f"{self.kind}:{self.state}", True, (240, 220, 220))
            screen.blit(label, (int(x) + 12, int(y) - 12))
    

    def move_towards(self, target_pos: pygame.Vector2, speed: float, dt: float):

        to = target_pos - self.pos
        if to.length_squared() <= 1e-6:
            return

        desired = to.normalize() * (self.max_speed * speed)
        force = self.steer_towards(desired)
        self.vel += force * dt

