"""Rule tests for Test Contract v1.0. Each test names the requirement it proves."""
import math
import unittest

from lantern import config
from lantern.contract_io import InputTimeline, parse_inputs
from lantern.headless import run

T = config.load_tuning()
QUIET = {"random_motes": False, "random_shades": False, "motes": [], "shades": []}


def sc(**kw):
    d = dict(QUIET)
    d.update(kw)
    return d


def frames(*fs):
    return parse_inputs({"frames": list(fs)})


def events(out, name=None):
    return [o for o in out if o["type"] == "event" and (name is None or o["name"] == name)]


def snaps(out):
    return [o for o in out if o["type"] == "snapshot"]


class TickModel(unittest.TestCase):
    def test_snapshot_tick0_and_every_n(self):
        out = run(1, 1, 25, sc(), snapshot_every=10)
        self.assertEqual([s["tick"] for s in snaps(out)], [0, 10, 20])
        self.assertEqual(out[-1], {"type": "end", "ticks": 25, "state": "playing", "score": 0})

    def test_time_left(self):
        out = run(1, 1, 60, sc(time_left_s=100))
        self.assertEqual(snaps(out)[-1]["time_left_s"], 99.0)

    def test_event_tick_is_k_plus_1(self):
        # mote under the player: picked during step k=0 -> event tick 1
        out = run(1, 1, 5, sc(motes=[[0, 0, 0.5]]))
        self.assertEqual(events(out, "mote_picked")[0]["tick"], 1)


class Movement(unittest.TestCase):
    def test_speed_and_axis(self):
        out = run(1, 1, 60, sc(), frames({"tick": 0, "move": [0, 1]}))
        self.assertAlmostEqual(snaps(out)[-1]["player"]["pos"][2], T["player_speed"], places=2)

    def test_cam_yaw_rotation(self):
        # theta=90: x' = z*sin = 1 -> moves +X
        out = run(1, 1, 60, sc(), frames({"tick": 0, "move": [0, 1], "cam_yaw_deg": 90}))
        pos = snaps(out)[-1]["player"]["pos"]
        self.assertAlmostEqual(pos[0], T["player_speed"], places=2)
        self.assertAlmostEqual(pos[2], 0.0, places=2)

    def test_diagonal_normalized(self):
        out = run(1, 1, 60, sc(), frames({"tick": 0, "move": [1, 1]}))
        pos = snaps(out)[-1]["player"]["pos"]
        self.assertAlmostEqual(math.hypot(pos[0], pos[2]), T["player_speed"], places=2)

    def test_fields_persist_between_frames(self):
        tl = InputTimeline({0: {"tick": 0, "move": [1, 0]}, 5: {"tick": 5, "jump": True}})
        tl.at(0)
        cur = tl.at(5)
        self.assertEqual(cur["move"], [1, 0])
        self.assertTrue(cur["jump"])

    def test_jump_goes_up_and_lands(self):
        out = run(1, 1, 120, sc(), frames({"tick": 0, "jump": True}), snapshot_every=1)
        ys = [s["player"]["pos"][1] for s in snaps(out)]
        self.assertGreater(max(ys), 0.5)
        self.assertEqual(ys[-1], 0.0)


class Motes(unittest.TestCase):
    def test_pickup_radius_inclusive(self):
        r = T["pickup_radius"]
        out = run(1, 1, 1, sc(motes=[[r, 0, 0], [r + 0.01, 0, 0]]))
        self.assertEqual(len(events(out, "mote_picked")), 1)
        self.assertEqual(out[-1]["score"], T["score"]["per_mote"])

    def test_capacity(self):
        cap = T["carry_capacity"]
        out = run(1, 1, 1, sc(player={"carried": cap}, motes=[[0, 0, 0]]))
        self.assertEqual(events(out, "mote_picked"), [])


class Lanterns(unittest.TestCase):
    def test_deposit_and_light(self):
        cost = T["lantern_cost"]
        s = sc(player={"pos": [0, 0, 24], "carried": cost},
               lanterns=[{"id": "L1", "pos": [0, 0, 25]}])
        out = run(1, 1, 3, s, frames({"tick": 0, "interact": True}))
        d = events(out, "deposit")[0]
        self.assertEqual(d["data"], {"lantern_id": "L1", "amount": cost, "deposited": cost})
        self.assertEqual(events(out, "lantern_lit")[0]["data"], {"lantern_id": "L1"})
        self.assertEqual(out[-1]["score"], T["score"]["per_lantern"])

    def test_partial_deposit(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 3})
        out = run(1, 1, 3, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "deposit")[0]["data"]["deposited"], 3)
        self.assertEqual(events(out, "lantern_lit"), [])

    def test_out_of_interact_radius(self):
        s = sc(player={"pos": [0, 0, 25 - T["interact_radius"] - 0.1], "carried": 5})
        out = run(1, 1, 3, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "deposit"), [])

    def test_interact_is_edge_triggered(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 5})
        out = run(1, 1, 30, s, frames({"tick": 0, "interact": True}))  # held 30 ticks
        self.assertEqual(len(events(out, "deposit")), 1)

    def test_scenario_lit_gives_no_score(self):
        lit = [{"id": "L%d" % i, "lit": True} for i in range(1, 5)]
        out = run(1, 1, 1, sc(lanterns=lit))
        self.assertEqual(out[0]["score"], 0)
        self.assertEqual(events(out), [])

    def test_win_all_lit_and_bonus(self):
        cost = T["lantern_cost"]
        lit = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)]
        s = sc(player={"pos": [0, 0, 24], "carried": cost}, lanterns=lit, time_left_s=100)
        out = run(1, 1, 50, s, frames({"tick": 0, "interact": True}))
        go = events(out, "game_over")[0]
        self.assertEqual(go["data"], {"result": "won", "reason": "all_lit"})
        sc_ = T["score"]
        # time_left after 1 step = 99.983 -> floor 99
        expect = sc_["per_lantern"] + sc_["per_second_left"] * 99 + sc_["per_flame_left"] * T["flames"]
        self.assertEqual(out[-1], {"type": "end", "ticks": 1, "state": "won", "score": expect})


class ShadesAndPulse(unittest.TestCase):
    def test_shade_chases_at_speed(self):
        out = run(1, 1, 60, sc(shades=[{"id": "A", "pos": [20, 0, 0]}]))
        sh = snaps(out)[-1]["shades"][0]
        self.assertAlmostEqual(sh["pos"][0], 20 - T["shade_speed"], places=2)
        self.assertEqual(sh["state"], "chase")

    def test_hit_drop_and_invuln(self):
        s = sc(player={"carried": 4}, shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        n = int(T["invuln_s"] * 60)
        out = run(1, 1, n, s)
        hits = events(out, "player_hit")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["data"], {"by": "shade", "flames": T["flames"] - 1,
                                           "dropped": math.floor(4 * T["hit_drop_ratio"])})
        out2 = run(1, 1, n + 1, s)
        self.assertEqual(len(events(out2, "player_hit")), 2)

    def test_lose_no_flames(self):
        s = sc(player={"flames": 1}, shades=[{"pos": [0.5, 0, 0]}])
        out = run(1, 1, 10, s)
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "lost", "reason": "no_flames"})
        self.assertEqual(out[-1]["state"], "lost")

    def test_pulse_stuns_pushes_costs(self):
        r = T["pulse_radius"]
        s = sc(player={"carried": 2}, shades=[{"id": "A", "pos": [r, 0, 0]},
                                              {"id": "B", "pos": [r + 3, 0, 0]}])
        out = run(1, 1, 1, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        self.assertEqual(events(out, "pulse")[0]["data"], {"stunned_ids": ["A"]})
        st = snaps(out)[-1]
        a = [x for x in st["shades"] if x["id"] == "A"][0]
        self.assertEqual(a["state"], "stunned")
        self.assertAlmostEqual(a["pos"][0], r + T["pulse_push_m"], places=3)
        self.assertEqual(st["player"]["carried"], 2 - T["pulse_cost"])
        self.assertEqual(st["score"], T["score"]["per_stun"])

    def test_stun_duration(self):
        s = sc(player={"carried": 2}, shades=[{"id": "A", "pos": [3, 0, 0]}])
        n = int(T["pulse_stun_s"] * 60)
        out = run(1, 1, n + 1, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        st = {x["tick"]: x["shades"][0]["state"] for x in snaps(out)}
        self.assertEqual(st[n], "stunned")
        self.assertEqual(st[n + 1], "chase")

    def test_pulse_needs_light(self):
        s = sc(player={"carried": 0}, shades=[{"pos": [3, 0, 0]}])
        out = run(1, 1, 2, s, frames({"tick": 0, "pulse": True}))
        self.assertEqual(events(out, "pulse"), [])

    def test_pulse_cooldown(self):
        cd = int(T["pulse_cooldown_s"] * 60)
        s = sc(player={"carried": 5})
        fs = frames({"tick": 0, "pulse": True}, {"tick": 1, "pulse": False},
                    {"tick": 2, "pulse": True}, {"tick": 3, "pulse": False},
                    {"tick": cd, "pulse": True})
        out = run(1, 1, cd + 2, s, fs)
        self.assertEqual([e["tick"] for e in events(out, "pulse")], [1, cd + 1])

    def test_safe_radius_blocks_shade(self):
        s = sc(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "pos": [0, 0, 25], "lit": True}],
               shades=[{"id": "A", "pos": [0, 0, 15]}])
        out = run(1, 1, 600, s, snapshot_every=1)
        for snap in snaps(out):
            d = math.hypot(snap["shades"][0]["pos"][0], snap["shades"][0]["pos"][2] - 25)
            self.assertGreaterEqual(d, T["safe_radius"] - 1e-3)
        self.assertEqual(events(out, "player_hit"), [])


class Dawn(unittest.TestCase):
    def test_dawn_loss(self):
        out = run(1, 1, 1000, sc(time_left_s=1))
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "lost", "reason": "dawn"})
        self.assertEqual(out[-1]["ticks"], 60)


class Determinism(unittest.TestCase):
    def test_same_seed_same_output(self):
        fs = lambda: frames({"tick": 0, "move": [0.3, 1]}, {"tick": 300, "pulse": True})
        self.assertEqual(run(42, 1, 3000, None, fs()), run(42, 1, 3000, None, fs()))

    def test_spawned_shades_emit_events(self):
        # start with no shades but auto-spawn on: first spawn at 30 s, id S1
        out = run(7, 1, 60 * 31, {"shades": [], "random_shades": True})
        ev = events(out, "shade_spawned")
        self.assertEqual([(e["tick"], e["data"]) for e in ev], [(1800, {"id": "S1"})])


if __name__ == "__main__":
    unittest.main()
