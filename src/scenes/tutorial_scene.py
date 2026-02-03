from __future__ import annotations

import pygame

from scenes.base_scene import Scene
from systems.background import Starfield


class TutorialScene(Scene):
    """Tutorial page reachable from the main menu."""

    def __init__(self, app):
        super().__init__(app)
        self.bg = Starfield(app.screen.get_width(), app.screen.get_height(), seed=2031)
        self.t = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            from scenes.menu_scene import MenuScene
            self.app.change_scene(MenuScene(self.app))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # click anywhere bottom hint to go back
            mx, my = pygame.mouse.get_pos()
            if my >= self.app.screen.get_height() - 60:
                from scenes.menu_scene import MenuScene
                self.app.change_scene(MenuScene(self.app))

    def update(self, dt: float) -> None:
        self.t += dt

    def draw(self, screen: pygame.Surface) -> None:
        self.bg.draw(screen, camera_scroll_x=self.t * 50.0, base_bg=(6, 8, 12))

        w, h = screen.get_width(), screen.get_height()
        title_font = pygame.font.SysFont("consolas", 34, bold=True)
        body_font = pygame.font.SysFont("consolas", 18)
        small_font = pygame.font.SysFont("consolas", 16)

        title = title_font.render("TUTORIAL", True, (240, 245, 255))
        screen.blit(title, (48, 42))

        lines = [
            ("Goal", "Keep the swarm alive and score by surviving + killing predators."),
            ("Controls", "WASD to move | Mouse to aim | RMB: shoot | LMB: shield"),
            ("Swarm Power", "The more boids close to you, the stronger your shots become."),
            ("Shield", "Hold LMB to project a shield arc. It consumes energy and blocks bullets."),
            ("Beacon", "Sometimes a beacon appears. If enough boids reach it, you get a big reward."),
            ("Zones", "SAFE boosts morale. STORM increases danger. CLONE can duplicate boids if you hold inside."),
            ("Objective", "Each run has rotating objectives. Completing one gives score + shield energy."),
            ("Tips", "Stay mobile. Regroup often. Use shield to save boids, not just yourself."),
        ]

        y = 110
        for head, desc in lines:
            head_s = body_font.render(head + ":", True, (120, 245, 255))
            desc_s = body_font.render(desc, True, (210, 215, 225))
            screen.blit(head_s, (54, y))
            screen.blit(desc_s, (230, y))
            y += 34

        # Back hint
        hint = small_font.render("ESC / Backspace or click here to return", True, (120, 130, 150))
        box = pygame.Rect(0, h - 58, w, 58)
        pygame.draw.rect(screen, (0, 0, 0, 110), box)
        screen.blit(hint, hint.get_rect(center=(w // 2, h - 29)))
