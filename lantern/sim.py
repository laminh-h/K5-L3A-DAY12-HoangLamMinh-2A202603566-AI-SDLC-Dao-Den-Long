"""Deterministic game simulation (Test Contract v1.0). No rendering, no wall clock.

Step order inside one tick (documented in docs/notes/phase-1-assumptions.md):
  1. timers (invuln, pulse cooldown, shade stun)   2. player move + jump
  3. mote pickup   4. interact/deposit   5. pulse   6. shades move
  7. shade hits    8. spawns             9. dawn check
"""
import math
import random

from . import config as C

BUTTONS = ("jump", "interact", "pulse", "dash")
DT = 1.0 / C.TICK_RATE


def r3(v):
    x = round(float(v), 3)
    return 0.0 if x == 0 else x


def dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def default_input():
    return {"move": [0.0, 0.0], "cam_yaw_deg": 0.0,
            "jump": False, "interact": False, "pulse": False, "dash": False}


class Game:
    def __init__(self, seed, tuning, night=1, scenario=None):
        if night != 1:
            raise ValueError("only --night 1 is supported in this build")
        self.t = tuning
        self.rng = random.Random(seed)
        self.tick = 0
        self.state = "playing"
        self.result_reason = None
        self.score = 0
        self.events = []
        self.time_base = float(tuning["night1_duration_s"])
        self.player = {"pos": [0.0, 0.0, 0.0], "vy": 0.0,
                       "flames": int(tuning["flames"]), "carried": 0,
                       "invuln": 0, "cooldown": 0}
        self.lanterns = []
        n = int(tuning["lantern_count_night1"])
        for i in range(n):
            a = math.radians(360.0 * i / n)
            self.lanterns.append({"id": "L%d" % (i + 1),
                                  "pos": [r3(C.LANTERN_RING_RADIUS * math.sin(a)), 0.0,
                                          r3(C.LANTERN_RING_RADIUS * math.cos(a))],
                                  "lit": False, "deposited": 0})
        self.motes, self.mote_seq = [], 0
        self.shades, self.shade_seq = [], 0
        self.random_motes = True
        self.random_shades = True
        self.prev = {b: False for b in BUTTONS}
        self.mote_timer = 0
        self.shade_timer = 0
        self._setup(scenario or {})

    # ------------------------------------------------------------------ setup
    def _setup(self, sc):
        """Build the scenario. Emits no events and adds no score."""
        self.random_motes = sc.get("random_motes", True)
        self.random_shades = sc.get("random_shades", True)
        p = sc.get("player", {})
        if "pos" in p:
            self.player["pos"] = [float(v) for v in p["pos"]]
        if "carried" in p:
            self.player["carried"] = int(p["carried"])
        if "flames" in p:
            self.player["flames"] = int(p["flames"])
        if "time_left_s" in sc:
            self.time_base = float(sc["time_left_s"])
        by_id = {l["id"]: l for l in self.lanterns}
        for ls in sc.get("lanterns", []):
            l = by_id[ls["id"]]
            if "pos" in ls:
                l["pos"] = [float(v) for v in ls["pos"]]
            if "deposited" in ls:
                l["deposited"] = int(ls["deposited"])
            if "lit" in ls:
                l["lit"] = bool(ls["lit"])
        if "motes" in sc:
            for m in sc["motes"]:
                self._add_mote([float(v) for v in m])
        elif self.random_motes:
            for _ in range(C.INITIAL_MOTES):
                self._add_mote(self._random_point(C.MOTE_MIN_R, C.MOTE_MAX_R))
        if "shades" in sc:
            used = {s["id"] for s in sc["shades"] if "id" in s}
            for s in sc["shades"]:
                sid = s.get("id") or self._next_shade_id(used)
                used.add(sid)
                self.shades.append(self._new_shade(sid, [float(v) for v in s["pos"]]))
        elif self.random_shades:
            for _ in range(C.INITIAL_SHADES):
                self._spawn_shade(emit=False)

    def _random_point(self, rmin, rmax):
        a = self.rng.uniform(0, 2 * math.pi)
        r = math.sqrt(self.rng.uniform(rmin * rmin, rmax * rmax))
        return [r * math.sin(a), 0.0, r * math.cos(a)]

    def _add_mote(self, pos):
        self.mote_seq += 1
        self.motes.append({"id": "M%d" % self.mote_seq, "pos": pos})

    def _next_shade_id(self, used=()):
        while True:
            self.shade_seq += 1
            sid = "S%d" % self.shade_seq
            if sid not in used and all(s["id"] != sid for s in self.shades):
                return sid

    def _new_shade(self, sid, pos):
        return {"id": sid, "pos": pos, "state": "chase", "stun": 0}

    def _spawn_shade(self, emit=True):
        a = self.rng.uniform(0, 2 * math.pi)
        pos = [C.SHADE_SPAWN_R * math.sin(a), 0.0, C.SHADE_SPAWN_R * math.cos(a)]
        s = self._new_shade(self._next_shade_id(), pos)
        self._keep_out_of_safe(s)
        self.shades.append(s)
        if emit:
            self._emit("shade_spawned", {"id": s["id"]})

    # ------------------------------------------------------------------ helpers
    @property
    def time_left(self):
        return self.time_base - self.tick / C.TICK_RATE

    def _ticks(self, seconds):
        return int(round(seconds * C.TICK_RATE))

    def _emit(self, name, data):
        self.events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def _finish(self, result, reason):
        self.state = result
        self.result_reason = reason
        if result == "won":
            sc = self.t["score"]
            secs = max(0, math.floor(self.time_left + 1e-9))
            self.score += sc["per_second_left"] * secs + sc["per_flame_left"] * self.player["flames"]
        self._emit("game_over", {"result": result, "reason": reason})

    def _keep_out_of_safe(self, s):
        r = float(self.t["safe_radius"])
        for l in self.lanterns:
            if not l["lit"]:
                continue
            d = dist_xz(s["pos"], l["pos"])
            if d < r:
                if d == 0:
                    dx, dz = 1.0, 0.0
                else:
                    dx, dz = (s["pos"][0] - l["pos"][0]) / d, (s["pos"][2] - l["pos"][2]) / d
                s["pos"][0] = l["pos"][0] + dx * r
                s["pos"][2] = l["pos"][2] + dz * r

    # ------------------------------------------------------------------ step
    def step(self, inp):
        """Apply input of tick k, produce state k+1."""
        if self.state != "playing":
            return
        self.tick += 1
        t, p = self.t, self.player
        pressed = {b: bool(inp.get(b)) and not self.prev[b] for b in BUTTONS}
        self.prev = {b: bool(inp.get(b)) for b in BUTTONS}

        # 1. timers
        if p["invuln"] > 0:
            p["invuln"] -= 1
        if p["cooldown"] > 0:
            p["cooldown"] -= 1
        for s in self.shades:
            if s["state"] == "stunned":
                s["stun"] -= 1
                if s["stun"] <= 0:
                    s["state"], s["stun"] = "chase", 0

        # 2. movement
        mx, mz = float(inp["move"][0]), float(inp["move"][1])
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(float(inp["cam_yaw_deg"]))
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        sp = float(t["player_speed"]) * DT
        p["pos"][0] += wx * sp
        p["pos"][2] += wz * sp
        r = math.hypot(p["pos"][0], p["pos"][2])
        if r > C.ISLAND_RADIUS:
            p["pos"][0] *= C.ISLAND_RADIUS / r
            p["pos"][2] *= C.ISLAND_RADIUS / r
        if pressed["jump"] and p["pos"][1] <= 0 and p["vy"] <= 0:
            p["vy"] = C.JUMP_SPEED
        if p["pos"][1] > 0 or p["vy"] > 0:
            p["pos"][1] += p["vy"] * DT
            p["vy"] -= C.GRAVITY * DT
            if p["pos"][1] <= 0:
                p["pos"][1], p["vy"] = 0.0, 0.0

        # 3. pickup
        cap, pr = int(t["carry_capacity"]), float(t["pickup_radius"])
        keep = []
        for m in self.motes:
            if p["carried"] < cap and dist_xz(p["pos"], m["pos"]) <= pr:
                p["carried"] += 1
                self.score += t["score"]["per_mote"]
                self._emit("mote_picked", {"carried": p["carried"]})
            else:
                keep.append(m)
        self.motes = keep

        # 4. interact -> deposit into nearest unlit lantern in range
        if pressed["interact"]:
            ir, cost = float(t["interact_radius"]), int(t["lantern_cost"])
            best = None
            for l in self.lanterns:
                if l["lit"]:
                    continue
                d = dist_xz(p["pos"], l["pos"])
                if d <= ir and (best is None or d < best[0]):
                    best = (d, l)
            if best and p["carried"] > 0:
                l = best[1]
                amount = min(p["carried"], cost - l["deposited"])
                if amount > 0:
                    p["carried"] -= amount
                    l["deposited"] += amount
                    self._emit("deposit", {"lantern_id": l["id"], "amount": amount,
                                           "deposited": l["deposited"]})
                    if l["deposited"] >= cost:
                        l["lit"] = True
                        self.score += t["score"]["per_lantern"]
                        self._emit("lantern_lit", {"lantern_id": l["id"]})
                        for s in self.shades:
                            self._keep_out_of_safe(s)
                        if all(x["lit"] for x in self.lanterns):
                            self._finish("won", "all_lit")
                            return

        # 5. pulse
        if pressed["pulse"] and p["cooldown"] == 0 and p["carried"] >= int(t["pulse_cost"]):
            p["carried"] -= int(t["pulse_cost"])
            p["cooldown"] = self._ticks(float(t["pulse_cooldown_s"]))
            stunned = []
            for s in self.shades:
                d = dist_xz(p["pos"], s["pos"])
                if d <= float(t["pulse_radius"]):
                    s["state"], s["stun"] = "stunned", self._ticks(float(t["pulse_stun_s"]))
                    dx, dz = ((s["pos"][0] - p["pos"][0]) / d, (s["pos"][2] - p["pos"][2]) / d) \
                        if d > 0 else (1.0, 0.0)
                    s["pos"][0] += dx * float(t["pulse_push_m"])
                    s["pos"][2] += dz * float(t["pulse_push_m"])
                    self._keep_out_of_safe(s)
                    stunned.append(s["id"])
            self.score += t["score"]["per_stun"] * len(stunned)
            self._emit("pulse", {"stunned_ids": stunned})

        # 6. shades chase
        ss = float(t["shade_speed"]) * DT
        for s in self.shades:
            if s["state"] != "chase":
                continue
            d = dist_xz(p["pos"], s["pos"])
            if d > 0:
                stepd = min(ss, d)
                s["pos"][0] += (p["pos"][0] - s["pos"][0]) / d * stepd
                s["pos"][2] += (p["pos"][2] - s["pos"][2]) / d * stepd
            self._keep_out_of_safe(s)

        # 7. hits (at most one per tick; invulnerability afterwards)
        if p["invuln"] == 0:
            hr = float(t["shade_hit_radius"])
            for s in self.shades:
                if s["state"] == "chase" and dist_xz(p["pos"], s["pos"]) <= hr:
                    p["flames"] -= 1
                    dropped = int(math.floor(p["carried"] * float(t["hit_drop_ratio"])))
                    p["carried"] -= dropped
                    p["invuln"] = self._ticks(float(t["invuln_s"]))
                    self._emit("player_hit", {"by": "shade", "flames": p["flames"],
                                              "dropped": dropped})
                    if p["flames"] <= 0:
                        self._finish("lost", "no_flames")
                        return
                    break

        # 8. spawns
        if self.random_motes:
            self.mote_timer += 1
            if self.mote_timer >= self._ticks(C.MOTE_RESPAWN_S):
                self.mote_timer = 0
                if len(self.motes) < C.MAX_MOTES:
                    self._add_mote(self._random_point(C.MOTE_MIN_R, C.MOTE_MAX_R))
        if self.random_shades:
            self.shade_timer += 1
            if self.shade_timer >= self._ticks(C.SHADE_SPAWN_S):
                self.shade_timer = 0
                if len(self.shades) < C.MAX_SHADES:
                    self._spawn_shade()

        # 9. dawn
        if self.time_left <= 1e-9:
            self._finish("lost", "dawn")

    # ------------------------------------------------------------------ output
    def snapshot(self):
        p = self.player
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.tick,
            "state": self.state, "time_left_s": r3(max(0.0, self.time_left)),
            "score": self.score,
            "player": {"pos": [r3(v) for v in p["pos"]], "flames": p["flames"],
                       "carried": p["carried"]},
            "lanterns": [{"id": l["id"], "pos": [r3(v) for v in l["pos"]], "lit": l["lit"],
                          "deposited": l["deposited"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]], "state": s["state"]}
                       for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(v) for v in m["pos"]]} for m in self.motes],
        }

    def drain_events(self):
        ev, self.events = self.events, []
        return ev
