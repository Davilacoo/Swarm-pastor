# systems/director.py
import random


class DifficultyDirector:
    def __init__(self):
        # difficulty in [0,1]
        self.D = 0.22  # empieza un poco más alto que antes

        # timers
        self.time_no_loss = 0.0
        self.time_since_loss = 999.0

        # pacing (waves)
        self.wave_timer = 0.0
        self.next_wave_in = 6.5  # más pronto

    def notify_boid_lost(self):
        self.time_no_loss = 0.0
        self.time_since_loss = 0.0
        # forgiveness, but not too much (avoid going trivial)
        self.D = max(0.08, self.D - 0.10)

    def update(self, dt, boids_alive, boids_close, predators_alive):
        self.time_since_loss += dt
        self.time_no_loss += dt
        self.wave_timer += dt

        # --- performance score P in [0,1] ---
        close_score = min(1.0, boids_close / 14.0)       # 14 close boids is "good"
        streak_score = min(1.0, self.time_no_loss / 14.0)  # faster ramp

        # crowd penalty: only if it's REALLY crowded
        crowd_penalty = 1.0
        if predators_alive >= 11:
            crowd_penalty = 0.70
        elif predators_alive >= 9:
            crowd_penalty = 0.82

        # low boids => reduce difficulty a bit
        alive_factor = 1.0
        if boids_alive <= 6:
            alive_factor = 0.55
        elif boids_alive <= 10:
            alive_factor = 0.78

        P = (0.60 * close_score + 0.40 * streak_score) * crowd_penalty * alive_factor

        # --- update D smoothly toward P ---
        # rises steadily, falls faster (for forgiveness)
        if P > self.D:
            self.D += (P - self.D) * min(1.0, 0.85 * dt)
        else:
            self.D += (P - self.D) * min(1.0, 1.65 * dt)

        self.D = max(0.05, min(0.98, self.D))

    # ---- knobs applied to PredatorSystem ----
    def spawn_interval(self):
        # more pressure base: ~1.55..0.50
        return 1.55 - 1.05 * self.D

    def max_predators(self):
        # 7..16
        return int(7 + 9 * self.D)

    def type_weights(self):
        # more SHOOT/KAMI earlier
        w_grab = 0.40 - 0.18 * self.D
        w_shoot = 0.38 + 0.10 * self.D
        w_kami = 0.22 + 0.08 * self.D
        # small safety normalization (not strictly needed but nice)
        s = w_grab + w_shoot + w_kami
        return (w_grab / s, w_shoot / s, w_kami / s)

    def should_trigger_wave(self, dt):
        if self.wave_timer < self.next_wave_in:
            return False

        self.wave_timer = 0.0
        # harder => more frequent
        self.next_wave_in = random.uniform(5.5, 8.0) - 2.6 * self.D
        self.next_wave_in = max(2.6, self.next_wave_in)

        # harder => more probable
        chance = 0.30 + 0.45 * self.D
        return random.random() < chance

    def wave_size(self):
        # 3..5 (sometimes feels like "events")
        return 3 + int(3 * self.D)
