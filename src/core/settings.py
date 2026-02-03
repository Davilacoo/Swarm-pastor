# --- Window ---
SCREEN_W = 1200
SCREEN_H = 700
FPS = 60

BG_COLOR = (8, 8, 16)

# --- Camera ---
# Where the drone is kept on screen (in pixels)
CAMERA_ANCHOR_X = 360

# --- World / chunks ---
CHUNK_W = 600
CHUNK_H = SCREEN_H
LOAD_RADIUS = 2  # chunks loaded to the left/right of the current one

# --- Drone ---
DRONE_SPEED = 320.0  # player-controlled, no auto-forward

# --- Swarm follow (relative to drone) ---
SWARM_COUNT = 45
SWARM_FOLLOW_OFFSET_X = 220   # anchor in front of the drone (negative -> behind)
SWARM_FOLLOW_OFFSET_Y = 0

# --- Boids tuning defaults ---
BOID_MAX_SPEED = 185.0
BOID_MAX_FORCE = 360.0

# --- Phase 7.3: Boids = Power ---
POWER_RADIUS = 140            # boids within this radius count as "with me"
POWER_MAX_COUNT = 18          # cap for scaling
POWER_MIN_RATE = 0.14         # worst cooldown (few boids)
POWER_MAX_RATE = 0.06         # best cooldown (many boids)

# thresholds for perks (based on "close boids" count)
POWER_TIER1 = 7               # unlock slight recoil reduction / better feel
POWER_TIER2 = 14              # unlock double-shot
POWER_TIER3 = 18              # unlock piercing (hit 2 enemies)



# --- Swarm leash (game over if you abandon the swarm) ---
SWARM_LEASH_DIST = 420.0  # max distance to the closest boid
SWARM_LEASH_GRACE = 2.5   # seconds allowed beyond leash before game over

# --- Progression caps ---
MAX_BOIDS = 120  # hard cap for swarm size (keeps perf + balance)
