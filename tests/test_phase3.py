"""Ticket-03 'Den can dau' (Contract v1.2). Expected values derived from the ticket text."""
import math
import unittest

from lantern import config
from lantern.contract_io import parse_inputs
from lantern.headless import run

from tests.test_rules import events, frames, sc, snap_at, snaps

T = config.load_tuning()


def lantern(snap, lid):
    return [l for l in snap["lanterns"] if l["id"] == lid][0]


def shade(snap, sid):
    return [s for s in snap["shades"] if s["id"] == sid][0]


class Fuel(unittest.TestCase):
    def test_light_sets_fuel_100_and_decays_1_per_s(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 10})
        out = run(1, 1, 61, s, frames({"tick": 0, "interact": True}), snapshot_every=1)
        self.assertEqual(lantern(snap_at(out, 1), "L1")["fuel"], 100.0)
        self.assertEqual(lantern(snap_at(out, 61), "L1")["fuel"], 99.0)
        self.assertTrue(lantern(snap_at(out, 1), "L1")["ever_lit"])

    def test_burn_out_event_and_state(self):
        s = sc(lanterns=[{"id": "L1", "lit": True, "fuel": 0.5}])
        out = run(1, 1, 40, s, snapshot_every=1)
        e = events(out, "lantern_out")[0]
        self.assertEqual((e["tick"], e["data"]), (30, {"lantern_id": "L1"}))
        l = lantern(snap_at(out, 30), "L1")
        self.assertEqual((l["lit"], l["fuel"], l["deposited"], l["ever_lit"]), (False, 0, 0, True))

    def test_scenario_lit_defaults_fuel_100(self):
        out = run(1, 1, 0, sc(lanterns=[{"id": "L2", "lit": True}]))
        self.assertEqual(lantern(snaps(out)[0], "L2")["fuel"], 100.0)
        self.assertEqual(lantern(snaps(out)[0], "L1")["fuel"], 0)

    def test_refuel_formula(self):
        # fuel 63.5 -> missing 36.5 -> ceil(3.65) = 4 motes -> min(100, 63.5+40) = 100
        s = sc(player={"pos": [0, 0, 24], "carried": 6},
               lanterns=[{"id": "L1", "lit": True, "fuel": 63.5 + 1 / 60}])
        out = run(1, 1, 1, s, frames({"tick": 0, "interact": True}), snapshot_every=1)
        self.assertEqual(events(out, "refuel")[0]["data"],
                         {"lantern_id": "L1", "amount": 4, "fuel": 100.0})
        self.assertEqual(snap_at(out, 1)["player"]["carried"], 2)
        self.assertEqual(out[-1]["score"], 4 * 5)

    def test_refuel_limited_by_carried(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 2},
               lanterns=[{"id": "L1", "lit": True, "fuel": 20 + 1 / 60}])
        out = run(1, 1, 1, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "refuel")[0]["data"]["fuel"], 40.0)

    def test_full_lantern_not_selectable(self):
        # L1 full (lit this tick of setup -> decays 1/60 in step 2, so it is NOT full any more);
        # use fuel 100 + 1/60 so it is exactly 100 after the decay of step 2.
        s = sc(player={"pos": [0, 0, 24], "carried": 5},
               lanterns=[{"id": "L1", "lit": True, "fuel": 100 + 1 / 60},
                         {"id": "L2", "pos": [0, 0, 22.5]}])
        out = run(1, 1, 1, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "refuel"), [])
        self.assertEqual(events(out, "deposit")[0]["data"]["lantern_id"], "L2")

    def test_relight_costs_5_and_scores_40(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 7}, lanterns=[{"id": "L1", "ever_lit": True}])
        out = run(1, 1, 1, s, frames({"tick": 0, "interact": True}), snapshot_every=1)
        self.assertEqual(events(out, "deposit")[0]["data"], {"lantern_id": "L1", "amount": 5,
                                                             "deposited": 5})
        self.assertEqual(events(out, "lantern_lit")[0]["data"], {"lantern_id": "L1", "relight": True})
        l = lantern(snap_at(out, 1), "L1")
        self.assertEqual((l["relit_count"], l["fuel"]), (1, 100.0))
        self.assertEqual(out[-1]["score"], 5 * 5 + 40)

    def test_never_lit_still_costs_10(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 7})
        out = run(1, 1, 1, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "lantern_lit"), [])


class LowFuelAndDrain(unittest.TestCase):
    def test_low_fuel_loses_safe_zone(self):
        # fuel 29 -> no safe zone -> chasing shade reaches the player standing at the lantern
        s = sc(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "lit": True, "fuel": 29}],
               shades=[{"id": "A", "pos": [0, 0, 15]}])
        out = run(1, 1, 200, s)
        self.assertEqual(len(events(out, "player_hit")), 1)

    def test_exactly_30_keeps_safe_zone(self):
        # 30 + 200 ticks of decay -> stays >= 30 for the whole test
        s = sc(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "lit": True, "fuel": 30 + 200 / 60}],
               shades=[{"id": "A", "pos": [0, 0, 15]}])
        out = run(1, 1, 200, s)
        self.assertEqual(events(out, "player_hit"), [])

    def test_wander_goes_to_weak_lantern_and_drains(self):
        # player far away (on the other side); weak L1 at (0,0,25); shade 10 m from it
        s = sc(player={"pos": [0, 0, -30]}, lanterns=[{"id": "L1", "lit": True, "fuel": 25}],
               shades=[{"id": "A", "pos": [0, 0, 15]}])
        out = run(1, 1, 400, s, snapshot_every=1)
        states = [shade(x, "A")["state"] for x in snaps(out)]
        self.assertIn("drain", states)
        k = states.index("drain")
        # 8 m at 2 m/s = 240 ticks
        self.assertAlmostEqual(k, 240, delta=2)
        fd = events(out, "fuel_drain")
        self.assertEqual(fd[0]["tick"] - k, 60)
        self.assertEqual(fd[0]["data"]["shade_id"], "A")
        # while draining: 1 + 5 per second
        f0, f1 = lantern(snap_at(out, k + 10), "L1")["fuel"], lantern(snap_at(out, k + 70), "L1")["fuel"]
        self.assertAlmostEqual(f0 - f1, 6.0, places=1)
        self.assertEqual(shade(snap_at(out, k + 10), "A")["pos"], shade(snap_at(out, k + 70), "A")["pos"])

    def test_drain_until_out_then_wander(self):
        s = sc(player={"pos": [0, 0, -30]}, lanterns=[{"id": "L1", "lit": True, "fuel": 3}],
               shades=[{"id": "A", "pos": [0, 0, 23.5], "state": "drain", "target_lantern_id": "L1"}])
        out = run(1, 1, 60, s, snapshot_every=1)
        e = events(out, "lantern_out")[0]
        self.assertEqual(e["tick"], 30)  # 3 fuel / (6 per s) = 0.5 s
        self.assertEqual(shade(snap_at(out, 30), "A")["state"], "wander")

    def test_drains_stack(self):
        s = sc(player={"pos": [0, 0, -30]}, lanterns=[{"id": "L1", "lit": True, "fuel": 20}],
               shades=[{"id": "A", "pos": [1, 0, 25], "state": "drain", "target_lantern_id": "L1"},
                       {"id": "B", "pos": [-1, 0, 25], "state": "drain", "target_lantern_id": "L1"}])
        out = run(1, 1, 60, s)
        self.assertAlmostEqual(lantern(snaps(out)[-1], "L1")["fuel"], 20 - 11, places=1)

    def test_drain_to_chase_within_6(self):
        s = sc(player={"pos": [0, 0, 19.5]}, lanterns=[{"id": "L1", "lit": True, "fuel": 20}],
               shades=[{"id": "A", "pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"}])
        out = run(1, 1, 1, s, snapshot_every=1)
        self.assertEqual(shade(snap_at(out, 1), "A")["state"], "chase")

    def test_pulse_draining_shade_scores_15(self):
        s = sc(player={"pos": [0, 0, 27.5], "carried": 5},
               lanterns=[{"id": "L1", "lit": True, "fuel": 20}],
               shades=[{"id": "A", "pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"},
                       {"id": "B", "pos": [3, 0, 27.5]}])
        # player 3.5 m from the drainer -> it would switch to chase in step 8, but pulse is step 7
        out = run(1, 1, 1, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        self.assertEqual(events(out, "pulse")[0]["data"]["stunned_ids"], ["A", "B"])
        self.assertEqual(out[-1]["score"], 15 + 5)

    def test_refuel_to_30_evicts_drainers(self):
        s = sc(player={"pos": [0, 0, 23.5], "carried": 1}, lanterns=[{"id": "L1", "lit": True, "fuel": 25}],
               shades=[{"id": "A", "pos": [1.5, 0, 25], "state": "drain", "target_lantern_id": "L1"}])
        out = run(1, 1, 31, s, frames({"tick": 0, "interact": True}), snapshot_every=1)
        # step 2 burns decay 1/60 + drain 5/60 before the refuel: 25 - 0.1 + 10
        self.assertEqual(events(out, "refuel")[0]["data"]["fuel"], 34.9)
        a = shade(snap_at(out, 31), "A")
        self.assertGreaterEqual(math.hypot(a["pos"][0], a["pos"][2] - 25), 6 - 1e-3)
        self.assertEqual(events(out, "player_hit"), [])


class WinRule(unittest.TestCase):
    def _dawn(self, night, n_lit, flames=3, time_left=1):
        lit = [{"id": "L%d" % i, "lit": True} for i in range(1, n_lit + 1)]
        s = sc(player={"pos": [0, 0, -30] if night == 3 else [0, 0, 0], "flames": flames},
               lanterns=lit, time_left_s=time_left)
        return run(1, night, 200, s)

    def test_thresholds_3_of_5_4_of_6_5_of_7(self):
        for night, need in ((1, 3), (2, 4), (3, 5)):
            self.assertEqual(events(self._dawn(night, need), "game_over")[0]["data"],
                             {"result": "won", "reason": "dawn_survived"}, night)
            self.assertEqual(events(self._dawn(night, need - 1), "game_over")[0]["data"],
                             {"result": "lost", "reason": "dawn"}, night)

    def test_dawn_score(self):
        out = self._dawn(1, 3, flames=2)
        # 3 lanterns * (50 + floor(99.0)) + 2 flames * 50; no time bonus
        self.assertEqual(out[-1]["score"], 3 * (50 + 99) + 2 * 50)
        self.assertEqual(out[-1]["ticks"], 60)

    def test_durations(self):
        for night, secs in ((1, 240), (2, 270), (3, 300)):
            self.assertEqual(snaps(run(1, night, 0, sc()))[0]["time_left_s"], float(secs))

    def test_no_flames_beats_dawn_on_last_tick(self):
        lit = [{"id": "L%d" % i, "lit": True} for i in range(1, 6)]
        s = sc(player={"flames": 1}, lanterns=lit, time_left_s=1,
               shades=[{"id": "A", "pos": [0, 0, 1.0 + 4.0 * 60 / 60 - 1e-3]}])  # reaches 1 m at tick 60
        out = run(1, 1, 100, s)
        go = events(out, "game_over")[0]
        self.assertEqual((go["tick"], go["data"]["reason"]), (60, "no_flames"))


class Capacity(unittest.TestCase):
    def test_capacity_grows_with_lights(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 10})
        out = run(1, 1, 1, s, frames({"tick": 0, "interact": True}), snapshot_every=1)
        self.assertEqual(snaps(out)[0]["player"]["capacity"], 10)
        self.assertEqual(snap_at(out, 1)["player"]["capacity"], 12)

    def test_capacity_max_20_and_scenario_field(self):
        out = run(1, 1, 0, sc(player={"successful_lights": 9}))
        self.assertEqual(snaps(out)[0]["player"]["capacity"], 20)

    def test_preset_lit_does_not_count(self):
        out = run(1, 1, 0, sc(lanterns=[{"id": "L1", "lit": True}]))
        self.assertEqual(snaps(out)[0]["player"]["capacity"], 10)

    def test_pickup_up_to_new_capacity(self):
        s = sc(player={"carried": 10, "successful_lights": 1}, motes=[[0, 0, 0], [0.5, 0, 0], [0.2, 0, 0]])
        out = run(1, 1, 1, s)
        self.assertEqual(len(events(out, "mote_picked")), 2)


if __name__ == "__main__":
    unittest.main()
