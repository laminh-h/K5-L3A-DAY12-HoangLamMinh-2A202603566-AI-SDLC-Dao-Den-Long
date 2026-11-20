"""Parsing + validation of --inputs / --scenario files. Any format error -> InputError (exit 2)."""
import json
import numbers

from .sim import BUTTONS, DRIFTER_STATES, SHADE_STATES, default_input


class InputError(Exception):
    pass


def _num(v):
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _vec(v, n):
    return isinstance(v, list) and len(v) == n and all(_num(x) for x in v)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise InputError("cannot read %s: %s" % (path, e))


def parse_inputs(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("frames"), list):
        raise InputError("inputs: expected object with 'frames' array")
    last = -1
    frames = {}
    for i, f in enumerate(obj["frames"]):
        if not isinstance(f, dict) or not _int(f.get("tick")) or f["tick"] < 0:
            raise InputError("inputs: frame %d needs integer tick >= 0" % i)
        if f["tick"] <= last:
            raise InputError("inputs: frame ticks must be strictly increasing (frame %d)" % i)
        last = f["tick"]
        if "move" in f and not (_vec(f["move"], 2) and all(-1 <= x <= 1 for x in f["move"])):
            raise InputError("inputs: frame %d move must be [x,z] in [-1,1]" % i)
        if "cam_yaw_deg" in f and not _num(f["cam_yaw_deg"]):
            raise InputError("inputs: frame %d cam_yaw_deg must be a number" % i)
        for b in BUTTONS:
            if b in f and not isinstance(f[b], bool):
                raise InputError("inputs: frame %d %s must be boolean" % (i, b))
        frames[f["tick"]] = f
    return InputTimeline(frames)


class InputTimeline:
    """Held input state; a frame changes only the fields it contains."""

    def __init__(self, frames=None):
        self.frames = frames or {}
        self.cur = default_input()

    def at(self, tick):
        f = self.frames.get(tick)
        if f:
            for k in ("move", "cam_yaw_deg") + BUTTONS:
                if k in f:
                    self.cur[k] = list(f[k]) if k == "move" else f[k]
        return self.cur


def parse_scenario(obj, lantern_ids):
    if not isinstance(obj, dict):
        raise InputError("scenario: expected object")
    p = obj.get("player", {})
    if not isinstance(p, dict):
        raise InputError("scenario: player must be object")
    if "pos" in p and not _vec(p["pos"], 3):
        raise InputError("scenario: player.pos must be [x,y,z]")
    for k in ("carried", "flames", "invuln_ticks", "dash_cd_ticks", "pulse_cd_ticks",
              "charm_ticks"):
        if k in p and not (_int(p[k]) and p[k] >= 0):
            raise InputError("scenario: player.%s must be integer >= 0" % k)
    for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
        if k in obj and not isinstance(obj[k], bool):
            raise InputError("scenario: %s must be boolean" % k)
    if "motes" in obj:
        if not isinstance(obj["motes"], list):
            raise InputError("scenario: motes must be array")
        for m in obj["motes"]:
            ok = _vec(m, 3) or (isinstance(m, dict) and _vec(m.get("pos"), 3)
                                and m.get("kind", "random") in ("random", "dropped"))
            if not ok:
                raise InputError("scenario: mote must be [x,y,z] or {pos, kind}")
    if "shades" in obj:
        sh = obj["shades"]
        if not isinstance(sh, list):
            raise InputError("scenario: shades must be array")
        ids = set()
        for s in sh:
            if not isinstance(s, dict) or not _vec(s.get("pos"), 3):
                raise InputError("scenario: each shade needs pos [x,y,z]")
            if "state" in s and s["state"] not in SHADE_STATES:
                raise InputError("scenario: shade state must be one of %s" % (SHADE_STATES,))
            if "state_ticks_left" in s and not (_int(s["state_ticks_left"])
                                                and s["state_ticks_left"] >= 0):
                raise InputError("scenario: state_ticks_left must be integer >= 0")
            if "id" in s:
                if not isinstance(s["id"], str) or not s["id"] or s["id"] in ids:
                    raise InputError("scenario: shade id must be unique non-empty string")
                ids.add(s["id"])
    if "lanterns" in obj:
        if not isinstance(obj["lanterns"], list):
            raise InputError("scenario: lanterns must be array")
        for l in obj["lanterns"]:
            if not isinstance(l, dict) or l.get("id") not in lantern_ids:
                raise InputError("scenario: lantern id must be one of %s" % sorted(lantern_ids))
            if "pos" in l and not _vec(l["pos"], 3):
                raise InputError("scenario: lantern pos must be [x,y,z]")
            if "deposited" in l and not (_int(l["deposited"]) and l["deposited"] >= 0):
                raise InputError("scenario: lantern deposited must be integer >= 0")
            if "lit" in l and not isinstance(l["lit"], bool):
                raise InputError("scenario: lantern lit must be boolean")
    for key, states in (("drifters", DRIFTER_STATES), ("charms", None)):
        if key not in obj:
            continue
        if not isinstance(obj[key], list):
            raise InputError("scenario: %s must be array" % key)
        for e in obj[key]:
            if not isinstance(e, dict):
                raise InputError("scenario: %s entries must be objects" % key)
            if key == "drifters" and not _vec(e.get("pos"), 3):
                raise InputError("scenario: drifter needs pos [x,y,z]")
            if "pos" in e and not _vec(e["pos"], 3):
                raise InputError("scenario: %s pos must be [x,y,z]" % key)
            if states and "state" in e and e["state"] not in states:
                raise InputError("scenario: drifter state must be one of %s" % (states,))
            if "id" in e and not (isinstance(e["id"], str) and e["id"]):
                raise InputError("scenario: id must be a non-empty string")
            for k in ("stolen", "respawn_ticks", "state_ticks_left"):
                if k in e and not (_int(e[k]) and e[k] >= 0):
                    raise InputError("scenario: %s.%s must be integer >= 0" % (key, k))
            if "available" in e and not isinstance(e["available"], bool):
                raise InputError("scenario: charms.available must be boolean")
    if "time_left_s" in obj and not (_num(obj["time_left_s"]) and obj["time_left_s"] > 0):
        raise InputError("scenario: time_left_s must be a number > 0")
    return obj
