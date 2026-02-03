from __future__ import annotations

import pygame

from scenes.base_scene import Scene
from core.game import GameWorld


class GameScene(Scene):
    """Gameplay scene.

    Wraps the old core/game.py loop into a scene-friendly interface.
    """

    def __init__(self, app):
        super().__init__(app)
        self.world = GameWorld(screen=app.screen, font=pygame.font.SysFont("consolas", 18))

    def handle_event(self, event: pygame.event.Event) -> None:
        # let the world handle debug toggles etc.
        action = self.world.handle_event(event)
        if action == "restart":
            self.world = GameWorld(screen=self.app.screen, font=pygame.font.SysFont("consolas", 18))
        elif action == "quit_to_menu":
            # local import to avoid cyclic dependency
            from scenes.menu_scene import MenuScene

            self.app.change_scene(MenuScene(self.app))
        elif action == "quit":
            self.app.quit()

    def update(self, dt: float) -> None:
        self.world.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        self.world.draw()
