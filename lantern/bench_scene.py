"""Ticket-04 standard benchmark scene (pure logic, no rendering)."""
import math
import random

from . import config
from .sim import Game

BENCH_SHADES = 200
BENCH_MOTES = 100
ISLAND_R = 38.0  # inside Night 1 island (r = 40)


def _spread(rng, n):
    """Uniform area distribution on the island disc."""
    pts = []
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = ISLAND_R * math.sqrt(rng.random())
        pts.append([r * math.cos(a), 0.0, r * math.sin(a)])
    return pts


def bench_scenario(seed=42):
    rng = random.Random(seed)
    return {
        "player": {"pos": [0, 0, 0]},
        "random_motes": False, "random_shades": False, "random_drifters": False,
        "wind_enabled": False,
        "shades": [{"id": "S%d" % (i + 1), "pos": p, "state": "wander"}
                   for i, p in enumerate(_spread(rng, BENCH_SHADES))],
        "motes": _spread(rng, BENCH_MOTES),
        "lanterns": [{"id": "L%d" % i, "lit": True, "fuel": 100} for i in (1, 2, 3)],
        "time_left_s": 240,  # end conditions are off in bench; clock just stops at 0
    }


def make_bench_game(seed=42, tuning=None):
    return Game(seed, tuning or config.load_tuning(), night=1,
                scenario=bench_scenario(seed), bench=True)


def camera_pose(t_s):
    """Camera orbit: radius 30, Y=15, starts at (30,15,0), CCW from above, 15 s per lap."""
    a = 2 * math.pi * (t_s / 15.0)
    return (30 * math.cos(a), 15.0, 30 * math.sin(a))


def frame_stats(dts_ms):
    n = len(dts_ms)
    if n == 0:
        return {"frames": 0, "avg_fps": 0.0, "p1_low_fps": 0.0, "frame_ms_p95": 0.0}
    k = max(1, math.ceil(0.01 * n))
    worst = sorted(dts_ms, reverse=True)[:k]
    srt = sorted(dts_ms)
    idx = min(n - 1, max(0, math.ceil(0.95 * n) - 1))  # nearest-rank P95
    return {"frames": n,
            "avg_fps": round(1000.0 * n / sum(dts_ms), 1),
            "p1_low_fps": round(1000.0 / (sum(worst) / k), 1),
            "frame_ms_p95": round(srt[idx], 2)}
