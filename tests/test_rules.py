"""Rule tests - Test Contract v1.1 / Ticket-02.

Phase-1 tests changed by Ticket-02 are kept and updated; reason noted as `# T02:` (see
docs/notes/phase-2-spec.md section "Test changes").
"""
import math
import time
import unittest

from lantern import config
from lantern.contract_io import InputTimeline, parse_inputs
from lantern.headless import run

T = config.load_tuning()
QUIET = {"random_motes": False, "random_shades": False, "random_drifters": False,
         "motes": [], "shades": [], "drifters": [], "charms": []}


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


def snap_at(out, tick):
    return [s for s in snaps(out) if s["tick"] == tick][0]


class TickModel(unittest.TestCase):
    def test_snapshot_tick0_and_every_n(self):
        out = run(1, 1, 25, sc(), snapshot_every=10)
        self.assertEqual([s["tick"] for s in snaps(out)], [0, 10, 20])
        self.assertEqual(out[-1], {"type": "end", "ticks": 25, "state": "playing", "score": 0})

    def test_night_start_event(self):
        out = run(1, 2, 1, sc())
        self.assertEqual(events(out, "night_start")[0], {"type": "event", "tick": 0,
                                                         "name": "night_start",
                                                         "data": {"night": 2}})

    def test_time_left(self):
        out = run(1, 1, 60, sc(time_left_s=100))
        self.assertEqual(snaps(out)[-1]["time_left_s"], 99.0)

    def test_event_tick_is_k_plus_1(self):
        out = run(1, 1, 5, sc(motes=[[0, 0, 0.5]]))
        self.assertEqual(events(out, "mote_picked")[0]["tick"], 1)

    def test_snapshot_v11_fields(self):
        s = snaps(run(1, 3, 1, sc()))[0]
        for k in ("night", "wind", "player", "motes", "drifters", "charms"):
            self.assertIn(k, s)
        for k in ("vel", "grounded", "invuln", "dash_cd_s", "pulse_cd_s", "charm_s"):
            self.assertIn(k, s["player"])
        self.assertEqual(s["night"], 3)


class Movement(unittest.TestCase):
    def test_speed_and_axis(self):
        out = run(1, 1, 60, sc(), frames({"tick": 0, "move": [0, 1]}))
        self.assertAlmostEqual(snaps(out)[-1]["player"]["pos"][2], 6.0, places=2)

    def test_cam_yaw_rotation(self):
        out = run(1, 1, 60, sc(), frames({"tick": 0, "move": [0, 1], "cam_yaw_deg": 90}))
        pos = snaps(out)[-1]["player"]["pos"]
        self.assertAlmostEqual(pos[0], 6.0, places=2)
        self.assertAlmostEqual(pos[2], 0.0, places=2)

    def test_diagonal_normalized(self):
        out = run(1, 1, 60, sc(), frames({"tick": 0, "move": [1, 1]}))
        pos = snaps(out)[-1]["player"]["pos"]
        self.assertAlmostEqual(math.hypot(pos[0], pos[2]), 6.0, places=2)

    def test_fields_persist_between_frames(self):
        tl = InputTimeline({0: {"tick": 0, "move": [1, 0]}, 5: {"tick": 5, "jump": True}})
        tl.at(0)
        cur = tl.at(5)
        self.assertEqual(cur["move"], [1, 0])
        self.assertTrue(cur["jump"])

    def test_jump_apex_and_land(self):
        # v=7, g=20 -> apex ~1.225 m, airtime ~0.7 s
        out = run(1, 1, 120, sc(), frames({"tick": 0, "jump": True}), snapshot_every=1)
        ys = [s["player"]["pos"][1] for s in snaps(out)]
        self.assertAlmostEqual(max(ys), 1.225, delta=0.06)
        air = sum(1 for y in ys if y > 0)
        self.assertAlmostEqual(air / 60, 0.7, delta=0.05)
        self.assertEqual(ys[-1], 0.0)
        self.assertTrue(snaps(out)[-1]["player"]["grounded"])

    def test_no_double_jump(self):
        out = run(1, 1, 40, sc(), frames({"tick": 0, "jump": True}, {"tick": 5, "jump": False},
                                         {"tick": 10, "jump": True}), snapshot_every=1)
        ys = [s["player"]["pos"][1] for s in snaps(out)]
        self.assertLess(max(ys), 1.3)


class Dash(unittest.TestCase):
    def test_dash_distance_event_cooldown(self):
        fs = frames({"tick": 0, "move": [1, 0], "dash": True}, {"tick": 1, "dash": False},
                    {"tick": 30, "dash": True}, {"tick": 31, "dash": False},
                    {"tick": 90, "dash": True}, {"tick": 91, "dash": False})
        out = run(1, 1, 92, sc(), fs, snapshot_every=1)
        self.assertEqual([e["tick"] for e in events(out, "dash")], [1, 91])
        # 12 ticks at 14 m/s = 2.8 m, versus 12 ticks of running = 1.2 m
        self.assertAlmostEqual(snap_at(out, 12)["player"]["pos"][0], 2.8, places=2)
        self.assertAlmostEqual(snap_at(out, 13)["player"]["pos"][0], 2.9, places=2)

    def test_dash_uses_facing_when_idle(self):
        # start facing +Z
        out = run(1, 1, 12, sc(), frames({"tick": 0, "dash": True}), snapshot_every=12)
        self.assertAlmostEqual(snaps(out)[-1]["player"]["pos"][2], 2.8, places=2)

    def test_air_dash_keeps_height(self):
        fs = frames({"tick": 0, "jump": True}, {"tick": 10, "dash": True})
        out = run(1, 1, 22, sc(), fs, snapshot_every=1)
        ys = [snap_at(out, k)["player"]["pos"][1] for k in range(11, 23)]
        self.assertEqual(len(set(ys)), 1)


class Motes(unittest.TestCase):
    def test_pickup_radius_inclusive(self):
        out = run(1, 1, 1, sc(motes=[[1.0, 0, 0], [1.01, 0, 0]]))
        self.assertEqual(len(events(out, "mote_picked")), 1)
        self.assertEqual(out[-1]["score"], 0)  # T02: score is per DEPOSITED mote now

    def test_pickup_height_limit(self):
        out = run(1, 1, 1, sc(motes=[[0, 1.5, 0], [0.5, 1.6, 0]]))
        self.assertEqual(len(events(out, "mote_picked")), 1)

    def test_capacity(self):
        out = run(1, 1, 1, sc(player={"carried": 10}, motes=[[0, 0, 0]]))
        self.assertEqual(events(out, "mote_picked"), [])

    def test_initial_20_distinct_and_spawn_every_240(self):
        out = run(3, 1, 480, {"random_shades": False}, snapshot_every=240)
        s0, s1, s2 = snaps(out)
        self.assertEqual(s0["motes_active"], 20)
        self.assertEqual(len({tuple(m["pos"]) for m in s0["motes"]}), 20)
        self.assertEqual((s1["motes_active"], s2["motes_active"]), (21, 22))


class Lanterns(unittest.TestCase):
    def test_deposit_and_light(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 10})
        out = run(1, 1, 3, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "deposit")[0]["data"],
                         {"lantern_id": "L1", "amount": 10, "deposited": 10})
        # T03: lantern_lit has relight flag; +5 per deposited mote, +100 first light
        self.assertEqual(events(out, "lantern_lit")[0]["data"], {"lantern_id": "L1", "relight": False})
        self.assertEqual(out[-1]["score"], 10 * 5 + 100)

    def test_partial_deposit_remembers(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 3}, lanterns=[{"id": "L1", "deposited": 4}])
        out = run(1, 1, 3, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "deposit")[0]["data"]["deposited"], 7)

    def test_interact_radius_2(self):
        s = sc(player={"pos": [0, 0, 22.9], "carried": 5})  # 2.1 m from L1
        out = run(1, 1, 3, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "deposit"), [])

    def test_tie_goes_to_smaller_id(self):
        s = sc(player={"carried": 5}, lanterns=[{"id": "L3", "pos": [1, 0, 0]},
                                               {"id": "L2", "pos": [-1, 0, 0]}])
        out = run(1, 1, 2, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "deposit")[0]["data"]["lantern_id"], "L2")

    def test_interact_is_edge_triggered(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 5})
        out = run(1, 1, 30, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(len(events(out, "deposit")), 1)

    def test_scenario_lit_gives_no_score(self):
        lit = [{"id": "L%d" % i, "lit": True} for i in range(1, 5)]
        out = run(1, 1, 1, sc(lanterns=lit))
        self.assertEqual(snaps(out)[0]["score"], 0)  # T02: line 0 is now night_start
        self.assertEqual([e["name"] for e in events(out)], ["night_start"])

    def test_all_lit_no_longer_wins_early(self):
        # T03 [THAY THE]: lighting every lantern no longer ends the night (was won/all_lit in T02)
        lit = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)]
        s = sc(player={"pos": [0, 0, 24], "carried": 10}, lanterns=lit, time_left_s=100)
        out = run(1, 1, 50, s, frames({"tick": 0, "interact": True}))
        self.assertEqual(events(out, "game_over"), [])
        self.assertEqual(out[-1]["state"], "playing")

    def test_win_on_last_tick_beats_dawn(self):
        # T03: still valid - enough lanterns lit at the dawn tick -> dawn_survived
        lit = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)]
        s = sc(player={"pos": [0, 0, 24], "carried": 10}, lanterns=lit, time_left_s=1)
        out = run(1, 1, 100, s, frames({"tick": 59, "interact": True}))
        self.assertEqual(out[-1]["state"], "won")
        self.assertEqual(out[-1]["ticks"], 60)


class Shades(unittest.TestCase):
    def test_shade_chases_at_speed(self):
        # T02: detection 12 m -> start at 10 m (was 20 m)
        out = run(1, 1, 30, sc(shades=[{"id": "A", "pos": [10, 0, 0]}]))
        sh = snaps(out)[-1]["shades"][0]
        self.assertAlmostEqual(sh["pos"][0], 10 - 2.0, places=2)
        self.assertEqual(sh["state"], "chase")

    def test_far_shade_wanders(self):
        out = run(1, 1, 1, sc(shades=[{"id": "A", "pos": [20, 0, 0]}]))
        self.assertEqual(snaps(out)[-1]["shades"][0]["state"], "wander")

    def test_lose_track_beyond_18(self):
        s = sc(shades=[{"id": "A", "pos": [-11, 0, 0]}])
        out = run(1, 1, 300, s, frames({"tick": 0, "move": [1, 0]}), snapshot_every=1)
        states = [x["shades"][0]["state"] for x in snaps(out)]
        self.assertIn("chase", states)
        self.assertEqual(states[-1], "wander")

    def test_hit_drop_invuln_recoil(self):
        s = sc(player={"carried": 5}, shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        out = run(1, 1, 61, s, snapshot_every=1)
        hits = events(out, "player_hit")
        self.assertEqual(hits[0]["data"], {"by": "shade", "flames": 2, "dropped": 2})
        self.assertEqual(snap_at(out, 1)["shades"][0]["state"], "recoil")
        dropped = [m for m in snap_at(out, 1)["motes"] if m["kind"] == "dropped"]
        self.assertEqual(len(dropped), 2)
        for m in dropped:
            self.assertTrue(1.5 - 1e-3 <= math.hypot(m["pos"][0], m["pos"][2]) <= 2.5 + 1e-3)
            self.assertEqual(m["ttl_s"], 8.0)
        # step 8 (chase 4/60 m) happens before step 9 (hit); then recoil 2 m in 60 ticks
        self.assertAlmostEqual(snap_at(out, 61)["shades"][0]["pos"][0], 0.5 - 4 / 60 + 2.0, places=2)

    def test_invuln_90_ticks(self):
        s = sc(shades=[{"id": "A", "pos": [0.5, 0, 0]}, {"id": "B", "pos": [-0.5, 0, 0]}])
        out = run(1, 1, 92, s)
        self.assertEqual([e["tick"] for e in events(out, "player_hit")], [1, 91])

    def test_one_flame_per_tick_lowest_id(self):
        s = sc(shades=[{"id": "S2", "pos": [0.5, 0, 0]}, {"id": "S10", "pos": [-0.5, 0, 0]}])
        out = run(1, 1, 1, s, snapshot_every=1)
        self.assertEqual(len(events(out, "player_hit")), 1)
        st = {x["id"]: x["state"] for x in snaps(out)[-1]["shades"]}
        self.assertEqual(st, {"S2": "recoil", "S10": "chase"})

    def test_hit_height_limit(self):
        s = sc(shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        out = run(1, 1, 20, s, frames({"tick": 0, "jump": True}))
        # jumping: still < 1.5 m above -> hit once on tick 1
        self.assertEqual(len(events(out, "player_hit")), 1)

    def test_lose_no_flames(self):
        s = sc(player={"flames": 1}, shades=[{"pos": [0.5, 0, 0]}])
        out = run(1, 1, 10, s)
        self.assertEqual(events(out, "game_over")[0]["data"], {"result": "lost", "reason": "no_flames"})

    def test_spawn_schedule_night1(self):
        out = run(7, 1, 300 + 480 * 5 + 1, {"random_motes": False}, snapshot_every=10000)
        ev = [(e["tick"], e["data"]["id"]) for e in events(out, "shade_spawned")]
        self.assertEqual(ev[:3], [(300, "S1"), (300, "S2"), (780, "S3")])
        self.assertEqual(len(ev), 6)  # max 6

    def test_spawn_15m_from_player(self):
        out = run(11, 1, 301, {"random_motes": False, "player": {"pos": [37, 0, 0]}},
                  snapshot_every=301)
        for s in snaps(out)[-1]["shades"]:
            self.assertGreaterEqual(math.hypot(s["pos"][0] - 37, s["pos"][2]), 15 - 1e-3)

    def test_spawning_state_harmless(self):
        out = run(7, 1, 301, {"random_motes": False}, snapshot_every=301)
        self.assertTrue(all(s["state"] == "spawning" for s in snaps(out)[-1]["shades"]))


class Pulse(unittest.TestCase):
    def test_pulse_stuns_pushes_costs(self):
        # T02: cost 3, radius 5 (3D from foot+0.8), push 4 m over 15 ticks, score +5
        s = sc(player={"carried": 5}, shades=[{"id": "A", "pos": [4.9, 0, 0]},
                                              {"id": "B", "pos": [3, 0, 4.1]}])
        out = run(1, 1, 16, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        self.assertEqual(events(out, "pulse")[0]["data"], {"stunned_ids": ["A"]})
        a = [x for x in snap_at(out, 15)["shades"] if x["id"] == "A"][0]
        self.assertEqual(a["state"], "stunned")
        self.assertAlmostEqual(a["pos"][0], 4.9 + 4.0, places=3)
        self.assertEqual(snap_at(out, 1)["player"]["carried"], 2)
        self.assertEqual(snap_at(out, 1)["score"], 5)

    def test_stun_120_ticks(self):
        s = sc(player={"carried": 5}, shades=[{"id": "A", "pos": [3, 0, 0]}])
        out = run(1, 1, 121, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        self.assertEqual(snap_at(out, 120)["shades"][0]["state"], "stunned")
        self.assertNotEqual(snap_at(out, 121)["shades"][0]["state"], "stunned")

    def test_pulse_needs_3(self):
        s = sc(player={"carried": 2}, shades=[{"pos": [3, 0, 0]}])
        out = run(1, 1, 2, s, frames({"tick": 0, "pulse": True}))
        self.assertEqual(events(out, "pulse"), [])

    def test_pulse_cooldown_180(self):
        s = sc(player={"carried": 9})
        fs = frames({"tick": 0, "pulse": True}, {"tick": 1, "pulse": False},
                    {"tick": 100, "pulse": True}, {"tick": 101, "pulse": False},
                    {"tick": 180, "pulse": True})
        out = run(1, 1, 182, s, fs)
        self.assertEqual([e["tick"] for e in events(out, "pulse")], [1, 181])

    def test_repulse_stunned_scores_again(self):
        s = sc(player={"carried": 9}, shades=[{"id": "A", "pos": [1, 0, 0], "state": "stunned",
                                               "state_ticks_left": 50}])
        out = run(1, 1, 1, s, frames({"tick": 0, "pulse": True}))
        self.assertEqual(out[-1]["score"], 5)


class SafeZone(unittest.TestCase):
    def test_lit_lantern_blocks_shade(self):
        s = sc(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "lit": True}],
               shades=[{"id": "A", "pos": [0, 0, 15]}])
        out = run(1, 1, 600, s, snapshot_every=1)
        for snap in snaps(out):
            d = math.hypot(snap["shades"][0]["pos"][0], snap["shades"][0]["pos"][2] - 25)
            self.assertGreaterEqual(d, 6.0 - 1e-3)
        self.assertEqual(events(out, "player_hit"), [])

    def test_evicted_when_lit(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 10},
               shades=[{"id": "A", "pos": [0, 0, 22], "state": "stunned", "state_ticks_left": 2}])
        out = run(1, 1, 31, s, frames({"tick": 0, "interact": True}), snapshot_every=1)
        d = math.hypot(*[snap_at(out, 31)["shades"][0]["pos"][i] - (0, 0, 25)[i] for i in (0, 2)])
        self.assertGreaterEqual(d, 6.0 - 1e-3)
        self.assertEqual(events(out, "player_hit"), [])


class Fall(unittest.TestCase):
    def test_fall_respawn(self):
        s = sc(player={"pos": [39.5, 0, 0], "carried": 4})
        out = run(1, 1, 200, s, frames({"tick": 0, "move": [1, 0]}, {"tick": 10, "move": [0, 0]}),
                  snapshot_every=1)
        hit = events(out, "player_hit")[0]
        self.assertEqual(hit["data"], {"by": "fall", "flames": 2, "dropped": 0, "lost": 4})
        ft = hit["tick"]
        self.assertEqual(snap_at(out, ft + 60)["player"]["pos"], [0.0, 0.0, 0.0])
        self.assertEqual(snap_at(out, ft + 60)["player"]["invuln"], 1.5)

    def test_fall_last_flame_loses(self):
        s = sc(player={"pos": [39.5, 0, 0], "flames": 1})
        out = run(1, 1, 200, s, frames({"tick": 0, "move": [1, 0]}))
        self.assertEqual(events(out, "game_over")[0]["data"]["reason"], "no_flames")


class Night2Map(unittest.TestCase):
    def test_lanterns_and_pad_launch(self):
        s = sc(player={"pos": [20, 0, 18]})
        out = run(1, 2, 120, s, snapshot_every=1)
        self.assertEqual([l["id"] for l in snaps(out)[0]["lanterns"]], ["L%d" % i for i in range(1, 7)])
        land = [x for x in snaps(out)[2:] if x["player"]["grounded"]][0]
        px, _, pz = land["player"]["pos"]
        self.assertLessEqual(math.hypot(px - 70, pz), 28)
        self.assertAlmostEqual(land["tick"] / 60, 1.4, delta=0.1)
        self.assertEqual(events(out, "player_hit"), [])

    def test_bridge_walk(self):
        s = sc(player={"pos": [27, 0, 0]})
        out = run(1, 2, 180, s, frames({"tick": 0, "move": [1, 0]}))
        self.assertEqual(events(out, "player_hit"), [])

    def test_off_bridge_falls(self):
        s = sc(player={"pos": [35, 0, 0]})
        out = run(1, 2, 200, s, frames({"tick": 0, "move": [0, 1]}))
        self.assertEqual(events(out, "player_hit")[0]["data"]["by"], "fall")


class Night3Map(unittest.TestCase):
    def test_wall_blocks_tier1_from_ground(self):
        s = sc(player={"pos": [0, 0, 26]})
        out = run(1, 3, 120, s, frames({"tick": 0, "move": [0, -1]}))
        p = snaps(out)[-1]["player"]["pos"]
        self.assertAlmostEqual(p[2], 24.0, delta=0.15)
        self.assertEqual(p[1], 0.0)

    def test_ramp_up_to_tier1(self):
        a = math.radians(30)
        s = sc(player={"pos": [31 * math.cos(a), 0, 31 * math.sin(a)]}, wind_enabled=False)
        # walk inward along the ramp axis (world dir = -u)
        out = run(1, 3, 90, s, frames({"tick": 0, "move": [-math.cos(a), -math.sin(a)]}))
        self.assertAlmostEqual(snaps(out)[-1]["player"]["pos"][1], 3.0, places=3)

    def test_pad_to_tier2(self):
        s = sc(player={"pos": [0, 3, 13]}, wind_enabled=False)
        out = run(1, 3, 120, s)
        p = snaps(out)[-1]["player"]
        self.assertEqual(p["pos"][1], 6.0)
        self.assertTrue(p["grounded"])

    def test_wind_gust(self):
        out = run(5, 3, 1801, sc(wind_enabled=True), snapshot_every=1)
        self.assertFalse(snap_at(out, 1799)["wind"]["active"])
        self.assertTrue(snap_at(out, 1800)["wind"]["active"])
        p0, p1 = snap_at(out, 1800)["player"]["pos"], snap_at(out, 1801)["player"]["pos"]
        self.assertAlmostEqual(math.hypot(p1[0] - p0[0], p1[2] - p0[2]), 2.0 / 60, delta=0.002)  # 3dp rounding

    def test_shade_speed_45(self):
        s = sc(player={"pos": [0, 0, -30]}, shades=[{"id": "A", "pos": [10, 0, -30]}])
        out = run(1, 3, 60, s)
        self.assertAlmostEqual(snaps(out)[-1]["shades"][0]["pos"][0], 10 - 4.5, places=2)


class Drifters(unittest.TestCase):
    def test_steal_then_flee_and_vanish(self):
        s = sc(player={"carried": 6}, drifters=[{"id": "D1", "pos": [5, 0, 0]}])
        out = run(1, 2, 400, s, snapshot_every=1)
        st = events(out, "drifter_steal")[0]
        self.assertEqual(st["data"], {"drifter_id": "D1", "amount": 3, "carried": 3})
        t0 = st["tick"]
        self.assertEqual(snap_at(out, t0)["drifters"][0]["state"], "flee")
        self.assertEqual(snap_at(out, t0 + 240)["drifters"], [])
        self.assertEqual(events(out, "player_hit"), [])

    def test_idle_when_few_motes(self):
        s = sc(player={"carried": 4}, drifters=[{"id": "D1", "pos": [5, 0, 0]}])
        out = run(1, 2, 60, s)
        self.assertEqual(snaps(out)[-1]["drifters"][0]["state"], "idle")

    def test_pulse_chasing_drifter_flees(self):
        s = sc(player={"carried": 8}, drifters=[{"id": "D1", "pos": [4, 0, 0], "state": "chase"}])
        out = run(1, 2, 5, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        self.assertEqual(snap_at(out, 1)["drifters"][0]["state"], "flee")
        self.assertEqual(events(out, "drifter_steal"), [])

    def test_pulse_fleeing_drops_stolen(self):
        s = sc(player={"carried": 3}, drifters=[{"id": "D1", "pos": [3, 0, 0], "state": "flee",
                                                 "stolen": 3}])
        out = run(1, 2, 130, s, frames({"tick": 0, "pulse": True}), snapshot_every=1)
        self.assertEqual(events(out, "drifter_drop")[0]["data"], {"drifter_id": "D1", "amount": 3})
        self.assertEqual(sum(m["kind"] == "dropped" for m in snap_at(out, 1)["motes"]), 3)
        self.assertEqual(snap_at(out, 121)["drifters"], [])

    def test_safe_zone_and_invuln_do_not_stop_steal(self):
        s = sc(player={"pos": [0, 0, 24], "carried": 6, "invuln_ticks": 200},
               lanterns=[{"id": "L1", "lit": True}], drifters=[{"id": "D1", "pos": [0, 0, 20]}])
        out = run(1, 2, 120, s)
        self.assertEqual(len(events(out, "drifter_steal")), 1)

    def test_spawn_schedule(self):
        out = run(2, 2, 2401, {"random_shades": False, "random_motes": False}, snapshot_every=1200)
        self.assertEqual([[d["id"] for d in x["drifters"]] for x in snaps(out)],
                         [[], ["D1"], ["D1", "D2"]])


class Charm(unittest.TestCase):
    def test_pickup_speed_and_dash_no_cd(self):
        s = sc(player={"pos": [35, 0, 0]}, charms=[{"id": "C1", "pos": [35, 0, 0]}])
        fs = frames({"tick": 0, "move": [0, 0]}, {"tick": 1, "move": [1, 0]},
                    {"tick": 70, "dash": True}, {"tick": 71, "dash": False},
                    {"tick": 90, "dash": True}, {"tick": 91, "dash": False})
        out = run(1, 2, 100, s, fs, snapshot_every=1)
        self.assertEqual(events(out, "charm_picked")[0]["data"],
                         {"charm_id": "C1", "charm_ticks": 600})
        dx = snap_at(out, 61)["player"]["pos"][0] - snap_at(out, 1)["player"]["pos"][0]
        self.assertAlmostEqual(dx, 7.2, places=2)
        self.assertEqual(len(events(out, "dash")), 2)
        c = snap_at(out, 1)["charms"][0]
        self.assertEqual((c["available"], c["respawn_s"]), (False, 45.0))

    def test_night2_default_charm(self):
        self.assertEqual([(c["id"], c["pos"]) for c in snaps(run(1, 2, 0))[0]["charms"]],
                         [("C1", [35.0, 0.0, 0.0])])


class Pause(unittest.TestCase):
    def test_pause_freezes_sim(self):
        # pause toggles on each false->true edge (releasing the key does not resume)
        fs = frames({"tick": 0, "move": [1, 0]}, {"tick": 10, "pause": True},
                    {"tick": 11, "pause": False}, {"tick": 30, "pause": True})
        out = run(1, 1, 40, sc(), fs, snapshot_every=1)
        self.assertEqual([(e["name"], e["tick"]) for e in events(out)][1:],
                         [("paused", 11), ("resumed", 31)])
        s20 = snap_at(out, 20)
        self.assertEqual((s20["state"], s20["sim_tick"]), ("paused", 10))
        self.assertEqual(s20["time_left_s"], snap_at(out, 11)["time_left_s"])
        self.assertEqual(s20["player"]["pos"], snap_at(out, 11)["player"]["pos"])
        self.assertEqual(snap_at(out, 40)["sim_tick"], 20)
        self.assertEqual(out[-1]["ticks"], 40)


class Determinism(unittest.TestCase):
    def test_same_seed_same_output_all_nights(self):
        for n in (1, 2, 3):
            fs = lambda: frames({"tick": 0, "move": [0.3, 1]}, {"tick": 300, "pulse": True})
            self.assertEqual(run(42, n, 3000, None, fs()), run(42, n, 3000, None, fs()))


class Performance(unittest.TestCase):
    def test_full_night_under_30s(self):
        t0 = time.perf_counter()
        run(1, 3, 21600, {"player": {"flames": 99}})
        self.assertLess(time.perf_counter() - t0, 30.0)


if __name__ == "__main__":
    unittest.main()
