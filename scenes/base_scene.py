from __future__ import annotations

import pygame


class Scene:
    """Base scene interface."""

    def __init__(self, app):
        self.app = app

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        pass
