# entities/bullet.py
import pygame


class Bullet:
    def __init__(self, x, y, direction: pygame.Vector2):
        self.pos = pygame.Vector2(x, y)
        self.prev = pygame.Vector2(x, y)
        self.vel = direction.normalize() * 720.0
        self.radius = 4
        self.ttl = 1.0
        self.alive = True

    def update(self, dt: float):
        self.prev.update(self.pos.x, self.pos.y)
        self.pos += self.vel * dt
        self.ttl -= dt
        if self.ttl <= 0:
            self.alive = False

    def draw(self, screen, camera):
        x1, y1 = camera.world_to_screen(self.prev.x, self.prev.y)
        x2, y2 = camera.world_to_screen(self.pos.x, self.pos.y)

        # tracer line
        pygame.draw.line(screen, (140, 245, 255), (int(x1), int(y1)), (int(x2), int(y2)), 3)
        # bright core
        pygame.draw.circle(screen, (230, 255, 255), (int(x2), int(y2)), self.radius)
        pygame.draw.circle(screen, (20, 30, 40), (int(x2), int(y2)), self.radius, 1)
