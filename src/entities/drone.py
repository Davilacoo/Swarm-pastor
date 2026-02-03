# entities/drone.py
import pygame
from pathlib import Path


class Drone:
    def __init__(self, x: float, y: float):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)

        # Movement feel
        self.max_speed = 420.0
        self.accel = 1650.0
        self.friction = 11.5  # bigger = more braking

        # Shooting (kept for later)
        self.fire_cooldown = 0.10  # default; will be overwritten by swarm power
        self.base_fire_cooldown = 0.10

        self._fire_t = 0.0

        # Visuals
        self.size = pygame.Vector2(54, 32)  # fallback rect size

        self.sprite = None
        self._load_sprite()

        # tilt
        self.tilt_deg = 0.0
        self.tilt_speed = 16.0  # how fast tilt follows

    def set_fire_cooldown(self, cd: float):
        self.fire_cooldown = float(max(0.02, cd))


    def _load_sprite(self):
        # Optional: assets/sprites/drone.png
        try:
            root = Path(__file__).resolve().parents[1]
            path = root / "assets" / "sprites" / "drone.png"
            img = pygame.image.load(str(path)).convert_alpha()
            # scale keeping aspect ratio (not squashed)
            target_w = 70
            w, h = img.get_size()
            scale = target_w / float(w)
            self.sprite = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        except Exception:
            self.sprite = None

    def can_fire(self) -> bool:
        return self._fire_t <= 0.0

    def fire(self):
        self._fire_t = self.fire_cooldown

    def update(self, dt: float, screen_w: int, screen_h: int):
        keys = pygame.key.get_pressed()

        inp = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            inp.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            inp.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            inp.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            inp.x += 1

        if inp.length_squared() > 0:
            inp = inp.normalize()
            self.vel += inp * self.accel * dt
        else:
            # friction toward 0
            self.vel -= self.vel * min(1.0, self.friction * dt)

        # clamp speed
        if self.vel.length_squared() > self.max_speed * self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        self.pos += self.vel * dt

        # clamp Y (world vertical bounds)
        margin = 22
        self.pos.y = max(margin, min(screen_h - margin, self.pos.y))

        # update fire timer
        if self._fire_t > 0:
            self._fire_t -= dt

        # tilt: based on lateral speed (x) + a bit of y
        target_tilt = -self.vel.y * 0.02 + self.vel.x * 0.01
        target_tilt = max(-18.0, min(18.0, target_tilt))
        self.tilt_deg += (target_tilt - self.tilt_deg) * min(1.0, self.tilt_speed * dt)

    def draw(self, screen, camera):
        x, y = camera.world_to_screen(self.pos.x, self.pos.y)

        if self.sprite is not None:
            img = pygame.transform.rotozoom(self.sprite, self.tilt_deg, 1.0)
            r = img.get_rect(center=(int(x), int(y)))
            screen.blit(img, r)
        else:
            # fallback: a tilted rect
            rect = pygame.Rect(0, 0, int(self.size.x), int(self.size.y))
            rect.center = (int(x), int(y))
            pygame.draw.rect(screen, (120, 235, 255), rect, border_radius=7)
            pygame.draw.rect(screen, (20, 30, 40), rect, 2, border_radius=7)
