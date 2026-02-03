# core/game.py
from __future__ import annotations
import random
import pygame

from core.settings import (
    SWARM_LEASH_DIST, SWARM_LEASH_GRACE,
    MAX_BOIDS,
    SCREEN_W, SCREEN_H, FPS, BG_COLOR,
    CHUNK_W,
    SWARM_COUNT, SWARM_FOLLOW_OFFSET_X, SWARM_FOLLOW_OFFSET_Y,
    POWER_RADIUS, POWER_MAX_COUNT,
    POWER_MIN_RATE, POWER_MAX_RATE,
    POWER_TIER1, POWER_TIER2, POWER_TIER3
)

from core.camera import Camera
from world.chunk_manager import ChunkManager

from entities.drone import Drone
from entities.boid import Boid
from entities.bullet import Bullet
from entities.shield import Shield  # <<< NEW

from systems.boids_system import BoidsSystem
from systems.predator_system import PredatorSystem
from systems.director import DifficultyDirector
from systems.background import Starfield
from systems.beacon_system import BeaconSystem
from systems.swarm_power import SwarmPower
from systems.swarm_mood import SwarmMood

from core.audio import Audio
from systems.particles import ParticleSystem
from systems.screenshake import ScreenShake
from systems.scoreboard import Scoreboard

from world.zones import Zone


def circle_hit(pa: pygame.Vector2, pb: pygame.Vector2, ra: float, rb: float) -> bool:
    return (pa - pb).length_squared() <= (ra + rb) * (ra + rb)


class GameWorld:
    """Gameplay state + update/draw.

    Phase 1 refactor:
    - pygame init + main loop moved to core/app.py
    - this class only contains gameplay state and frame methods
    """

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        self.screen = screen
        self.font = font

        self.world_surface = pygame.Surface((SCREEN_W, SCREEN_H)).convert_alpha()

        # procedural background (parallax)
        self.bg = Starfield(SCREEN_W, SCREEN_H)

        self.camera = Camera()
        self.chunks = ChunkManager()

        self.drone = Drone(x=120, y=SCREEN_H * 0.5)

        # swarm
        spawn_x = self.drone.pos.x + 160
        spawn_y = self.drone.pos.y
        self.boids = [
            Boid(
                x=spawn_x + (k % 9) * 10,
                y=spawn_y + (k // 9) * 10
            )
            for k in range(SWARM_COUNT)
        ]
        self.boids_system = BoidsSystem(self.boids)

        # predators
        self.predators = PredatorSystem()

        # bullets
        self.bullets: list[Bullet] = []

        # pacing director (smooth difficulty)
        self.director = DifficultyDirector()

        # beacon (temporary regroup anchor)
        self.beacon = BeaconSystem()
        self.beacon_bonus_ready = True

        # run stats
        self.time_alive = 0.0
        self.score = 0
        self.game_over = False
        self.game_over_reason = ""
        self.leash_t = 0.0
        self._score_written = False
        self.scoreboard = Scoreboard()

        # "Addictive" layer: rotating objectives (lightweight, high replay value)
        self.objective = self._roll_objective()
        self.obj_progress = 0.0
        self.obj_target = float(self.objective.get("target", 1))
        self.obj_done = False
        # Objective bonus (temporary power after completing an objective)
        self.bonus_type = None       # e.g., "RAPID_FIRE", "BOMB_NOVA", "BOID_SURGE", "SHIELD_OVERCHARGE"
        self.bonus_t = 0.0
        self.bonus_label = ""

        # Permanent progression (boids + stats) — grows each completed objective
        self.objectives_completed = 0
        self.score_mult = 1.0
        self.fire_cd_mult = 1.0       # multiplies fire cooldown (lower = faster)
        self.shield_eff_mult = 1.0    # multiplies shield costs (lower = cheaper)
        self.boid_speed_mult = 1.0    # multiplies boid speed via mood mods

        # Difficulty scaling (ramps with objectives)
        self.difficulty_mult = 1.0

        self.kills_this_run = 0
        self.beacon_claims = 0
        self.boids_lost = 0

        # feedback
        self.audio = Audio(sfx_volume=0.25)
        self.particles = ParticleSystem()
        self.shake = ScreenShake()
        self.hitstop_t = 0.0

        # swarm power (7.3)
        self.swarm_power = SwarmPower(radius=POWER_RADIUS, cap_count=POWER_MAX_COUNT)

        # mood
        self.mood = SwarmMood()

        # NEW: Shield
        self.shield = Shield()

        self.show_debug = False

        # balancing for CLONE zone
        self.max_boids = MAX_BOIDS

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Return an action string for the outer App/Scene manager."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit_to_menu"
            if event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
                self.boids_system.debug = self.show_debug
            if self.game_over and event.key == pygame.K_r:
                return "restart"
        return None

    # -------- Objectives (replay value / dynamism) --------
    def _roll_objective(self) -> dict:
        """Pick a simple objective that creates short-term goals.

        Important: cheap to implement, but adds replayability.
        """
        # Slightly bias early game toward survival/regroup
        options = [
            {"type": "HUNT", "target": random.randint(5, 8)},
            {"type": "SURVIVE", "target": random.randint(35, 55)},
            {"type": "CLOSE", "target": random.randint(12, 18), "threshold": random.randint(9, 12)},
            # Bring the swarm to a temporary beacon (clear progress feedback in HUD)
            {"type": "BEACON", "target": 12},
        ]
        obj = random.choice(options)

        t = obj["type"]
        if t == "HUNT":
            obj["text"] = f"Kill {obj['target']} predators"
        elif t == "SURVIVE":
            obj["text"] = f"Survive {obj['target']}s"
        elif t == "CLOSE":
            thr = obj.get("threshold", 10)
            obj["text"] = f"Keep {thr}+ boids close for {obj['target']}s"
        elif t == "BEACON":
            obj["text"] = "Bring 12 boids to the beacon"
        return obj


    def _grant_objective_bonus(self):
        """Grant a short, satisfying power spike after completing an objective."""
        # Choose a bonus. We keep it simple but meaningful.
        bonuses = [
            ("RAPID_FIRE", 6.0, "BONUS: Rapid Fire (6s)"),
            ("BOMB_NOVA", 0.0, "BONUS: Bomb Nova!"),
            ("BOID_SURGE", 0.0, "BONUS: Boid Surge!"),
            ("SHIELD_OVERCHARGE", 6.0, "BONUS: Shield Overcharge (6s)"),
        ]
        btype, dur, label = random.choice(bonuses)
        self.bonus_type = btype
        self.bonus_t = float(dur)
        self.bonus_label = label

        # Immediate effects
        if btype == "BOMB_NOVA":
            # Kill / heavily damage nearby predators instantly
            center = pygame.Vector2(self.drone.pos)
            radius = 260.0
            r2 = radius * radius
            killed = 0
            for pred in list(self.predators.predators):
                if (pred.pos - center).length_squared() <= r2:
                    pred.hp = 0
                    killed += 1
                    self.particles.spawn_explosion(pred.pos)
            # remove dead
            for pred in list(self.predators.predators):
                if pred.hp <= 0 and pred in self.predators.predators:
                    self.predators.predators.remove(pred)
                    self.score += int(50 * self.score_mult)
                    self.kills_this_run += 1
            # Big feedback even if no one was in range
            self.audio.play("explosion")
            self.shake.kick(10.0, 0.18)
            self.particles.spawn_explosion(center)
            self.hitstop_t = 0.060

        elif btype == "BOID_SURGE":
            # Spawn extra boids (permanent) as a big reward
            if len(self.boids) > 0:
                add = min(len(self.boids), max(0, self.max_boids - len(self.boids)))
                for _ in range(add):
                    base = random.choice(self.boids)
                    self.boids.append(Boid(base.pos.x + random.uniform(-18, 18), base.pos.y + random.uniform(-18, 18)))
                self.audio.play("powerup")
                self.shake.kick(7.0, 0.14)
                self.particles.spawn_explosion(self.drone.pos)

        elif btype == "SHIELD_OVERCHARGE":
            # Top up shield and make it more efficient for a few seconds (handled in update)
            self.shield.energy = self.shield.max_energy
            self.audio.play("powerup")
            self.shake.kick(6.0, 0.12)

        elif btype == "RAPID_FIRE":
            # Purely handled in update via cooldown multiplier
            self.audio.play("powerup")
            self.shake.kick(5.0, 0.10)

    def _update_bonus(self, dt: float):
        # Tick duration bonuses
        if self.bonus_t > 0.0:
            self.bonus_t = max(0.0, self.bonus_t - dt)
            if self.bonus_t <= 0.0:
                # End of timed bonus
                self.bonus_type = None
                self.bonus_label = ""


    def _apply_progression_after_objective(self):
        """Increase permanent power each time you complete an objective."""
        self.objectives_completed += 1

        n = self.objectives_completed
        # Score multiplier ramps gently (caps to avoid runaway)
        self.score_mult = min(2.5, 1.0 + 0.12 * n)

        # Fire rate: reduce cooldown (caps at 55% of base)
        self.fire_cd_mult = max(0.55, 1.0 * (0.93 ** n))

        # Shield efficiency: reduce drain/hit cost (caps at 55% of base cost)
        self.shield_eff_mult = max(0.55, 1.0 * (0.92 ** n))
        if hasattr(self, "shield") and self.shield is not None:
            # Use base_* if present, else treat current as base on first call
            if not hasattr(self.shield, "_progression_inited"):
                self.shield._progression_inited = True
                self.shield.base_drain_per_s = getattr(self.shield, "base_drain_per_s", self.shield.drain_per_s)
                self.shield.base_recharge_per_s = getattr(self.shield, "base_recharge_per_s", self.shield.recharge_per_s)
                self.shield.base_hit_cost = getattr(self.shield, "base_hit_cost", self.shield.hit_cost)
            self.shield.drain_per_s = self.shield.base_drain_per_s * self.shield_eff_mult
            self.shield.hit_cost = self.shield.base_hit_cost * self.shield_eff_mult
            # Slightly better recharge as you progress
            self.shield.recharge_per_s = self.shield.base_recharge_per_s * min(1.6, 1.0 + 0.06 * n)

        # Boid speed: small ramp (caps)
        self.boid_speed_mult = min(1.55, 1.0 + 0.04 * n)

        # Boid growth (permanent): add some boids each completion + milestone doubling
        self._award_progression_boids()

        # Increase enemy pressure too (keeps the run frenetic)
        self.difficulty_mult = min(2.6, 1.0 + 0.22 * n)

    def _award_progression_boids(self):
        if len(self.boids) <= 0:
            return
        # Per objective: add a few boids (scales with objectives)
        add_n = 3 + min(10, self.objectives_completed * 2)
        # Milestone: every 4 objectives, double current boids (capped by max_boids)
        if self.objectives_completed % 4 == 0:
            add_n += len(self.boids)
        space = max(0, self.max_boids - len(self.boids))
        add_n = min(add_n, space)
        if add_n <= 0:
            return
        for _ in range(add_n):
            base = random.choice(self.boids)
            self.boids.append(Boid(base.pos.x + random.uniform(-16, 16), base.pos.y + random.uniform(-16, 16)))

    def _complete_objective(self):
        # Reward loop (addictive): instant payoff + visual/audio punch
        self.obj_done = True
        self.score += int(250 * self.score_mult)
        self._apply_progression_after_objective()
        # Grant a big momentary bonus to keep the loop exciting
        self._grant_objective_bonus()
        self.shield.energy = min(self.shield.max_energy, self.shield.energy + 35.0)

        self.audio.play("powerup")
        self.shake.kick(6.0, 0.12)
        self.particles.spawn_explosion(self.drone.pos)

        # Immediately roll the next objective to keep momentum
        self.objective = self._roll_objective()
        self.obj_progress = 0.0
        self.obj_target = float(self.objective.get("target", 1))
        self.obj_done = False


    # -------- Shooting (right click held) --------
    def _shoot_if_pressed(self):
        mb = pygame.mouse.get_pressed()
        if not mb[2]:
            return

        if not self.drone.can_fire():
            return

        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world(mx, my)

        dir_vec = pygame.Vector2(wx - self.drone.pos.x, wy - self.drone.pos.y)
        if dir_vec.length_squared() <= 0.0001:
            return
        dir_vec = dir_vec.normalize()

        close = self.swarm_power.close_count
        tier1 = close >= POWER_TIER1
        tier2 = close >= POWER_TIER2
        tier3 = close >= POWER_TIER3

        spawn = self.drone.pos + dir_vec * 24

        b1 = Bullet(spawn.x, spawn.y, dir_vec)
        if tier3:
            b1.pierce = 2
        self.bullets.append(b1)

        if tier2:
            spread = dir_vec.rotate(random.uniform(-6, 6))
            b2 = Bullet(spawn.x, spawn.y, spread)
            if tier3:
                b2.pierce = 2
            self.bullets.append(b2)

        self.drone.fire()

        # feedback
        self.audio.play("player_shoot")
        if hasattr(self.particles, "spawn_muzzle"):
            self.particles.spawn_muzzle(spawn, dir_vec)
        else:
            self.particles.spawn_impact(spawn, direction=dir_vec)

        recoil = 60.0
        if tier1:
            recoil = 40.0
        self.drone.vel -= dir_vec * recoil
        self.shake.kick(1.0, 0.04)

        # shooting near big swarm stresses them slightly
        if self.swarm_power.close_count >= 10:
            self.mood.add_threat(self.drone.pos, strength=0.25)

    def update(self, dt: float):
        # If game over, keep lightweight visuals
        if self.game_over:
            self.shake.update(dt)
            self.particles.update(dt)
            return

        # drone
        self.drone.update(dt, SCREEN_W, SCREEN_H)

        # camera
        self.camera.update(self.drone.pos.x, self.drone.vel, dt)

        # run timer
        if not self.game_over:
            self.time_alive += dt

        # beacon pacing
        self.beacon.update(dt, self.camera.scroll_x, SCREEN_W, SCREEN_H)

        # chunks + zones generation
        self.chunks.update(self.camera.scroll_x)

        # --- Shield update (LEFT CLICK) ---
        mb = pygame.mouse.get_pressed()
        want_shield = mb[0]

        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world(mx, my)
        aim_dir = pygame.Vector2(wx - self.drone.pos.x, wy - self.drone.pos.y)

        self.shield.update(dt, self.drone.pos, aim_dir, want_active=want_shield)

        # Bonus: shield overcharge (temporary efficiency + bigger arc)
        if self.bonus_type == "SHIELD_OVERCHARGE" and self.bonus_t > 0.0:
            if hasattr(self.shield, "base_drain_per_s"):
                self.shield.drain_per_s = self.shield.base_drain_per_s * 0.35
                self.shield.recharge_per_s = self.shield.base_recharge_per_s * 1.6
                self.shield.hit_cost = self.shield.base_hit_cost * 0.55
                self.shield.radius = self.shield.base_radius + 18.0
        else:
            if hasattr(self.shield, "base_drain_per_s"):
                self.shield.drain_per_s = self.shield.base_drain_per_s
                self.shield.recharge_per_s = self.shield.base_recharge_per_s
                self.shield.hit_cost = self.shield.base_hit_cost
                self.shield.radius = self.shield.base_radius


        # shoot (RIGHT CLICK)
        self._shoot_if_pressed()

        # swarm power
        self.swarm_power.update(dt, self.drone.pos, self.boids)

        # --- Objectives update (adds short-term goals) ---
        ot = self.objective.get("type")
        if ot == "SURVIVE":
            self.obj_progress += dt
            if self.obj_progress >= self.obj_target:
                self._complete_objective()
        elif ot == "CLOSE":
            thr = int(self.objective.get("threshold", 10))
            if self.swarm_power.close_count >= thr:
                self.obj_progress += dt
                if self.obj_progress >= self.obj_target:
                    self._complete_objective()
        elif ot == "BEACON":
            # Progress = how many boids are currently inside beacon radius.
            # This makes the objective readable and prevents the old bug where it
            # instantly showed DONE after the first beacon of the run.
            if self.beacon.active:
                near = 0
                r2 = 56 * 56
                for b in self.boids:
                    if (b.pos - self.beacon.pos).length_squared() <= r2:
                        near += 1
                self.obj_progress = float(near)
                # completion is handled by the beacon bonus block below (near>=12),
                # but keep this as a safe fallback.
                if self.obj_progress >= self.obj_target and self.beacon_bonus_ready:
                    self._complete_objective()
            else:
                self.obj_progress = 0.0

                # objective completion bonuses
        self._update_bonus(dt)

# fire rate from swarm power
        p = self.swarm_power.power01
        fire_cd = POWER_MIN_RATE + (POWER_MAX_RATE - POWER_MIN_RATE) * p
        fire_cd = max(0.02, fire_cd * self.fire_cd_mult)  # permanent progression
        # Bonus: rapid fire temporarily overrides cooldown
        if self.bonus_type == "RAPID_FIRE" and self.bonus_t > 0.0:
            fire_cd = max(0.025, fire_cd * 0.45)

        if hasattr(self.drone, "set_fire_cooldown"):
            self.drone.set_fire_cooldown(fire_cd)
        else:
            self.drone.fire_cooldown = fire_cd

        # --- ZONE EFFECTS (SAFE / STORM / CLONE) ---
        zone = self.chunks.get_active_zone(self.drone.pos.x)

        zone_effect = 0.0
        if zone is not None:
            if zone.kind == Zone.SAFE:
                zone_effect = +1.0
            elif zone.kind == Zone.STORM:
                zone_effect = -0.6
            elif zone.kind == Zone.CLONE:
                zone_effect = 0.0

        # --- MOOD update + apply to boids system ---
        self.mood.update(dt, self.drone.pos, self.swarm_power.close_count, zone_effect=zone_effect)
        mods = self.mood.modifiers()
        mods["speed"] = mods.get("speed", 1.0) * self.boid_speed_mult
        self.boids_system.set_mood_mods(mods)

        # --- BOIDS update (mood-aware) ---
        if self.beacon.active:
            anchor = pygame.Vector2(self.beacon.pos)
        else:
            anchor = pygame.Vector2(
                self.drone.pos.x + SWARM_FOLLOW_OFFSET_X,
                self.drone.pos.y + SWARM_FOLLOW_OFFSET_Y
            )
        self.boids_system.update(dt, self.drone.pos, self.drone.vel, anchor, 20, SCREEN_H - 20)

        # --- Beacon bonus: if many boids reach it, reward + despawn ---
        if self.beacon.active:
            near = 0
            r2 = 56 * 56
            for b in self.boids:
                if (b.pos - self.beacon.pos).length_squared() <= r2:
                    near += 1
            if near >= 12 and self.beacon_bonus_ready:
                # Reward: refill shield energy a bit + score
                self.shield.energy = min(self.shield.max_energy, self.shield.energy + 45.0)
                self.score += int(120 * self.score_mult)
                self.beacon_claims += 1
                if self.objective.get("type") == "BEACON":
                    self._complete_objective()
                self.audio.play("powerup")
                self.shake.kick(7.0, 0.14)
                self.particles.spawn_explosion(self.beacon.pos)
                self.beacon.active = False
                self.beacon_bonus_ready = False
        else:
            self.beacon_bonus_ready = True

        # --- CLONE ZONE logic (hold inside -> duplicate boids) ---
        if zone is not None and zone.kind == Zone.CLONE and not zone.clone_used:
            zone.clone_hold += dt
            if zone.clone_hold >= 1.4 and len(self.boids) >= 10:
                to_add = min(len(self.boids), self.max_boids - len(self.boids))
                if to_add > 0:
                    for _ in range(to_add):
                        base = random.choice(self.boids)
                        nx = base.pos.x + random.uniform(-18, 18)
                        ny = base.pos.y + random.uniform(-18, 18)
                        self.boids.append(Boid(nx, ny))

                    zone.clone_used = True
                    self.audio.play("powerup")
                    self.shake.kick(8.0, 0.14)
                    self.particles.spawn_explosion(self.drone.pos)

        # --- Director (difficulty pacing) ---
        self.director.update(
            dt,
            boids_alive=len(self.boids),
            boids_close=self.swarm_power.close_count,
            predators_alive=len(self.predators.predators),
        )
        base_spawn = self.director.spawn_interval()
        base_maxp = self.director.max_predators()

        # --- Conceptual progression: phases by objectives completed ---
        # We want difficulty to feel like "new threats" rather than pure spawn spam.
        n = self.objectives_completed
        phase = 0
        if n >= 2:
            phase = 1   # introduce shooters more often
        if n >= 4:
            phase = 2   # introduce kamikaze more often
        if n >= 7:
            phase = 3   # occasional mini-waves
        if n >= 10:
            phase = 4   # late pressure, but still readable

        # Spawn pacing: gentle ramp (avoid the old hyper-frenzy)
        # (Higher n -> slightly faster spawns, but never absurd.)
        spawn_interval = max(0.75, base_spawn * (1.00 - 0.04 * n))

        # Population cap: increases slowly with progress
        max_predators = min(22, base_maxp + min(6, n))

        # Enemy mix progression
        # Start mostly GRAB, then add SHOOT, then add KAMI.
        wg, ws, wk = 0.72, 0.22, 0.06
        if phase >= 1:
            ws += 0.08
            wg -= 0.08
        if phase >= 2:
            wk += 0.06
            wg -= 0.06
        if phase >= 3:
            ws += 0.05
            wg -= 0.05
        if phase >= 4:
            wk += 0.04
            wg -= 0.04

        wg = max(0.12, wg)
        ws = max(0.12, ws)
        wk = max(0.06, wk)
        s = wg + ws + wk
        weights = (wg / s, ws / s, wk / s)

        self.predators.apply_director(
            spawn_interval=spawn_interval,
            max_predators=max_predators,
            weights=weights,
        )

        # Global enemy tuning: mild ramp (keeps readability)
        self.predators.speed_mult = min(1.45, 1.0 + 0.03 * n)

        # Make shooter cadence a bit tighter over time (without exponential runaway)
        if not hasattr(self.predators, "_base_shoot_cd"):
            self.predators._base_shoot_cd = getattr(self.predators, "shoot_cd", 0.9)
        self.predators.shoot_cd = max(0.55, self.predators._base_shoot_cd * (1.0 - 0.025 * n))

        # Occasional mini-wave only after midgame (phase 3+), and not too often
        if phase >= 3 and self.director.should_trigger_wave(dt):
            extra = 2 + (1 if phase >= 4 else 0)
            self.predators.spawn_many(self.director.wave_size() + extra, self.camera.scroll_x, SCREEN_H)

# --- Predators update ---
        if zone is not None and zone.kind == Zone.STORM:
            self.predators.shoot_cd = min(self.predators.shoot_cd, 0.62)
            self.predators.max_predators = max(self.predators.max_predators, 12)

        self.predators.update(
        dt=dt,
        camera_scroll_x=self.camera.scroll_x,
        screen_h=SCREEN_H,
        boids=self.boids,
        drone_pos=self.drone.pos
        )


        # --- Swarm leash (don't abandon the flock) ---
        if (not self.game_over) and self.boids:
            # distance to closest boid
            d2_min = None
            for b in self.boids:
                d2 = (b.pos - self.drone.pos).length_squared()
                if d2_min is None or d2 < d2_min:
                    d2_min = d2
            if d2_min is None:
                self.leash_t = 0.0
            else:
                if d2_min > (SWARM_LEASH_DIST * SWARM_LEASH_DIST):
                    self.leash_t += dt
                    if self.leash_t >= SWARM_LEASH_GRACE:
                        self.game_over = True
                        self.game_over_reason = "You abandoned the swarm!"
                else:
                    self.leash_t = max(0.0, self.leash_t - dt * 0.5)

        # --- Shield interactions with enemy bullets ---
        # absorb bullets on shield hit
        for eb in list(self.predators.enemy_bullets):
            if self.shield.absorb_enemy_bullet(eb.pos, eb.radius):
                # feedback
                self.audio.play("shield_hit") if hasattr(self.audio, "play") else None
                self.shake.kick(2.5, 0.06)
                if hasattr(self.particles, "spawn_impact"):
                    self.particles.spawn_impact(self.shield.pos, direction=(eb.pos - self.shield.pos))
                self.predators.enemy_bullets.remove(eb)

        # --- OPTIONAL: Shield body-block predators (makes it feel useful) ---
        if self.shield.active:
            for pred in list(self.predators.predators):
                # if predator touches shield, push it away a bit + stun moment
                if circle_hit(pred.pos, self.shield.pos, pred.radius, self.shield.radius):
                    push = (pred.pos - self.shield.pos)
                    if push.length_squared() > 1e-6:
                        push = push.normalize()
                        pred.vel += push * 220.0  # needs Predator.vel to exist
                    # small feedback
                    self.shake.kick(1.0, 0.03)

        # predators events -> mood + audio
        for ev, pos in self.predators.events:
            if ev == "enemy_shoot":
                self.audio.play("enemy_shoot")
                self.mood.add_threat(pos, strength=0.6)
            elif ev == "boid_die":
                self.audio.play("boid_die")
                self.boids_lost += 1
                self.particles.spawn_boid_death(pos)
                self.shake.kick(3.5, 0.10)
                self.mood.add_threat(pos, strength=1.2)
            elif ev == "explosion":
                self.audio.play("explosion")
                self.particles.spawn_explosion(pos)
                self.shake.kick(9.0, 0.16)
                self.mood.add_threat(pos, strength=1.6)

        # --- player bullets update ---
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if getattr(b, "alive", True)]

        # --- bullet -> predator collision ---
        for bullet in list(self.bullets):
            for pred in list(self.predators.predators):
                if circle_hit(bullet.pos, pred.pos, bullet.radius, pred.radius):
                    pred.hp -= 1

                    self.audio.play("hit_enemy")
                    self.particles.spawn_impact(pred.pos, direction=(pred.pos - bullet.pos))
                    self.shake.kick(3.0, 0.08)
                    self.hitstop_t = 0.030

                    # piercing
                    if hasattr(bullet, "pierce"):
                        bullet.pierce -= 1
                        if bullet.pierce <= 0 and bullet in self.bullets:
                            self.bullets.remove(bullet)
                    else:
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)

                    if pred.hp <= 0 and pred in self.predators.predators:
                        self.particles.spawn_explosion(pred.pos)
                        self.shake.kick(6.0, 0.12)
                        self.predators.predators.remove(pred)
                        self.score += int(50 * self.score_mult)
                        self.kills_this_run += 1
                        if self.objective.get("type") == "HUNT":
                            self.obj_progress += 1
                            if self.obj_progress >= self.obj_target:
                                self._complete_objective()
                    break

        # game over
        if (not self.game_over) and len(self.boids) <= 0:
            self.game_over = True
            self.game_over_reason = "All boids lost!"

        # Always write run history exactly once, for ANY game_over reason
        if self.game_over and (not self._score_written):
            note = f"reason={self.game_over_reason} kills={self.kills_this_run} beacon={self.beacon_claims}"
            self.scoreboard.append(self.score, self.time_alive, len(self.boids), note=note)
            self._score_written = True

# feedback systems
        self.shake.update(dt)
        self.particles.update(dt)

    def draw(self):
        self.bg.draw(self.world_surface, self.camera.scroll_x, base_bg=BG_COLOR)

        # draw zones overlay FIRST
        self.chunks.draw_zones(self.world_surface, self.camera, SCREEN_H)

        # chunks (IMPORTANT: pass SCREEN_H because your Chunk.draw needs it)
        for chunk in self.chunks.iter_chunks():
            chunk.draw(self.world_surface, self.camera, SCREEN_H, debug=self.show_debug, font=self.font)

        # beacon (regroup event)
        self.beacon.draw(self.world_surface, self.camera)


        # aura from swarm power
        power = self.swarm_power.power01
        if power > 0.02:
            x, y = self.camera.world_to_screen(self.drone.pos.x, self.drone.pos.y)
            r = int(26 + 38 * power)
            alpha = int(35 + 90 * power)
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (120, 245, 255, alpha), (r, r), r)
            self.world_surface.blit(aura, (int(x - r), int(y - r)))

        # boids
        for b in self.boids:
            b.draw(self.world_surface, self.camera, debug=self.show_debug)

        # predators
        for p in self.predators.predators:
            p.draw(self.world_surface, self.camera, debug=self.show_debug)

        # enemy bullets
        for eb in self.predators.enemy_bullets:
            eb.draw(self.world_surface, self.camera)

        # player bullets
        for bullet in self.bullets:
            bullet.draw(self.world_surface, self.camera)

        # particles
        self.particles.draw(self.world_surface, self.camera)

        # drone
        self.drone.draw(self.world_surface, self.camera)

        # shield on top (so it is visible)
        self.shield.draw(self.world_surface, self.camera)

        # shake
        ox, oy = self.shake.offset()
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.world_surface, (int(ox), int(oy)))

        # HUD (no shake)
        self._draw_hud()

    def _draw_hud(self):
        # Minimal HUD (top-left)
        boids_alive = len(self.boids)
        shield01 = self.shield.energy_ratio()
        power01 = self.swarm_power.power01

        # text lines
        t = int(self.time_alive)
        mm = t // 60
        ss = t % 60

        lines = [
            f"BOIDS  {boids_alive}",
            f"TIME   {mm:02d}:{ss:02d}",
            f"SCORE  {self.score}",
        ]

        def _wrap(s: str, max_len: int = 34):
            s = s.strip()
            if len(s) <= max_len:
                return [s]
            out, cur = [], ""
            for w in s.split():
                if not cur:
                    cur = w
                elif len(cur) + 1 + len(w) <= max_len:
                    cur += " " + w
                else:
                    out.append(cur)
                    cur = w
            if cur:
                out.append(cur)
            return out[:2]  # HUD compact

        # objective line (adds “one more run” feeling) — readable + no fake DONE
        try:
            ot = self.objective.get("type")
            text = self.objective.get("text", "")
            prog_str = ""
            if ot in ("SURVIVE", "CLOSE"):
                prog = min(self.obj_progress, self.obj_target)
                prog_str = f"[{prog:.0f}/{self.obj_target:.0f}]"
            elif ot == "HUNT":
                prog = min(self.obj_progress, self.obj_target)
                prog_str = f"[{int(prog)}/{int(self.obj_target)}]"
            elif ot == "BEACON":
                # show live progress; if no beacon is currently active, say so
                if self.beacon.active:
                    prog = min(self.obj_progress, self.obj_target)
                    prog_str = f"[{int(prog)}/{int(self.obj_target)}]"
                else:
                    prog_str = "[WAIT]"

            wrapped = _wrap(text)
            if wrapped:
                lines.append(f"OBJ    {wrapped[0]}  {prog_str}".rstrip())
                if len(wrapped) > 1:
                    lines.append(f"       {wrapped[1]}")
        except Exception:
            pass

        # bonus line
        if self.bonus_type:
            if self.bonus_t > 0.0:
                lines.append(f"BONUS  {self.bonus_label} [{self.bonus_t:.0f}s]")
            else:
                lines.append(f"BONUS  {self.bonus_label}")

        y = 10
        for line in lines:
            s = self.font.render(line, True, (235, 240, 245))
            self.screen.blit(s, (12, y))
            y += 22

        # Power + Shield bars (minimal)
        bar_w = 170
        bar_h = 8
        x0 = 12
        y0 = y + 8

        # power bar
        pygame.draw.rect(self.screen, (40, 44, 52), (x0, y0, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(self.screen, (120, 245, 255), (x0, y0, int(bar_w * power01), bar_h), border_radius=6)
        self.screen.blit(self.font.render("POWER", True, (190, 200, 210)), (x0 + bar_w + 10, y0 - 6))

        # shield bar
        y1 = y0 + 16
        pygame.draw.rect(self.screen, (40, 44, 52), (x0, y1, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(self.screen, (160, 210, 255), (x0, y1, int(bar_w * shield01), bar_h), border_radius=6)
        self.screen.blit(self.font.render("SHIELD", True, (190, 200, 210)), (x0 + bar_w + 10, y1 - 6))

        if self.show_debug:
            current_chunk = int(self.camera.scroll_x // CHUNK_W)
            zone = self.chunks.get_active_zone(self.drone.pos.x)
            zone_name = zone.kind if zone is not None else "NONE"
            dbg = self.font.render(
                f"chunk={current_chunk} zone={zone_name} close={self.swarm_power.close_count} D={self.director.D:.2f} pred={len(self.predators.predators)}",
                True, (180, 180, 180)
            )
            self.screen.blit(dbg, (12, SCREEN_H - 24))

        if self.game_over:
            # overlay
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))

            title = self.font.render("GAME OVER", True, (255, 255, 255))
            hint = self.font.render("Press R to restart   |   ESC to menu", True, (220, 220, 220))
            self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 18)))
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 16)))
