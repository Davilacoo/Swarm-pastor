from __future__ import annotations

import pygame

from scenes.base_scene import Scene
from scenes.game_scene import GameScene
from scenes.tutorial_scene import TutorialScene
from scenes.history_scene import HistoryScene
from systems.background import Starfield


class MenuScene(Scene):
    """Main menu (clean + sci-fi)."""

    def __init__(self, app):
        super().__init__(app)
        self.bg = Starfield(app.screen.get_width(), app.screen.get_height(), seed=2026)
        self.t = 0.0
        self.sel = 0  # 0=play, 1=tutorial, 2=history, 3=quit

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % 4
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % 4
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.sel == 0:
                    self.app.change_scene(GameScene(self.app))
                elif self.sel == 1:
                    self.app.change_scene(TutorialScene(self.app))
                elif self.sel == 2:
                    self.app.change_scene(HistoryScene(self.app))
                else:
                    self.app.quit()
            elif event.key == pygame.K_ESCAPE:
                self.app.quit()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            # simple hitboxes
            if 300 <= my <= 340:
                self.app.change_scene(GameScene(self.app))
            if 348 <= my <= 388:
                self.app.change_scene(TutorialScene(self.app))
            if 396 <= my <= 436:
                self.app.change_scene(HistoryScene(self.app))
            if 444 <= my <= 484:
                self.app.quit()

    def update(self, dt: float) -> None:
        self.t += dt

    def _draw_button(self, screen, text, y, active=False):
        w = screen.get_width()
        col = (235, 240, 245) if active else (170, 180, 200)
        glow = (120, 245, 255) if active else (70, 90, 110)

        label = self.app.font.render(text, True, col)
        rect = label.get_rect(center=(w // 2, y))

        pad_x, pad_y = 18, 10
        box = pygame.Rect(rect.x - pad_x, rect.y - pad_y, rect.w + pad_x * 2, rect.h + pad_y * 2)

        # glow frame
        pygame.draw.rect(screen, glow, box, width=2, border_radius=12)
        if active:
            a = int(70 + 60 * (0.5 + 0.5 * __import__('math').sin(self.t * 6.0)))
            glow_s = pygame.Surface((box.w + 30, box.h + 30), pygame.SRCALPHA)
            pygame.draw.rect(glow_s, (120, 245, 255, a), glow_s.get_rect(), width=0, border_radius=18)
            screen.blit(glow_s, (box.x - 15, box.y - 15), special_flags=pygame.BLEND_RGBA_ADD)

        screen.blit(label, rect)

    def draw(self, screen: pygame.Surface) -> None:
        self.bg.draw(screen, camera_scroll_x=self.t * 60.0, base_bg=(6, 8, 12))

        w, h = screen.get_width(), screen.get_height()

        # Title
        title_font = pygame.font.SysFont("consolas", 44, bold=True)
        sub_font = pygame.font.SysFont("consolas", 18)

        title = title_font.render("SWARM PASTOR", True, (240, 245, 255))
        sub = sub_font.render("Protect the swarm. Control the chaos.", True, (170, 180, 200))

        screen.blit(title, title.get_rect(center=(w // 2, 170)))
        screen.blit(sub, sub.get_rect(center=(w // 2, 215)))

        # Buttons
        self._draw_button(screen, "PLAY", 320, active=(self.sel == 0))
        self._draw_button(screen, "TUTORIAL", 368, active=(self.sel == 1))
        self._draw_button(screen, "HISTORY", 416, active=(self.sel == 2))
        self._draw_button(screen, "QUIT", 464, active=(self.sel == 3))

        # Footer
