"""Ticket-04 (Contract v1.3): bench scene, soak, leaderboard, settings - logic parts."""
import datetime
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

from lantern import bench_scene, config, storage
from lantern.soak import run_soak


class BenchScene(unittest.TestCase):
    def test_scene_contents(self):
        g = bench_scene.make_bench_game(42)
        self.assertEqual(len(g.shades), 200)
        self.assertTrue(all(s["state"] == "wander" for s in g.shades))
        self.assertEqual(len(g.motes), 100)
        lit = [(l["id"], l["fuel"] // 60) for l in g.lanterns if l["lit"]]
        self.assertEqual(lit, [("L1", 100), ("L2", 100), ("L3", 100)])
        self.assertEqual(g.p["pos"], [0.0, 0.0, 0.0])

    def test_bench_disables_damage_pickup_fuel_spawn_end(self):
        g = bench_scene.make_bench_game(42)
        g.motes.append({"id": "MX", "pos": [0.0, 0.0, 0.0], "kind": "random", "ttl": None,
                        "born": -1, "point": None})
        for _ in range(60 * 30):
            g.step({"move": [0, 0], "cam_yaw_deg": 0})
        self.assertEqual(g.state, "playing")
        self.assertEqual(g.p["flames"], 3)
        self.assertEqual(g.p["carried"], 0)
        self.assertEqual(len(g.shades), 200)
        self.assertEqual(len(g.motes), 101)
        self.assertEqual([l["fuel"] for l in g.lanterns if l["lit"]], [6000] * 3)
        self.assertTrue(all(s["state"] == "wander" for s in g.shades))
        names = {e["name"] for e in g.drain_events()}
        self.assertFalse(names & {"player_hit", "mote_picked", "shade_spawned", "game_over"})

    def test_bench_deterministic_positions(self):
        a, b = bench_scene.bench_scenario(42), bench_scene.bench_scenario(42)
        self.assertEqual(a, b)
        self.assertTrue(all(math.hypot(p[0], p[2]) <= 38 for p in a["motes"]))

    def test_camera_orbit(self):
        self.assertEqual(bench_scene.camera_pose(0), (30.0, 15.0, 0.0))
        x, y, z = bench_scene.camera_pose(3.75)  # quarter lap -> +Z (CCW from above)
        self.assertAlmostEqual(x, 0, places=6)
        self.assertAlmostEqual(z, 30, places=6)

    def test_frame_stats_definitions(self):
        dts = [10.0] * 99 + [40.0]
        s = bench_scene.frame_stats(dts)
        self.assertEqual(s["frames"], 100)
        self.assertEqual(s["avg_fps"], round(1000 * 100 / 1030, 1))
        self.assertEqual(s["p1_low_fps"], 25.0)  # k = 1 -> worst = 40 ms
        self.assertEqual(s["frame_ms_p95"], 10.0)


class Soak(unittest.TestCase):
    def test_soak_runs_cycle_and_reports(self):
        r = run_soak(7, 3)
        self.assertEqual(r["nights"], 3)
        self.assertEqual(r["crashes"], 0)
        self.assertEqual(len(r["results"]), 3)
        self.assertTrue(set(r["results"]) <= {"won", "lost"})
        for k in ("mem_start_mb", "mem_end_mb", "duration_s"):
            self.assertIn(k, r)

    def test_soak_deterministic_results(self):
        self.assertEqual(run_soak(11, 3)["results"], run_soak(11, 3)["results"])


class Leaderboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["DDL_HOME"] = self.tmp

    def tearDown(self):
        os.environ.pop("DDL_HOME", None)

    def test_name_rules(self):
        for ok in ("abc", "May_01", "A" * 12, "Mây", "Đăng"):
            self.assertTrue(storage.valid_name(ok), ok)
        for bad in ("ab", "A" * 13, "a b", "x-y", ""):
            self.assertFalse(storage.valid_name(bad), bad)
        with self.assertRaises(ValueError):
            storage.add_score("a!", 1, 0, 1)

    def test_top10_sort_and_tie_order(self):
        base = datetime.datetime(2026, 11, 20, 10, 0, tzinfo=datetime.timezone.utc)
        for i in range(12):
            storage.add_score("p%02d" % i, 100 * (i % 4), 1, 7,
                              now=base + datetime.timedelta(minutes=i))
        e = storage.load_leaderboard()
        self.assertEqual(len(e), 10)
        self.assertEqual([x["score"] for x in e], [300, 300, 300, 200, 200, 200, 100, 100, 100, 0])
        self.assertEqual([x["name"] for x in e[:3]], ["p03", "p07", "p11"])  # earlier first
        self.assertEqual(set(e[0]), {"name", "score", "nights_won", "achieved_at", "seed"})
        self.assertIn("+00:00", e[0]["achieved_at"])

    def test_persist_and_export_cli(self):
        storage.add_score("Linh", 500, 2, 9)
        out = os.path.join(self.tmp, "lb.json")
        env = dict(os.environ, DDL_HOME=self.tmp)
        r = subprocess.run([sys.executable, "-m", "lantern.app", "--export-leaderboard", out],
                           cwd=config.ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual([x["name"] for x in data["entries"]], ["Linh"])


class Settings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["DDL_HOME"] = self.tmp

    def tearDown(self):
        os.environ.pop("DDL_HOME", None)

    def test_defaults_cover_all_actions(self):
        s = storage.load_settings()
        self.assertEqual(set(s["keys"]), set(storage.ACTIONS))
        self.assertEqual(storage.key_conflicts(s["keys"]), {})

    def test_conflict_detection_reset_persist(self):
        s = storage.load_settings()
        s["keys"]["jump"] = "e"
        self.assertEqual(storage.key_conflicts(s["keys"]), {"e": ["jump", "interact"]})
        s["volume"] = 0.2
        storage.save_settings(s)
        s2 = storage.load_settings()
        self.assertEqual((s2["keys"]["jump"], s2["volume"]), ("e", 0.2))
        storage.reset_keys(s2)
        self.assertEqual(s2["keys"], storage.DEFAULT_KEYS)


class ContractV13(unittest.TestCase):
    def test_contract_fields(self):
        with open(config.CONTRACT_PATH, encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.3")
        self.assertTrue(c["bench_cmd"] and c["soak_cmd"])


if __name__ == "__main__":
    unittest.main()
