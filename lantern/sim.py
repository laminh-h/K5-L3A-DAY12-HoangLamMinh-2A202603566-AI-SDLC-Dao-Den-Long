"""Deterministic game simulation - Test Contract v1.1 (Ticket-02).

Tick order (mandatory, Ticket-02):
  1 input (+pause)  2 counters  3 player move + fall  4 pickup motes/charms
  5 interact  6 safe zones  7 pulse  8 move shades/drifters  9 contacts
  10 spawns  11 win/lose  (12 snapshot is done by the runner)
"""
import math
import random
import re

from . import config as C
from .maps import make_night

BUTTONS = ("jump", "interact", "pulse", "dash", "pause")
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned")
DRIFTER_STATES = ("idle", "chase", "flee")
DT = 1.0 / C.TICK_RATE


def r3(v):
    x = round(float(v), 3)
    return 0.0 if x == 0 else x


def dxz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def idkey(obj):
    s = obj["id"]
    m = re.match(r"^(.*?)(\d+)$", s)
    return (m.group(1), int(m.group(2)), s) if m else (s, -1, s)


def unit(dx, dz, default=(1.0, 0.0)):
    d = math.hypot(dx, dz)
    return (dx / d, dz / d) if d > 1e-12 else default


def default_input():
    return {"move": [0.0, 0.0], "cam_yaw_deg": 0.0,
            "jump": False, "interact": False, "pulse": False, "dash": False, "pause": False}


class Game:
    def __init__(self, seed, tuning, night=1, scenario=None):
        self.t = t = tuning
        self.rng = random.Random(seed)
        self.night = night
        self.map = make_night(night)
        self.tick = 0
        self.sim_tick = 0
        self.state = "playing"
        self.paused = False
        self.score = 0
        self.events = []
        self.duration = float(t[self.map.duration_key])
        self.k_invuln = self._ticks(t["invuln_s"])
        self.k_stun = self._ticks(t["pulse_stun_s"])
        self.k_pulse_cd = self._ticks(t["pulse_cooldown_s"])
        self.k_dash = self._ticks(t["dash_duration_s"])
        self.k_dash_cd = self._ticks(t["dash_cooldown_s"])
        self.shade_speed = C.SHADE_SPEED_NIGHT3 if night == 3 else float(t["shade_speed"])
        sx, sy, sz = self.map.start
        self.p = {"pos": [sx, sy, sz], "vel": [0.0, 0.0, 0.0], "grounded": True,
                  "facing": (0.0, 1.0), "flames": int(t["flames"]), "carried": 0,
                  "invuln": 0, "dash_cd": 0, "pulse_cd": 0, "charm": 0,
                  "dash_t": 0, "dash_dir": (0.0, 1.0), "launch": None, "respawn": 0}
        self.lanterns = [{"id": "L%d" % (i + 1), "pos": [float(v) for v in pos],
                          "lit": False, "deposited": 0}
                         for i, pos in enumerate(self.map.lanterns)]
        self.motes, self.mote_seq = [], 0
        self.shades, self.shade_seq = [], 0
        self.drifters, self.drifter_seq = [], 0
        self.charms = [{"id": "C%d" % (i + 1), "pos": [float(v) for v in pos],
                        "available": True, "respawn": 0} for i, pos in enumerate(self.map.charms)]
        self.random_motes = True
        self.random_shades = True
        self.random_drifters = night in (2, 3)
        self.wind_enabled = self.map.wind
        self.wind = {"active": False, "dir": 0.0, "left": 0}
        self.prev = {b: False for b in BUTTONS}
        self._setup(scenario or {})

    # ================================================================ setup
    def _setup(self, sc):
        """Build the scenario. Emits no events, adds no score."""
        for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
            if k in sc:
                setattr(self, k, bool(sc[k]))
        p, sp = self.p, sc.get("player", {})
        if "pos" in sp:
            p["pos"] = [float(v) for v in sp["pos"]]
        for k, dst in (("carried", "carried"), ("flames", "flames"), ("invuln_ticks", "invuln"),
                       ("dash_cd_ticks", "dash_cd"), ("pulse_cd_ticks", "pulse_cd"),
                       ("charm_ticks", "charm")):
            if k in sp:
                p[dst] = int(sp[k])
        g = self.map.ground(p["pos"][0], p["pos"][2])
        p["grounded"] = g is not None and abs(p["pos"][1] - g) < 1e-6
        if "time_left_s" in sc:
            self.duration = float(sc["time_left_s"])
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
                if isinstance(m, dict):
                    ttl = m.get("ttl_ticks", round(m["ttl_s"] * 60) if "ttl_s" in m else C.DROP_TTL)
                    kind = m.get("kind", "random")
                    self._add_mote(m["pos"], kind, ttl if kind == "dropped" else None, born=-1)
                else:
                    self._add_mote(m, "random", None, born=-1)
        elif self.random_motes:
            pts = self.rng.sample(range(len(self.map.mote_points)), C.MOTE_INITIAL)
            for i in pts:
                self._add_mote(self.map.mote_points[i], "random", None, born=-1, point=i)
        if "shades" in sc:
            used = {s["id"] for s in sc["shades"] if "id" in s}
            for s in sc["shades"]:
                sid = s.get("id") or self._next_id("S", used)
                used.add(sid)
                sh = self._new_shade(sid, s["pos"], s.get("state", "wander"))
                left = s.get("state_ticks_left")
                if sh["state"] == "stunned":
                    sh["stun"] = int(left) if left is not None else self.k_stun
                elif sh["state"] == "spawning":
                    sh["spawn"] = int(left) if left is not None else C.SHADE_SPAWNING_TICKS
                elif sh["state"] == "recoil":
                    sh["recoil"] = int(left) if left is not None else C.RECOIL_TICKS
                self.shades.append(sh)
        if "drifters" in sc:
            used = {d["id"] for d in sc["drifters"] if "id" in d}
            for d in sc["drifters"]:
                did = d.get("id") or self._next_id("D", used)
                used.add(did)
                dr = self._new_drifter(did, d["pos"])
                dr["state"] = d.get("state", "idle")
                dr["stolen"] = int(d.get("stolen", 0))
                if dr["state"] == "flee":
                    dr["flee"] = int(d.get("state_ticks_left", C.DRIFTER_FLEE_TICKS))
                self.drifters.append(dr)
        if "charms" in sc:
            defaults = {c["id"]: c for c in self.charms}
            new = []
            for i, c in enumerate(sc["charms"]):
                cid = c.get("id", "C%d" % (i + 1))
                pos = c.get("pos", defaults[cid]["pos"] if cid in defaults else p["pos"])
                rs = int(c.get("respawn_ticks", 0))
                new.append({"id": cid, "pos": [float(v) for v in pos],
                            "available": bool(c.get("available", rs == 0)), "respawn": rs})
            self.charms = new
        self.shades.sort(key=idkey)
        self.drifters.sort(key=idkey)

    def _next_id(self, prefix, used=()):
        pool = {"S": self.shades, "D": self.drifters}[prefix]
        attr = {"S": "shade_seq", "D": "drifter_seq"}[prefix]
        while True:
            setattr(self, attr, getattr(self, attr) + 1)
            i = "%s%d" % (prefix, getattr(self, attr))
            if i not in used and all(o["id"] != i for o in pool):
                return i

    def _add_mote(self, pos, kind, ttl, born, point=None):
        self.mote_seq += 1
        self.motes.append({"id": "M%d" % self.mote_seq, "pos": [float(v) for v in pos],
                           "kind": kind, "ttl": ttl, "born": born, "point": point})

    def _new_shade(self, sid, pos, state):
        return {"id": sid, "pos": [float(v) for v in pos], "state": state, "stun": 0,
                "spawn": 0, "recoil": 0, "recoil_dir": (1.0, 0.0), "push": 0,
                "push_dir": (1.0, 0.0), "evict": 0, "evict_v": (0.0, 0.0)}

    def _new_drifter(self, did, pos):
        return {"id": did, "pos": [float(v) for v in pos], "state": "idle", "stolen": 0,
                "flee": 0, "wp": None}

    # ================================================================ helpers
    def _ticks(self, seconds):
        return int(round(float(seconds) * C.TICK_RATE))

    @property
    def time_left(self):
        return self.duration - self.sim_tick / C.TICK_RATE

    def _emit(self, name, data):
        self.events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def _ground(self, x, z):
        return self.map.ground(x, z)

    def _drop_motes(self, n, center):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            r = self.rng.uniform(*C.DROP_RING)
            x, z = center[0] + r * math.cos(a), center[2] + r * math.sin(a)
            g = self._ground(x, z)
            self._add_mote([x, center[1] if g is None else g, z], "dropped", C.DROP_TTL,
                           born=self.sim_tick)

    def _safe_lanterns(self):
        return [l for l in self.lanterns if l["lit"]]

    def _keep_out_of_safe(self, s):
        r = float(self.t["safe_radius"])
        for l in self._safe_lanterns():
            d = dxz(s["pos"], l["pos"])
            if d < r:
                ux, uz = unit(s["pos"][0] - l["pos"][0], s["pos"][2] - l["pos"][2])
                s["pos"][0], s["pos"][2] = l["pos"][0] + ux * r, l["pos"][2] + uz * r

    def _blocked_by_tower(self, x, z):
        tw = self.map.tower
        return tw is not None and math.hypot(x - tw[0], z - tw[1]) < tw[2]

    def _shade_move(self, s, vx, vz):
        nx, nz = s["pos"][0] + vx, s["pos"][2] + vz
        if self._blocked_by_tower(nx, nz):
            return False
        s["pos"][0], s["pos"][2] = nx, nz
        g = self._ground(nx, nz)
        if g is not None:
            s["pos"][1] = g
        return True

    def _move_toward(self, obj, target, speed):
        d = dxz(obj["pos"], target)
        if d <= 1e-12:
            return
        stepd = min(speed * DT, d)
        ux, uz = (target[0] - obj["pos"][0]) / d, (target[2] - obj["pos"][2]) / d
        return ux * stepd, uz * stepd

    # ================================================================ step
    def step(self, inp):
        if self.state not in ("playing", "paused"):
            return
        self.tick += 1
        t, p = self.t, self.p
        cur = {b: bool(inp.get(b)) for b in BUTTONS}
        pressed = {b: cur[b] and not self.prev[b] for b in BUTTONS}
        self.prev = cur

        # 1. pause
        if self.paused:
            if not pressed["pause"]:
                return
            self.paused, self.state = False, "playing"
            self._emit("resumed", {})
        elif pressed["pause"]:
            self.paused, self.state = True, "paused"
            self._emit("paused", {})
            return
        self.sim_tick += 1

        # 2. counters
        for k in ("invuln", "dash_cd", "pulse_cd", "charm"):
            if p[k] > 0:
                p[k] -= 1
        if p["respawn"] > 0:
            p["respawn"] -= 1
        for s in self.shades:
            if s["state"] == "stunned":
                s["stun"] -= 1
                if s["stun"] <= 0:
                    s["state"], s["stun"], s["push"] = "wander", 0, 0
            elif s["state"] == "spawning":
                s["spawn"] -= 1
                if s["spawn"] <= 0:
                    s["state"] = "wander"
        keep = []
        for m in self.motes:
            if m["kind"] == "dropped":
                m["ttl"] -= 1
                if m["ttl"] <= 0:
                    continue
            keep.append(m)
        self.motes = keep
        for c in self.charms:
            if not c["available"]:
                c["respawn"] -= 1
                if c["respawn"] <= 0:
                    c["available"], c["respawn"] = True, 0
        if self.wind_enabled:
            if self.wind["active"]:
                self.wind["left"] -= 1
                if self.wind["left"] <= 0:
                    self.wind["active"] = False
            if self.sim_tick % C.WIND_EVERY == 0:
                self.wind = {"active": True, "dir": self.rng.uniform(0, 360), "left": C.WIND_TICKS}

        # 3. player movement + fall
        self._move_player(inp, pressed)

        alive = p["respawn"] == 0
        # 4. pickup motes and charms
        if alive:
            cap, pr = int(t["carry_capacity"]), float(t["pickup_radius"])
            keep = []
            for m in self.motes:
                if (m["born"] != self.sim_tick and p["carried"] < cap
                        and dxz(p["pos"], m["pos"]) <= pr
                        and abs(p["pos"][1] - m["pos"][1]) <= C.PICKUP_DY):
                    p["carried"] += 1
                    self._emit("mote_picked", {"carried": p["carried"]})
                else:
                    keep.append(m)
            self.motes = keep
            for c in self.charms:
                if (c["available"] and dxz(p["pos"], c["pos"]) <= pr
                        and abs(p["pos"][1] - c["pos"][1]) <= C.PICKUP_DY):
                    c["available"], c["respawn"] = False, C.CHARM_RESPAWN
                    p["charm"] = C.CHARM_TICKS
                    p["dash_cd"] = 0
                    self._emit("charm_picked", {"charm_id": c["id"], "charm_ticks": C.CHARM_TICKS})

        # 5. interact
        newly_lit = []
        if pressed["interact"] and alive:
            ir, cost = float(t["interact_radius"]), int(t["lantern_cost"])
            best = None
            for l in self.lanterns:  # id order -> ties keep smaller id
                if l["lit"]:
                    continue
                d = dxz(p["pos"], l["pos"])
                if d <= ir and (best is None or d < best[0]):
                    best = (d, l)
            if best and p["carried"] > 0:
                l = best[1]
                amount = min(p["carried"], cost - l["deposited"])
                if amount > 0:
                    p["carried"] -= amount
                    l["deposited"] += amount
                    self.score += t["score"]["per_mote"] * amount
                    self._emit("deposit", {"lantern_id": l["id"], "amount": amount,
                                           "deposited": l["deposited"]})
                    if l["deposited"] >= cost:
                        l["lit"] = True
                        self.score += t["score"]["per_lantern"]
                        self._emit("lantern_lit", {"lantern_id": l["id"]})
                        newly_lit.append(l)

        # 6. safe zones: shades inside a just-lit lantern are evicted to the edge in <=30 ticks
        sr = float(t["safe_radius"])
        for l in newly_lit:
            for s in self.shades:
                d = dxz(s["pos"], l["pos"])
                if d < sr:
                    ux, uz = unit(s["pos"][0] - l["pos"][0], s["pos"][2] - l["pos"][2])
                    need = sr - d
                    s["evict"] = C.EVICT_TICKS
                    s["evict_v"] = (ux * need / C.EVICT_TICKS, uz * need / C.EVICT_TICKS)

        # 7. pulse
        if (pressed["pulse"] and alive and p["pulse_cd"] == 0
                and p["carried"] >= int(t["pulse_cost"])):
            p["carried"] -= int(t["pulse_cost"])
            p["pulse_cd"] = self.k_pulse_cd
            cx, cy, cz = p["pos"][0], p["pos"][1] + C.PULSE_CENTER_DY, p["pos"][2]
            pr = float(t["pulse_radius"])
            hit = []
            for s in self.shades:
                if math.dist((cx, cy, cz), s["pos"]) <= pr:
                    s["state"], s["stun"] = "stunned", self.k_stun
                    s["push"] = C.PULSE_PUSH_TICKS
                    s["push_dir"] = unit(s["pos"][0] - cx, s["pos"][2] - cz)
                    hit.append(s["id"])
            self.score += t["score"]["per_stun"] * len(hit)
            self._emit("pulse", {"stunned_ids": hit})
            for d in self.drifters:
                if math.dist((cx, cy, cz), d["pos"]) <= pr:
                    if d["state"] == "chase":
                        d["state"], d["flee"] = "flee", C.DRIFTER_FLEE_TICKS
                    elif d["state"] == "flee" and d["stolen"] > 0:
                        n = d["stolen"]
                        for _ in range(n):
                            self._add_mote([d["pos"][0], self._ground(d["pos"][0], d["pos"][2])
                                            or 0.0, d["pos"][2]], "dropped", C.DROP_TTL,
                                           born=self.sim_tick)
                        d["stolen"], d["flee"] = 0, C.DRIFTER_DROP_VANISH
                        self._emit("drifter_drop", {"drifter_id": d["id"], "amount": n})

        # 8. move shades and drifters
        self._move_shades(alive)
        self._move_drifters(alive)

        # 9. contacts: drifters steal first, then shades hit (id ascending)
        if alive:
            for d in self.drifters:
                if d["state"] == "chase" and dxz(p["pos"], d["pos"]) <= C.DRIFTER_HIT_R:
                    amount = min(C.DRIFTER_STEAL, p["carried"])
                    if amount > 0:
                        p["carried"] -= amount
                        d["stolen"] = amount
                        d["state"], d["flee"] = "flee", C.DRIFTER_FLEE_TICKS
                        self._emit("drifter_steal", {"drifter_id": d["id"], "amount": amount,
                                                     "carried": p["carried"]})
            if p["invuln"] == 0:
                hr = float(t["shade_hit_radius"])
                for s in self.shades:
                    if (s["state"] in ("wander", "chase") and s["evict"] == 0
                            and dxz(p["pos"], s["pos"]) <= hr
                            and abs(p["pos"][1] - s["pos"][1]) <= C.HIT_DY):
                        p["flames"] -= 1
                        dropped = int(math.floor(p["carried"] * float(t["hit_drop_ratio"])))
                        p["carried"] -= dropped
                        self._drop_motes(dropped, p["pos"])
                        p["invuln"] = self.k_invuln
                        s["state"], s["recoil"] = "recoil", C.RECOIL_TICKS
                        s["recoil_dir"] = unit(s["pos"][0] - p["pos"][0], s["pos"][2] - p["pos"][2])
                        self._emit("player_hit", {"by": "shade", "flames": p["flames"],
                                                  "dropped": dropped})
                        break

        # 10. spawns (new entities act from next tick)
        self._spawns()

        # 11. win / lose
        if p["flames"] <= 0:
            self._finish("lost", "no_flames")
        elif all(l["lit"] for l in self.lanterns):
            self._finish("won", "all_lit")
        elif self.time_left <= 1e-9:
            self._finish("lost", "dawn")

    # ---------------------------------------------------------------- player
    def _move_player(self, inp, pressed):
        t, p = self.t, self.p
        if p["respawn"] > 0:
            return
        if p["respawn"] == 0 and p.get("_dead_wait"):
            p["_dead_wait"] = False
            sx, sy, sz = self.map.start
            p.update(pos=[sx, sy, sz], vel=[0.0, 0.0, 0.0], grounded=True, launch=None,
                     dash_t=0, invuln=self.k_invuln)
            return
        mx, mz = float(inp["move"][0]), float(inp["move"][1])
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(float(inp["cam_yaw_deg"]))
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        moving = math.hypot(wx, wz) > 1e-9
        if moving and p["launch"] is None:
            p["facing"] = unit(wx, wz)
        # dash
        if pressed["dash"] and p["dash_t"] == 0 and (p["charm"] > 0 or p["dash_cd"] == 0):
            p["dash_t"] = self.k_dash
            p["dash_dir"] = unit(wx, wz) if moving else p["facing"]
            p["dash_cd"] = 0 if p["charm"] > 0 else self.k_dash_cd
            self._emit("dash", {})
        # jump
        if pressed["jump"] and p["grounded"]:
            p["vel"][1] = C.JUMP_SPEED
            p["grounded"] = False
        # horizontal velocity
        dashing = p["dash_t"] > 0
        if dashing:
            ds = float(t["dash_speed"])
            vx, vz = p["dash_dir"][0] * ds, p["dash_dir"][1] * ds
            p["dash_t"] -= 1
        elif p["launch"] is not None:
            vx, vz = p["launch"]
        else:
            sp = C.CHARM_SPEED if p["charm"] > 0 else float(t["player_speed"])
            vx, vz = wx * sp, wz * sp
        if self.wind["active"]:
            a = math.radians(self.wind["dir"])
            vx += math.cos(a) * C.WIND_SPEED
            vz += math.sin(a) * C.WIND_SPEED
        # vertical velocity
        if dashing and not p["grounded"]:
            p["vel"][1] = 0.0
        elif not p["grounded"] or p["vel"][1] > 0:
            p["vel"][1] -= C.GRAVITY * DT
        x, y, z = p["pos"]
        # horizontal move with walls (try full, then x-only, then z-only)
        for nx, nz in ((x + vx * DT, z + vz * DT), (x + vx * DT, z), (x, z + vz * DT)):
            if not self._wall(nx, nz, y):
                break
        else:
            nx, nz = x, z
        p["vel"][0], p["vel"][2] = (nx - x) / DT, (nz - z) / DT
        ny = y + p["vel"][1] * DT if (not p["grounded"] or p["vel"][1] > 0) else y
        g = self._ground(nx, nz)
        if g is not None and ny <= g + 1e-9 and p["vel"][1] <= 0:
            ny, p["vel"][1], p["grounded"], p["launch"] = g, 0.0, True, None
        elif (g is not None and p["grounded"] and p["vel"][1] <= 0
              and 0 <= ny - g <= C.GROUND_SNAP):
            ny, p["grounded"] = g, True
        else:
            p["grounded"] = False
        p["pos"] = [nx, ny, nz]
        # bounce pads
        if p["grounded"] and p["launch"] is None:
            for center, vy, hv in self.map.pads:
                if dxz(p["pos"], center) <= 1.0 and abs(p["pos"][1] - center[1]) < 0.05:
                    p["launch"] = hv
                    p["vel"][1] = vy
                    p["grounded"] = False
                    break
        # fall
        if p["pos"][1] < C.FALL_Y:
            p["flames"] -= 1
            lost, p["carried"] = p["carried"], 0
            p["respawn"] = C.RESPAWN_WAIT
            p["_dead_wait"] = True
            p["vel"] = [0.0, 0.0, 0.0]
            p["launch"], p["dash_t"] = None, 0
            self._emit("player_hit", {"by": "fall", "flames": p["flames"], "dropped": 0,
                                      "lost": lost})

    def _wall(self, x, z, y):
        g = self._ground(x, z)
        if self._blocked_by_tower(x, z) and y < self.map.tower[3]:
            return True
        return g is not None and g > y + C.STEP_UP

    # ---------------------------------------------------------------- AI
    def _move_shades(self, alive):
        p = self.p
        for s in self.shades:
            if s["evict"] > 0:
                self._shade_move(s, *s["evict_v"])
                s["evict"] -= 1
                continue
            st = s["state"]
            if st == "spawning":
                continue
            if st == "stunned":
                if s["push"] > 0:
                    step = float(self.t["pulse_push_m"]) / C.PULSE_PUSH_TICKS
                    if self._shade_move(s, s["push_dir"][0] * step, s["push_dir"][1] * step):
                        s["push"] -= 1
                    else:
                        s["push"] = 0
                    self._keep_out_of_safe(s)
                continue
            if st == "recoil":
                step = C.RECOIL_M / C.RECOIL_TICKS
                self._shade_move(s, s["recoil_dir"][0] * step, s["recoil_dir"][1] * step)
                s["recoil"] -= 1
                if s["recoil"] <= 0:
                    s["state"] = "wander"
                self._keep_out_of_safe(s)
                continue
            d = dxz(p["pos"], s["pos"])
            if st == "wander" and alive and d <= C.DETECT_R:
                st = "chase"
            elif st == "chase" and (not alive or d > C.LOSE_R):
                st = "wander"
            s["state"] = st
            mv = None
            if st == "chase":
                mv = self._move_toward(s, p["pos"], self.shade_speed)
            else:
                target = self._wander_target(s)
                if target is not None and dxz(s["pos"], target["pos"]) > 2.0:
                    mv = self._move_toward(s, target["pos"], C.SHADE_WANDER_SPEED)
            if mv:
                self._shade_move(s, *mv)
            self._keep_out_of_safe(s)

    def _wander_target(self, s):
        best = None
        for l in self.lanterns:
            if l["lit"]:
                continue
            d = dxz(s["pos"], l["pos"])
            if best is None or d < best[0]:
                best = (d, l)
        return best[1] if best else None

    def _move_drifters(self, alive):
        p = self.p
        keep = []
        for d in self.drifters:
            if d["state"] == "flee":
                ux, uz = unit(d["pos"][0] - p["pos"][0], d["pos"][2] - p["pos"][2])
                d["pos"][0] += ux * C.DRIFTER_SPEED * DT
                d["pos"][2] += uz * C.DRIFTER_SPEED * DT
                d["flee"] -= 1
                self._drifter_y(d)
                if d["flee"] <= 0:
                    continue  # removed (with whatever it stole)
                keep.append(d)
                continue
            want = (alive and p["carried"] >= C.DRIFTER_CHASE_CARRY
                    and dxz(p["pos"], d["pos"]) <= C.DRIFTER_CHASE_R)
            d["state"] = "chase" if want else "idle"
            if want:
                mv = self._move_toward(d, p["pos"], C.DRIFTER_SPEED)
            else:
                if d["wp"] is None or dxz(d["pos"], d["wp"]) < 0.5:
                    d["wp"] = list(self.rng.choice(self.map.shade_points))
                mv = self._move_toward(d, d["wp"], C.DRIFTER_IDLE_SPEED)
            if mv:
                d["pos"][0] += mv[0]
                d["pos"][2] += mv[1]
            self._drifter_y(d)
            keep.append(d)
        self.drifters = keep

    def _drifter_y(self, d):
        g = self._ground(d["pos"][0], d["pos"][2])
        if g is not None:
            d["pos"][1] = g + C.DRIFTER_HOVER

    # ---------------------------------------------------------------- spawns
    def _spawns(self):
        st, p = self.sim_tick, self.p
        if self.random_motes and st % C.MOTE_SPAWN_EVERY == 0 and len(self.motes) < C.MOTE_CAP:
            used = {m["point"] for m in self.motes if m["point"] is not None}
            free = [i for i in range(len(self.map.mote_points)) if i not in used]
            if free:
                i = self.rng.choice(free)
                self._add_mote(self.map.mote_points[i], "random", None, born=st, point=i)
        if self.random_shades:
            n = 0
            if st == C.SHADE_FIRST_SPAWN:
                n = C.SHADE_FIRST_COUNT
            elif st > C.SHADE_FIRST_SPAWN and (st - C.SHADE_FIRST_SPAWN) % self.map.shade_interval == 0:
                n = 1
            valid = [pt for pt in self.map.shade_points
                     if dxz(pt, p["pos"]) >= C.SHADE_SPAWN_MIN_DIST]
            for _ in range(n):
                if len(self.shades) >= self.map.shade_max or not valid:
                    break
                pt = valid.pop(self.rng.randrange(len(valid)))
                s = self._new_shade(self._next_id("S"), pt, "spawning")
                s["spawn"] = C.SHADE_SPAWNING_TICKS
                self.shades.append(s)
                self._emit("shade_spawned", {"id": s["id"]})
        if (self.random_drifters and self.night in (2, 3) and st % C.DRIFTER_SPAWN_EVERY == 0
                and len(self.drifters) < C.DRIFTER_MAX):
            pt = self.rng.choice(self.map.shade_points)
            d = self._new_drifter(self._next_id("D"), pt)
            self._drifter_y(d)
            self.drifters.append(d)

    def _finish(self, result, reason):
        self.state = result
        if result == "won":
            sc = self.t["score"]
            secs = max(0, math.floor(self.time_left + 1e-9))
            self.score += sc["per_second_left"] * secs + sc["per_flame_left"] * self.p["flames"]
        self._emit("game_over", {"result": result, "reason": reason})

    # ================================================================ output
    def snapshot(self):
        p = self.p
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick,
            "state": self.state, "night": self.night,
            "time_left_s": r3(max(0.0, self.time_left)), "score": self.score,
            "wind": {"active": self.wind["active"],
                     "dir_deg": r3(self.wind["dir"]) if self.wind["active"] else None},
            "player": {"pos": [r3(v) for v in p["pos"]], "vel": [r3(v) for v in p["vel"]],
                       "grounded": p["grounded"], "flames": p["flames"], "carried": p["carried"],
                       "invuln": r3(p["invuln"] / 60), "dash_cd_s": r3(p["dash_cd"] / 60),
                       "pulse_cd_s": r3(p["pulse_cd"] / 60), "charm_s": r3(p["charm"] / 60)},
            "lanterns": [{"id": l["id"], "pos": [r3(v) for v in l["pos"]], "lit": l["lit"],
                          "deposited": l["deposited"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]],
                        "state": "recoil" if s["evict"] > 0 and s["state"] != "stunned"
                        else s["state"]} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(v) for v in m["pos"]], "kind": m["kind"],
                       "ttl_s": r3(m["ttl"] / 60) if m["kind"] == "dropped" else None}
                      for m in self.motes],
            "drifters": [{"id": d["id"], "pos": [r3(v) for v in d["pos"]], "state": d["state"],
                          "stolen": d["stolen"]} for d in self.drifters],
            "charms": [{"id": c["id"], "pos": [r3(v) for v in c["pos"]],
                        "available": c["available"], "respawn_s": r3(c["respawn"] / 60)}
                       for c in self.charms],
        }

    def drain_events(self):
        ev, self.events = self.events, []
        return ev
