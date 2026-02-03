# systems/background.py
from __future__ import annotations
import random
import pygame


class Starfield:
    """Lightweight parallax background (procedural, no assets needed).

    Draw order:
      - soft nebula blobs (very subtle)
      - 3 star layers (parallax)
    """

    def __init__(self, w: int, h: int, seed: int = 1337):
        self.w, self.h = w, h
        rnd = random.Random(seed)

        # Pre-render nebula layer
        self.nebula = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(28):
            x = rnd.randrange(0, w)
            y = rnd.randrange(0, h)
            r = rnd.randrange(80, 210)
            a = rnd.randrange(10, 26)
            col = (rnd.randrange(30, 90), rnd.randrange(40, 120), rnd.randrange(70, 160), a)
            pygame.draw.circle(self.nebula, col, (x, y), r)

        # Stars: (x, y, radius, alpha)
        def make_layer(n: int, rmin: int, rmax: int, amin: int, amax: int):
            layer = []
            for _ in range(n):
                layer.append((rnd.random() * w, rnd.random() * h,
                              rnd.randint(rmin, rmax), rnd.randint(amin, amax)))
            return layer

        self.layers = [
            (make_layer(90, 1, 1, 40, 90), 0.12),
            (make_layer(65, 1, 2, 60, 120), 0.22),
            (make_layer(45, 2, 3, 80, 160), 0.34),
        ]

        # Cached star surfaces for speed
        self._star_surfs = {}
        for r in (1, 2, 3):
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, 255), (r + 1, r + 1), r)
            self._star_surfs[r] = s

    def draw(self, surf: pygame.Surface, camera_scroll_x: float, base_bg=(6, 8, 12)):
        surf.fill(base_bg)

        # nebula scrolls very slowly
        nx = int(-(camera_scroll_x * 0.04) % self.w)
        surf.blit(self.nebula, (nx, 0))
        surf.blit(self.nebula, (nx - self.w, 0))

        # stars with parallax
        for stars, par in self.layers:
            offset = -(camera_scroll_x * par)
            for x, y, r, a in stars:
                sx = (x + offset) % self.w
                star = self._star_surfs[r].copy()
                star.set_alpha(a)
                surf.blit(star, (int(sx), int(y)))
