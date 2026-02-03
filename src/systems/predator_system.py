# systems/predator_system.py
import random
import pygame

from entities.predator import Predator
from entities.enemy_bullet import EnemyBullet


def circle_hit(pa: pygame.Vector2, pb: pygame.Vector2, ra: float, rb: float) -> bool:
    return (pa - pb).length_squared() <= (ra + rb) * (ra + rb)


class PredatorSystem:
    def __init__(self):
        self.predators = []
        self.enemy_bullets = []
        self.events = []  # ("enemy_shoot"/"boid_die"/"explosion", pos)

        # Director-controlled knobs (defaults)
        self.spawn_timer = 0.0
        self.speed_mult = 1.0  # global speed multiplier (difficulty/events)

        self.spawn_interval = 1.4
        self.max_predators = 15

        # weights (Director will override)
        self.w_grab = 0.38
        self.w_shoot = 0.40
        self.w_kami = 0.22

        # Targeting / isolation
        self.neighbor_r = 60.0

        # GRAB
        self.grab_range = 18.0
        self.escape_back_offset = 260.0
        self.grab_escape_speed = 1.60  # faster escape (more punishing)

        # SHOOT (harder)
        self.shoot_cd = 1    # faster shooting
        self.shoot_range = 520  # more often engages

        # KAMIKAZE (harder)
        self.kami_trigger_density = 6
        self.kami_explode_range = 26.0   # explodes a bit earlier
        self.kami_explode_radius = 52.0  # bigger danger

    # ---------------- Director API ----------------
    def apply_director(self, spawn_interval: float, max_predators: int, weights):
        self.spawn_interval = float(spawn_interval)
        self.max_predators = int(max_predators)
        self.w_grab, self.w_shoot, self.w_kami = weights

    def spawn_many(self, n: int, camera_scroll_x: float, screen_h: int):
        for _ in range(int(n)):
            self.spawn_predator(camera_scroll_x, screen_h)

    # ---------------- Swarm utilities ----------------
    def swarm_center(self, boids):
        if not boids:
            return pygame.Vector2(0, 0)
        s = pygame.Vector2(0, 0)
        for b in boids:
            s += b.pos
        return s / len(boids)

    def neighbor_count(self, boid, boids):
        r2 = self.neighbor_r * self.neighbor_r
        c = 0
        for other in boids:
            if other is boid:
                continue
            if (other.pos - boid.pos).length_squared() <= r2:
                c += 1
        return c
    
    def best_grab_target_for(self, p: Predator, boids):
        if not boids:
            return None

        center = self.swarm_center(boids)
        best = None
        best_score = -1e18

        for b in boids:
            d_pred = (b.pos - p.pos).length()          # cerca del predator = mejor
            d_center = (b.pos - center).length()       # más fuera = mejor
            n = self.neighbor_count(b, boids)          # menos vecinos = mejor

        # Score: castiga targets lejanos, premia aislamiento
            score = (
            -1.35 * d_pred +
            55.0 * (1.0 / (n + 1)) +
            0.35 * d_center
        )

        if score > best_score:
            best_score = score
            best = b

        return best

    def most_isolated_boid(self, boids):
        center = self.swarm_center(boids)
        best = None
        best_score = -1e9
        for b in boids:
            d = (b.pos - center).length()
            n = self.neighbor_count(b, boids)
            score = 1.2 * d + 80.0 * (1.0 / (n + 1))
            if score > best_score:
                best_score = score
                best = b
        return best

    def densest_boid(self, boids):
        best = None
        best_n = -1
        for b in boids:
            n = self.neighbor_count(b, boids)
            if n > best_n:
                best_n = n
                best = b
        return best, best_n

    # ---------------- Spawn ----------------
    def _roll_kind(self) -> str:
        return random.choices(
            [Predator.GRAB, Predator.SHOOT, Predator.KAMIKAZE],
            weights=[self.w_grab, self.w_shoot, self.w_kami]
        )[0]

    def spawn_predator(self, camera_scroll_x, screen_h):
        x = camera_scroll_x + random.uniform(900, 1200)
        y = random.uniform(70, screen_h - 70)
        kind = self._roll_kind()
        p = Predator(x, y, kind)

        # state vars
        p.carrying = None
        p.shoot_timer = random.uniform(0.25, 0.85)  # shoot sooner

        self.predators.append(p)

    # ---------------- Update ----------------
    def update(self, dt, camera_scroll_x, screen_h, boids, drone_pos):
        """Update predators and enemy bullets.

        Goals for "natural" enemies:
        - each predator keeps its own target (no jitter retarget every frame)
        - mild pursuit (predict where boid will be)
        - arrival (slow down when close) to avoid buzzing
        - small individuality for shooters (orbit dir/radius)
        """
        self.events.clear()

        # ---------------- Spawn loop ----------------
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            if len(self.predators) < self.max_predators and len(boids) > 0:
                self.spawn_predator(camera_scroll_x, screen_h)

        # ---------------- Enemy bullets ----------------
        for eb in self.enemy_bullets:
            eb.update(dt)
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive()]

        # bullet -> boid
        for eb in list(self.enemy_bullets):
            for b in list(boids):
                if circle_hit(eb.pos, b.pos, eb.radius, 6):
                    self.events.append(("boid_die", pygame.Vector2(b.pos)))
                    if b in boids:
                        boids.remove(b)
                    if eb in self.enemy_bullets:
                        self.enemy_bullets.remove(eb)
                    break

        # If no boids, drift out
        if not boids:
            for p in self.predators:
                p.integrate(dt)
            return

        # ---------------- Swarm stats ----------------
        center = self.swarm_center(boids)
        isolated = self.most_isolated_boid(boids)
        dense_boid, dense_n = self.densest_boid(boids)

        # ---------------- Movement helpers ----------------
        def pursue_point(boid, lead: float) -> pygame.Vector2:
            # Predict a little into the future (lead in seconds)
            v = getattr(boid, "vel", pygame.Vector2(0, 0))
            return pygame.Vector2(boid.pos) + pygame.Vector2(v) * lead

        def move_arrive(p: Predator, target: pygame.Vector2, speed: float, arrive_r: float):
            to = target - p.pos
            d2 = to.length_squared()
            if d2 < 1e-6:
                return
            d = d2 ** 0.5
            # arrival scaling
            k = 1.0
            if d < arrive_r:
                k = max(0.15, d / arrive_r)
            desired = to.normalize() * (p.max_speed * speed * k * self.speed_mult)
            force = p.steer_towards(desired)
            p.vel += force * dt

        def add_wander(p: Predator, strength: float = 0.18):
            # Small smooth wobble; gives life without making harder
            if not hasattr(p, "_wander_phase"):
                p._wander_phase = random.uniform(0, 10)
                p._wander_sign = random.choice([-1.0, 1.0])
            p._wander_phase += dt * random.uniform(0.8, 1.2)
            if p.vel.length_squared() > 25:
                perp = pygame.Vector2(-p.vel.y, p.vel.x)
                if perp.length_squared() > 1e-6:
                    perp = perp.normalize()
                    p.vel += perp * (p.max_speed * strength) * (0.5 + 0.5 * __import__('math').sin(p._wander_phase)) * p._wander_sign * dt

        # ---------------- Predators logic ----------------
        for p in list(self.predators):
            # despawn behind camera
            if p.pos.x < camera_scroll_x - 520:
                self.predators.remove(p)
                continue

            # retarget timer per predator
            if getattr(p, "retarget_time", 0.0) > 0.0:
                p.retarget_time -= dt

            # -------- GRABBER --------
            if p.kind == Predator.GRAB:
                if p.carrying is None:
                    # Keep target unless time to retarget or invalid
                    if p.retarget_time <= 0.0 or (p.target not in boids):
                        p.target = self.best_grab_target_for(p, boids)
                        p.retarget_time = random.uniform(0.45, 0.95)


                    tgt = p.target
                    # pursuit makes it feel intentional
                    aim = pursue_point(tgt, lead=0.35)
                    move_arrive(p, aim, speed=1.15, arrive_r=90.0)
                    add_wander(p, strength=0.08)
                    p.integrate(dt)

                    if (p.pos - tgt.pos).length() <= self.grab_range:
                        p.carrying = tgt
                        if tgt in boids:
                            boids.remove(tgt)
                else:
                    escape = pygame.Vector2(camera_scroll_x - self.escape_back_offset, p.pos.y)
                    move_arrive(p, escape, speed=self.grab_escape_speed, arrive_r=160.0)
                    p.integrate(dt)

                    if p.pos.x < camera_scroll_x - 180:
                        self.events.append(("boid_die", pygame.Vector2(p.pos)))
                        self.predators.remove(p)

            # -------- SHOOTER --------
            elif p.kind == Predator.SHOOT:
                # Individual orbit personality
                if not hasattr(p, "_orbit_dir"):
                    p._orbit_dir = random.choice([-1.0, 1.0])
                    p._orbit_r = random.uniform(250.0, 340.0)

                # Choose an "interest" target occasionally (isolated boid / drone)
                if p.retarget_time <= 0.0:
                    p.target = isolated if isolated is not None else None
                    p.retarget_time = random.uniform(0.55, 1.15)

                # Desired orbit position around swarm center
                to = center - p.pos
                d = to.length()
                # keep roughly on ring
                if d < p._orbit_r * 0.85:
                    move_arrive(p, p.pos - to.normalize() * 190, speed=0.95, arrive_r=140.0)
                elif d > p._orbit_r * 1.12:
                    move_arrive(p, center, speed=0.98, arrive_r=180.0)
                else:
                    if to.length_squared() > 1e-6:
                        tangent = pygame.Vector2(-to.y, to.x).normalize() * p._orbit_dir
                        move_arrive(p, p.pos + tangent * 220, speed=0.88, arrive_r=180.0)

                # Shoot at target (prefer isolated, else drone)
                aim_point = pygame.Vector2(drone_pos)
                if p.target is not None and p.target in boids:
                    aim_point = pursue_point(p.target, lead=0.18)

                p.shoot_timer -= dt
                if p.shoot_timer <= 0.0 and (aim_point - p.pos).length() <= self.shoot_range:
                    self.enemy_bullets.append(EnemyBullet(p.pos.x, p.pos.y, aim_point - p.pos))
                    self.events.append(("enemy_shoot", pygame.Vector2(p.pos)))
                    p.shoot_timer = self.shoot_cd

                add_wander(p, strength=0.06)
                p.integrate(dt)

            # -------- KAMIKAZE --------
            else:  # Predator.KAMIKAZE
                # Focus dense areas; don't change every frame
                if p.retarget_time <= 0.0:
                    if dense_boid is not None and dense_n >= self.kami_trigger_density:
                        p.target = dense_boid
                    else:
                        p.target = None
                    p.retarget_time = random.uniform(0.35, 0.75)

                if p.target is not None and p.target in boids:
                    target = pygame.Vector2(p.target.pos)
                else:
                    target = center

                move_arrive(p, target, speed=1.35, arrive_r=70.0)
                add_wander(p, strength=0.04)
                p.integrate(dt)

                if (p.pos - target).length() <= self.kami_explode_range:
                    self.events.append(("explosion", pygame.Vector2(p.pos)))

                    r2 = self.kami_explode_radius * self.kami_explode_radius
                    for b in list(boids):
                        if (b.pos - p.pos).length_squared() <= r2:
                            self.events.append(("boid_die", pygame.Vector2(b.pos)))
                            boids.remove(b)

                    if p in self.predators:
                        self.predators.remove(p)
