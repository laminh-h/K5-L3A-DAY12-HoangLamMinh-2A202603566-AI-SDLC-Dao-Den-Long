"""Soak test (Ticket-04): N nights in one process, nights 1->2->3 cycling, seed+i per night.

python3 -m lantern.soak --seed 7 --nights 10 --out soak.json
Random input from the seed: new move direction every 30 ticks; per tick 5% jump, 3% dash,
2% pulse, 10% interact.
"""
import argparse
import gc
import json
import math
import random
import sys
import time

from . import config
from .maps import NIGHTS
from .memory import rss_mb
from .sim import Game


def play_night(seed, night, tuning):
    g = Game(seed, tuning, night=night)
    rng = random.Random(seed)
    max_ticks = int(round(float(tuning[NIGHTS[night].duration_key]) * 60)) + 1
    move = [0.0, 0.0]
    for k in range(max_ticks):
        if k % 30 == 0:
            a = rng.uniform(0, 2 * math.pi)
            move = [math.cos(a), math.sin(a)]
        inp = {"move": move, "cam_yaw_deg": 0.0, "jump": rng.random() < 0.05,
               "dash": rng.random() < 0.03, "pulse": rng.random() < 0.02,
               "interact": rng.random() < 0.10, "pause": False}
        g.step(inp)
        g.drain_events()
        if k % 10 == 0:
            g.snapshot()  # exercise the output path like headless does
        if g.state in ("won", "lost"):
            break
    return g


def run_soak(seed, nights, tuning=None):
    tuning = tuning or config.load_tuning()
    results, crashes, mem_start = [], 0, None
    t0 = time.perf_counter()
    for i in range(nights):
        night = i % 3 + 1
        g = None
        try:
            if i == 0:
                g = Game(seed + i, tuning, night=night)
                mem_start = rss_mb()  # after the first night is loaded
                del g
            g = play_night(seed + i, night, tuning)
            results.append(g.state)
        except Exception as e:  # noqa: BLE001 - a crash is a result here
            crashes += 1
            results.append("crash")
            print("night %d crashed: %r" % (i + 1, e), file=sys.stderr)
        finally:
            g = None
            gc.collect()  # "reset" between nights
    mem_end = rss_mb()
    r = lambda v: None if v is None else round(v, 1)  # noqa: E731
    return {"nights": nights, "crashes": crashes, "results": results,
            "mem_start_mb": r(mem_start), "mem_end_mb": r(mem_end),
            "duration_s": round(time.perf_counter() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lantern.soak")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = run_soak(a.seed, a.nights)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=2)
        f.write("\n")
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
