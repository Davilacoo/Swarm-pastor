# systems/particles.py
import random
import pygame


class Particle:
    __slots__ = ("pos", "vel", "ttl", "radius", "color", "drag")

    def __init__(self, pos, vel, ttl, radius, color, drag=0.0):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.ttl = float(ttl)
        self.radius = float(radius)
        self.color = color
        self.drag = float(drag)

    def update(self, dt: float):
        self.ttl -= dt
        if self.drag > 0:
            self.vel *= max(0.0, 1.0 - self.drag * dt)
        self.pos += self.vel * dt

    def alive(self) -> bool:
        return self.ttl > 0.0
    
    def spawn_muzzle(self, pos, direction):
        base = pygame.Vector2(direction)
        if base.length_squared() > 0:
            base = base.normalize()
        else:
            base = pygame.Vector2(1, 0)

    # short bright burst
        for _ in range(8):
            v = base.rotate(random.uniform(-20, 20)) * random.uniform(120, 260)
            ttl = random.uniform(0.06, 0.12)
            r = random.uniform(1.8, 3.2)
            col = (255, 245, 210)
            self.particles.append(Particle(pos, v, ttl, r, col, drag=6.0))



class ParticleSystem:
    def __init__(self):
        self.particles = []

    # --- Spawners ---
    def spawn_impact(self, pos, direction=None):
        # sparks forward-ish
        base_dir = pygame.Vector2(direction) if direction is not None else pygame.Vector2(1, 0)
        if base_dir.length_squared() > 0:
            base_dir = base_dir.normalize()
        else:
            base_dir = pygame.Vector2(1, 0)

        for _ in range(10):
            ang = random.uniform(-0.7, 0.7)
            v = base_dir.rotate_rad(ang) * random.uniform(140, 260)
            v += pygame.Vector2(random.uniform(-50, 50), random.uniform(-50, 50))
            ttl = random.uniform(0.12, 0.22)
            r = random.uniform(1.4, 2.6)
            col = (255, 220, 160)
            self.particles.append(Particle(pos, v, ttl, r, col, drag=3.5))

    def spawn_boid_death(self, pos):
        for _ in range(18):
            v = pygame.Vector2(random.uniform(-140, 140), random.uniform(-140, 140))
            ttl = random.uniform(0.18, 0.35)
            r = random.uniform(1.4, 2.4)
            col = (230, 230, 255)
            self.particles.append(Particle(pos, v, ttl, r, col, drag=2.0))

    def spawn_explosion(self, pos):
        # core burst
        for _ in range(32):
            v = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
            if v.length_squared() > 0:
                v = v.normalize()
            v *= random.uniform(160, 360)
            ttl = random.uniform(0.25, 0.55)
            r = random.uniform(1.6, 3.2)
            col = (255, 170, 120)
            self.particles.append(Particle(pos, v, ttl, r, col, drag=1.2))

        # blu-ish debris for style
        for _ in range(10):
            v = pygame.Vector2(random.uniform(-220, 220), random.uniform(-220, 220))
            ttl = random.uniform(0.35, 0.70)
            r = random.uniform(1.8, 3.8)
            col = (140, 200, 255)
            self.particles.append(Particle(pos, v, ttl, r, col, drag=0.9))

    # --- Update/draw ---
    def update(self, dt: float):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive()]

    def draw(self, screen, camera):
        for p in self.particles:
            x, y = camera.world_to_screen(p.pos.x, p.pos.y)
            pygame.draw.circle(screen, p.color, (int(x), int(y)), max(1, int(p.radius)))
            
