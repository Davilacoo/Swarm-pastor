# core/camera.py
import pygame


class Camera:
    def __init__(self):
        self.scroll_x = 0.0

        # look-ahead
        self.lead_x = 0.0

        # tuning
        self.anchor_x = 320.0       # where player "wants" to sit when moving forward
        self.back_margin_x = 120.0  # min screen-x for player (avoid disappearing left)
        self.lead_strength = 7.0

        # optional smoothing when moving camera backward
        self.back_follow_strength = 10.0  # higher = snappier when pulling camera back

    def update(self, player_world_x: float, player_vel: pygame.Vector2, dt: float):
        # --- lead (look ahead) ---
        lead_target = max(-120.0, min(220.0, player_vel.x * 0.35))
        self.lead_x += (lead_target - self.lead_x) * min(1.0, self.lead_strength * dt)

        # --- forward anchor: camera advances when player crosses anchor ---
        # screen_x = player_x - scroll_x - lead_x
        screen_x = player_world_x - self.scroll_x - self.lead_x

        # if player goes beyond anchor -> push camera forward (classic feel)
        if screen_x > self.anchor_x:
            self.scroll_x = player_world_x - self.lead_x - self.anchor_x

        # --- back safety: if player is too close to left -> pull camera back ---
        # this prevents disappearing when moving backward
        if screen_x < self.back_margin_x:
            desired_scroll = player_world_x - self.lead_x - self.back_margin_x
            # smooth pull-back (feel natural)
            self.scroll_x += (desired_scroll - self.scroll_x) * min(1.0, self.back_follow_strength * dt)

        if self.scroll_x < 0:
            self.scroll_x = 0.0

    def world_to_screen(self, x, y):
        return x - self.scroll_x - self.lead_x, y

    def screen_to_world(self, x, y):
        return x + self.scroll_x + self.lead_x, y
