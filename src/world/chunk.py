# world/chunk.py
import pygame


class Chunk:
    def __init__(self, chunk_id: int, x0: float, bg_surface: pygame.Surface):
        self.chunk_id = chunk_id
        self.x0 = x0  # world x start of chunk
        self.bg = bg_surface  # preloaded & scaled surface (CHUNK_W x SCREEN_H)

        # decor points (si ya lo tenías)
        self.points = []

    def draw(self, screen, camera, screen_h: int, debug=False, font=None):
        # draw background image aligned to the chunk start
        x_screen, _ = camera.world_to_screen(self.x0, 0)

        # bottom align (looks nicer if the art has ground/platform at the bottom)
        y_screen = screen_h - self.bg.get_height()
        screen.blit(self.bg, (int(x_screen), int(y_screen)))

        if debug and font is not None:
            label = font.render(f"chunk {self.chunk_id}", True, (220, 220, 255))
            screen.blit(label, (int(x_screen) + 10, 10))
