"""Constants. Contract tuning is read from game.contract.json (single source of truth).
Everything below is the Ticket-02 standard numbers that are NOT tuning keys, plus
assumptions marked (A) - see docs/notes/phase-2-spec.md.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_PATH = os.path.join(ROOT, "game.contract.json")


def load_tuning(path=CONTRACT_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["tuning"]


TICK_RATE = 60
GRAVITY = 20.0
JUMP_SPEED = 7.0
STEP_UP = 0.35               # (A) max ground rise walkable per tick (ramps); higher = wall
GROUND_SNAP = 0.35           # (A) stick to ground when walking down a ramp

# motes
PICKUP_DY = 1.5
MOTE_INITIAL = 20
MOTE_CAP = 30
MOTE_SPAWN_EVERY = 240
DROP_RING = (1.5, 2.5)
DROP_TTL = 480

# shades
SHADE_FIRST_SPAWN = 300
SHADE_FIRST_COUNT = 2
SHADE_SPAWN_MIN_DIST = 15.0
SHADE_SPEED_NIGHT3 = 4.5
SHADE_WANDER_SPEED = 2.0     # (A)
SHADE_SPAWNING_TICKS = 60    # (A) harmless + still while "spawning"
DETECT_R = 12.0
LOSE_R = 18.0
HIT_DY = 1.5
RECOIL_M = 2.0
RECOIL_TICKS = 60
EVICT_TICKS = 30
PULSE_CENTER_DY = 0.8
PULSE_PUSH_TICKS = 15
DRAIN_R = 2.0                # T03: drain within 2 m of a weak lantern
DRAIN_BREAK_R = 6.0          # T03: drain -> chase when May within 6 m

# player
FALL_Y = -10.0
RESPAWN_WAIT = 60
CHARM_SPEED = 7.2

# drifters (Gio Lac)
DRIFTER_SPEED = 7.0
DRIFTER_IDLE_SPEED = 2.0
DRIFTER_MAX = 2
DRIFTER_SPAWN_EVERY = 1200
DRIFTER_CHASE_CARRY = 5
DRIFTER_CHASE_R = 15.0
DRIFTER_HIT_R = 1.2
DRIFTER_STEAL = 3
DRIFTER_FLEE_TICKS = 240
DRIFTER_DROP_VANISH = 120
DRIFTER_HOVER = 1.0          # (A) height above ground

# charm (Bua Gio)
CHARM_TICKS = 600
CHARM_RESPAWN = 2700

# wind (night 3)
WIND_EVERY = 1800
WIND_TICKS = 300
WIND_SPEED = 2.0
