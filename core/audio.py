# core/audio.py
from __future__ import annotations
from pathlib import Path
import pygame


class Audio:
    """Small audio helper: loads SFX (wav) and optional background music (mp3).

    Place your music at: assets/sfx/music.mp3
    If missing, the game will run silently (no crash).
    """

    def __init__(self, sfx_volume=0.25, music_volume=0.20, autoplay_music=True):
        self.enabled = True
        self.sfx_volume = float(sfx_volume)
        self.music_volume = float(music_volume)
        self.autoplay_music = bool(autoplay_music)

        self.sfx: dict[str, pygame.mixer.Sound | None] = {}
        self.music_path: Path | None = None
        self.music_loaded = False

        self._init_mixer()
        self._load_sfx()
        self._load_music()
        if self.autoplay_music:
            self.play_music()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            print("[WARN] pygame.mixer.init failed:", e)
            self.enabled = False

    def _project_root(self) -> Path:
        return Path(__file__).resolve().parents[1]  # Swarm_Pastor_Phase4_ManualCamera/

    def _load_sfx(self):
        if not self.enabled:
            return

        sfx_dir = self._project_root() / "assets" / "sfx"

        mapping = {
            "player_shoot": sfx_dir / "player_shoot.wav",
            "enemy_shoot":  sfx_dir / "enemy_shoot.wav",
            "hit_enemy":    sfx_dir / "hit_enemy.wav",
            "boid_die":     sfx_dir / "boid_die.wav",
            "explosion":    sfx_dir / "explosion.wav",
            "shield_hit":   sfx_dir / "shield_hit.wav",   # optional
        }

        for k, p in mapping.items():
            try:
                snd = pygame.mixer.Sound(str(p))
                snd.set_volume(self.sfx_volume)
                self.sfx[k] = snd
            except Exception:
                self.sfx[k] = None
                # keep it quiet: these files are optional
                # print(f"[WARN] Missing SFX: {p}")

    def _load_music(self):
        if not self.enabled:
            return
        music = self._project_root() / "assets" / "sfx" / "music.mp3"
        self.music_path = music
        try:
            if music.exists():
                pygame.mixer.music.load(str(music))
                pygame.mixer.music.set_volume(self.music_volume)
                self.music_loaded = True
            else:
                self.music_loaded = False
        except Exception as e:
            print("[WARN] Music load failed:", e)
            self.music_loaded = False

    def play(self, name: str):
        if not self.enabled:
            return
        snd = self.sfx.get(name)
        if snd is not None:
            snd.play()

    def play_music(self):
        if not self.enabled or not self.music_loaded:
            return
        try:
            pygame.mixer.music.set_volume(self.music_volume)
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)  # loop
        except Exception as e:
            print("[WARN] Music play failed:", e)

    def stop_music(self):
        if not self.enabled:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def set_sfx_volume(self, v: float):
        self.sfx_volume = float(max(0.0, min(1.0, v)))
        for snd in self.sfx.values():
            if snd is not None:
                snd.set_volume(self.sfx_volume)

    def set_music_volume(self, v: float):
        self.music_volume = float(max(0.0, min(1.0, v)))
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass
