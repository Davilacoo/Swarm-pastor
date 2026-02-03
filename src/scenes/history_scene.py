from __future__ import annotations

import pygame

from scenes.base_scene import Scene
from systems.background import Starfield
from systems.scoreboard import Scoreboard


class HistoryScene(Scene):
    """Scores history page (reads data/scores.csv)."""

    def __init__(self, app):
        super().__init__(app)
        self.bg = Starfield(app.screen.get_width(), app.screen.get_height(), seed=2042)
        self.t = 0.0
        self.board = Scoreboard()
        self.mode = 0  # 0=top, 1=last

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                from scenes.menu_scene import MenuScene
                self.app.change_scene(MenuScene(self.app))
            elif event.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
                self.mode = 1 - self.mode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            if my >= self.app.screen.get_height() - 60:
                from scenes.menu_scene import MenuScene
                self.app.change_scene(MenuScene(self.app))
            if 210 <= my <= 250:
                self.mode = 0
            if 260 <= my <= 300:
                self.mode = 1

    def update(self, dt: float) -> None:
        self.t += dt

    def _draw_tab(self, screen, text, y, active):
        w = screen.get_width()
        col = (240, 245, 255) if active else (170, 180, 200)
        glow = (120, 245, 255) if active else (70, 90, 110)
        font = pygame.font.SysFont("consolas", 20, bold=True)
        label = font.render(text, True, col)
        rect = label.get_rect(center=(w // 2, y))
        pad_x, pad_y = 16, 8
        box = pygame.Rect(rect.x - pad_x, rect.y - pad_y, rect.w + pad_x * 2, rect.h + pad_y * 2)
        pygame.draw.rect(screen, glow, box, width=2, border_radius=12)
        screen.blit(label, rect)

    def draw(self, screen: pygame.Surface) -> None:
        self.bg.draw(screen, camera_scroll_x=self.t * 45.0, base_bg=(6, 8, 12))

        w, h = screen.get_width(), screen.get_height()
        title_font = pygame.font.SysFont("consolas", 34, bold=True)
        mono = pygame.font.SysFont("consolas", 18)
        small = pygame.font.SysFont("consolas", 16)

        title = title_font.render("HISTORY", True, (240, 245, 255))
        screen.blit(title, (48, 42))

        # tabs
        self._draw_tab(screen, "TOP SCORES", 230, active=(self.mode == 0))
        self._draw_tab(screen, "LAST RUNS", 280, active=(self.mode == 1))

        entries = self.board.top(10) if self.mode == 0 else self.board.last(10)

        # table header
        y0 = 340
        header = mono.render("#   SCORE    TIME     BOIDS   DATE", True, (190, 200, 210))
        screen.blit(header, (60, y0))
        y = y0 + 28

        if not entries:
            msg = mono.render("No runs yet. Play a game first!", True, (170, 180, 200))
            screen.blit(msg, (60, y))
        else:
            for i, e in enumerate(entries, start=1):
                t = int(e.time_s)
                mm, ss = t // 60, t % 60
                date = e.ts
                line = f"{i:>2}  {e.score:>6}   {mm:02d}:{ss:02d}     {e.boids:>3}   {date}"
                s = mono.render(line, True, (220, 225, 235))
                screen.blit(s, (60, y))
                y += 22

        # Back hint
        hint = small.render("TAB to switch | ESC to return", True, (120, 130, 150))
        box = pygame.Rect(0, h - 58, w, 58)
        pygame.draw.rect(screen, (0, 0, 0, 110), box)
        screen.blit(hint, hint.get_rect(center=(w // 2, h - 29)))
