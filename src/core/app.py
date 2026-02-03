from __future__ import annotations

import pygame

from core.settings import SCREEN_W, SCREEN_H, FPS
from scenes.menu_scene import MenuScene
from scenes.base_scene import Scene


class App:
    """Minimal App/Scene manager.

    Owns:
      - pygame init
      - window + clock
      - main loop
      - active scene switching
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Swarm Pastor")

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)

        self._running = True
        self.scene: Scene = MenuScene(self)

    def change_scene(self, scene: Scene) -> None:
        self.scene = scene

    def quit(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                    break
                self.scene.handle_event(event)

            if not self._running:
                break

            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
