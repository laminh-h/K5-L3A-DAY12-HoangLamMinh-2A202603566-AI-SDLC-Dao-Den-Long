"""Constants. Contract tuning is read from game.contract.json (single source of truth)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_PATH = os.path.join(ROOT, "game.contract.json")


def load_tuning(path=CONTRACT_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["tuning"]


# --- Values NOT in the contract (documented in docs/notes/phase-1-assumptions.md) ---
TICK_RATE = 60
ISLAND_RADIUS = 40.0          # player is clamped inside (fall_enabled = false)
LANTERN_RING_RADIUS = 25.0    # L1..L5 on a ring, L1 at (0,0,25), 72 deg apart
GRAVITY = 20.0                # m/s^2 (jump is visual/feel only; distances are XZ)
JUMP_SPEED = 7.0              # m/s
INITIAL_MOTES = 30
MAX_MOTES = 30
MOTE_RESPAWN_S = 3.0          # one new mote every 3 s while below MAX_MOTES
MOTE_MIN_R = 3.0
MOTE_MAX_R = 38.0
INITIAL_SHADES = 2
MAX_SHADES = 5
SHADE_SPAWN_S = 30.0          # one new shade every 30 s while below MAX_SHADES
SHADE_SPAWN_R = 36.0
