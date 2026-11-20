"""Headless runner (Test Contract v1.0).

python3 -m lantern.headless --seed S --night 1 [--scenario f.json] [--inputs f.json]
                            --ticks N --out out.jsonl [--snapshot-every 10]
Exit: 0 ok, 2 bad inputs/scenario/args, 1 other error (message on stderr).
"""
import argparse
import json
import sys

from . import config
from .contract_io import InputError, InputTimeline, load_json, parse_inputs, parse_scenario
from .sim import Game


def dumps(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def run(seed, night, ticks, scenario=None, timeline=None, snapshot_every=10, tuning=None):
    """Run the sim and return the list of JSONL objects."""
    tuning = tuning or config.load_tuning()
    game = Game(seed, tuning, night=night, scenario=scenario)
    timeline = timeline or InputTimeline()
    out = [game.snapshot()]
    for k in range(ticks):
        game.step(timeline.at(k))
        out.extend(game.drain_events())
        if game.tick % snapshot_every == 0:
            out.append(game.snapshot())
        if game.state != "playing":
            break
    out.append({"type": "end", "ticks": game.tick, "state": game.state, "score": game.score})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lantern.headless")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--night", type=int, required=True)
    ap.add_argument("--scenario")
    ap.add_argument("--inputs")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-every", type=int, default=10)
    a = ap.parse_args(argv)  # argparse exits 2 on bad args
    try:
        if a.ticks < 0 or a.snapshot_every < 1:
            raise InputError("--ticks must be >= 0 and --snapshot-every >= 1")
        if a.night != 1:
            raise InputError("unsupported --night %d (this build has night 1)" % a.night)
        tuning = config.load_tuning()
        n = int(tuning["lantern_count_night1"])
        ids = {"L%d" % (i + 1) for i in range(n)}
        scenario = parse_scenario(load_json(a.scenario), ids) if a.scenario else None
        timeline = parse_inputs(load_json(a.inputs)) if a.inputs else None
        lines = run(a.seed, a.night, a.ticks, scenario, timeline, a.snapshot_every, tuning)
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            for obj in lines:
                f.write(dumps(obj) + "\n")
    except InputError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print("error: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
