# world/zones.py
import random
import pygame


class Zone:
    SAFE = "SAFE"
    STORM = "STORM"
    CLONE = "CLONE"

    def __init__(self, x0: float, width: float, kind: str):
        self.rect = pygame.Rect(int(x0), 0, int(width), 99999)
        self.kind = kind

        # clone zone internal
        self.clone_used = False
        self.clone_hold = 0.0  # seconds player stayed inside

    def contains_x(self, x: float) -> bool:
        return self.rect.left <= x <= self.rect.right

    def draw(self, surf, camera, screen_h):
        # very simple overlay, no assets needed
        x, _ = camera.world_to_screen(self.rect.left, 0)
        w = self.rect.width

        overlay = pygame.Surface((w, screen_h), pygame.SRCALPHA)

        if self.kind == Zone.SAFE:
            overlay.fill((40, 190, 120, 30))
        elif self.kind == Zone.STORM:
            overlay.fill((190, 60, 60, 28))
        else:
            overlay.fill((70, 120, 220, 30))

        surf.blit(overlay, (int(x), 0))


class ZoneManager:
    """
    Spawns one zone every N chunks.
    """
    def __init__(self, chunk_w: int):
        self.chunk_w = chunk_w
        self.zones = []

        self.every_n_chunks = 4
        self.zone_width_chunks = 1.2  # ~1 chunk wide

        # mix
        self.w_safe = 0.40
        self.w_storm = 0.35
        self.w_clone = 0.25

    def generate_if_needed(self, chunk_index: int):
        """
        Ensure zones exist up to this chunk index.
        We'll generate a zone at chunk indices: every_n_chunks * k + 2
        """
        target_k = chunk_index // self.every_n_chunks
        desired_count = max(0, target_k)

        while len(self.zones) < desired_count:
            k = len(self.zones) + 1
            base_chunk = self.every_n_chunks * k + 2
            x0 = base_chunk * self.chunk_w
            w = int(self.zone_width_chunks * self.chunk_w)

            kind = random.choices(
                [Zone.SAFE, Zone.STORM, Zone.CLONE],
                weights=[self.w_safe, self.w_storm, self.w_clone]
            )[0]

            self.zones.append(Zone(x0, w, kind))

    def active_zone(self, player_x: float):
        for z in self.zones:
            if z.contains_x(player_x):
                return z
        return None

    def draw(self, surf, camera, screen_h):
        for z in self.zones:
            # only draw near camera (cheap cull)
            if z.rect.right >= camera.scroll_x - 100 and z.rect.left <= camera.scroll_x + 1400:
                z.draw(surf, camera, screen_h)
