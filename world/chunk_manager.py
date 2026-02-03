# world/chunk_manager.py
from __future__ import annotations
import pygame
from dataclasses import dataclass

from core.settings import CHUNK_W
from world.zones import ZoneManager


@dataclass
class Chunk:
    index: int
    x0: float

    def draw(self, surf: pygame.Surface, camera, screen_h: int, debug: bool = False, font=None):
        # Minimal: just a subtle vertical delimiter so you "feel" chunks
        x_screen, _ = camera.world_to_screen(self.x0, 0)
        pygame.draw.line(surf, (35, 35, 45), (int(x_screen), 0), (int(x_screen), screen_h), 2)

        if debug and font is not None:
            t = font.render(f"chunk {self.index}", True, (180, 180, 200))
            surf.blit(t, (int(x_screen) + 10, 10))


class ChunkManager:
    """
    Infinite horizontal world in chunks.
    - Keeps a window of chunks around camera.scroll_x
    - Integrates ZoneManager (SAFE/STORM/CLONE zones)
    """
    def __init__(self):
        self.chunks: dict[int, Chunk] = {}
        self.keep_ahead = 6
        self.keep_behind = 2

        self.zones = ZoneManager(chunk_w=CHUNK_W)

    def _ensure_chunk(self, idx: int):
        if idx not in self.chunks:
            self.chunks[idx] = Chunk(index=idx, x0=idx * CHUNK_W)

    def update(self, scroll_x: float):
        current_idx = int(scroll_x // CHUNK_W)

        # generate chunks around camera
        for idx in range(current_idx - self.keep_behind, current_idx + self.keep_ahead + 1):
            if idx >= 0:
                self._ensure_chunk(idx)

        # cull far chunks
        to_del = []
        for idx in self.chunks.keys():
            if idx < current_idx - (self.keep_behind + 2) or idx > current_idx + (self.keep_ahead + 2):
                to_del.append(idx)
        for idx in to_del:
            del self.chunks[idx]

        # zones generation (based on chunk index)
        self.zones.generate_if_needed(current_idx)

    def iter_chunks(self):
        for idx in sorted(self.chunks.keys()):
            yield self.chunks[idx]

    # ---- Zones API ----
    def get_active_zone(self, player_x: float):
        return self.zones.active_zone(player_x)

    def draw_zones(self, surf: pygame.Surface, camera, screen_h: int):
        self.zones.draw(surf, camera, screen_h)
