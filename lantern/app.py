"""Entry point for the windowed game.

  python -m lantern.app                                   play (menu -> 3 nights)
  python -m lantern.app --export-leaderboard out.json     export top 10 (no window)
  python -m lantern.app --bench --seed 42 --duration 30 --out bench.json
  python -m lantern.app --screenshot shot.png [--night N] capture one frame (docs)
"""
import argparse
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lantern.app")
    ap.add_argument("--export-leaderboard", metavar="OUT")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", default="bench.json")
    ap.add_argument("--screenshot", metavar="PNG")
    ap.add_argument("--night", type=int, default=1)
    ap.add_argument("--autoplay", action="store_true", help="bot input (for screenshots/demo)")
    ap.add_argument("--record", metavar="PREFIX", help="save PNG frames at 30 fps (demo video)")
    ap.add_argument("--record-seconds", type=float, default=20.0)
    ap.add_argument("--overview", action="store_true", help="high camera over the island (docs)")
    ap.add_argument("--ui", choices=["menu", "settings", "keys", "leaderboard", "name", "pause"],
                    help="open a UI screen (use with --screenshot)")
    a = ap.parse_args(argv)
    if a.export_leaderboard:
        from .storage import export_leaderboard
        export_leaderboard(a.export_leaderboard)
        return 0
    from . import client  # imports ursina only when a window is needed
    return client.run(a)


if __name__ == "__main__":
    sys.exit(main())
