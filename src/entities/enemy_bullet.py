import pygame


class EnemyBullet:
    def __init__(self, x, y, direction: pygame.Vector2):
        self.pos = pygame.Vector2(x, y)
        self.vel = direction.normalize() * 420.0
        self.radius = 4
        self.ttl = 2.0  # seconds

    def update(self, dt: float):
        self.pos += self.vel * dt
        self.ttl -= dt

    def alive(self):
        return self.ttl > 0

    def draw(self, screen, camera):
        x, y = camera.world_to_screen(self.pos.x, self.pos.y)
        pygame.draw.circle(screen, (255, 220, 130), (int(x), int(y)), self.radius)
        pygame.draw.circle(screen, (25, 25, 25), (int(x), int(y)), self.radius, 1)
