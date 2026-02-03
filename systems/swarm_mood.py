# systems/swarm_mood.py
import pygame


class SwarmMood:
    """
    Global swarm mood:
    stress in [0,1]
      0..0.33  -> CALM
      0.33..0.66 -> ALERT
      0.66..1 -> PANIC

    Stress increases with nearby threats/explosions/shots,
    decreases when boids are close to drone and no threats.
    """

    CALM = "CALM"
    ALERT = "ALERT"
    PANIC = "PANIC"

    def __init__(self):
        self.stress = 0.12
        self.state = SwarmMood.CALM

        # threat memory
        self.threat_t = 0.0  # seconds since last threat

        # last threat position (for flee direction)
        self.last_threat_pos = pygame.Vector2(0, 0)
        self.last_threat_strength = 0.0

    def add_threat(self, pos: pygame.Vector2, strength: float):
        """Call this when something scary happens."""
        strength = max(0.0, float(strength))
        self.threat_t = 0.0
        self.last_threat_pos = pygame.Vector2(pos)
        self.last_threat_strength = strength

        # immediate stress bump (clamped)
        self.stress = min(1.0, self.stress + 0.08 * strength)

    def update(self, dt: float, drone_pos: pygame.Vector2, boids_close_count: int, zone_effect: float = 0.0):
        """
        zone_effect:
          + => calms faster (SAFE zone)
          - => stresses more / calms slower (STORM zone)
        """
        self.threat_t += dt

        # baseline: calms down over time
        calm_rate = 0.075 + 0.010 * boids_close_count  # more boids close => calmer
        calm_rate += max(0.0, zone_effect) * 0.08

        # if threat was recent, calm slower
        if self.threat_t < 1.5:
            calm_rate *= 0.35

        # storms make calming harder
        if zone_effect < 0:
            calm_rate *= (1.0 + zone_effect)  # e.g. zone_effect=-0.6 => 0.4x

        self.stress = max(0.0, self.stress - calm_rate * dt)

        # update state
        if self.stress < 0.33:
            self.state = SwarmMood.CALM
        elif self.stress < 0.66:
            self.state = SwarmMood.ALERT
        else:
            self.state = SwarmMood.PANIC

    def modifiers(self):
        """
        Returns multipliers for boid behavior.
        We want PANIC to: less cohesion + more separation + more speed + more randomness.
        """
        s = self.stress

        # smooth-ish mapping
        cohesion_mul = 1.0 - 0.65 * s
        align_mul = 1.0 - 0.30 * s
        separation_mul = 1.0 + 1.10 * s
        goal_mul = 1.0 - 0.55 * s

        speed_mul = 1.0 + 0.45 * s
        jitter = 0.0 + 1.0 * s  # for random steering

        return {
            "cohesion": cohesion_mul,
            "alignment": align_mul,
            "separation": separation_mul,
            "goal": goal_mul,
            "speed": speed_mul,
            "jitter": jitter,
            "state": self.state,
            "stress": self.stress,
            "threat_pos": self.last_threat_pos,
            "threat_strength": self.last_threat_strength,
            "threat_recent": self.threat_t < 1.0,
        }
