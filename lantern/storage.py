"""Local persistence: leaderboard + settings (keybinds, audio, accessibility).
Data dir: $DDL_HOME or ~/.dao_den_long
"""
import datetime
import json
import os
import re

TOP_N = 10
NAME_RE = re.compile(r"^\w{3,12}$", re.UNICODE)  # [A-Za-z0-9_] + Vietnamese letters (bonus)

ACTIONS = ("up", "down", "left", "right", "jump", "dash", "interact", "pulse", "pause")
DEFAULT_KEYS = {"up": "w", "down": "s", "left": "a", "right": "d", "jump": "space",
                "dash": "shift", "interact": "e", "pulse": "q", "pause": "escape"}
DEFAULT_SETTINGS = {"volume": 0.7, "mouse_sensitivity": 1.0, "colorblind": False,
                    "reduced_motion": False, "large_text": False, "keys": dict(DEFAULT_KEYS)}


def data_dir():
    d = os.environ.get("DDL_HOME") or os.path.join(os.path.expanduser("~"), ".dao_den_long")
    os.makedirs(d, exist_ok=True)
    return d


def _path(name):
    return os.path.join(data_dir(), name)


def _load(name, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(name, obj):
    tmp = _path(name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _path(name))


# ------------------------------------------------------------------ leaderboard
def valid_name(name):
    return bool(NAME_RE.match(name or ""))


def sort_entries(entries):
    # score desc; same score -> earlier achieved_at first
    def key(e):
        ts = datetime.datetime.fromisoformat(e["achieved_at"]).timestamp()
        return (-e["score"], ts)
    return sorted(entries, key=key)[:TOP_N]


def load_leaderboard():
    return sort_entries(_load("leaderboard.json", {"entries": []}).get("entries", []))


def add_score(name, score, nights_won, seed, now=None):
    if not valid_name(name):
        raise ValueError("name must be 3-12 letters, digits or _")
    if not 0 <= nights_won <= 3:
        raise ValueError("nights_won must be 0..3")
    now = now or datetime.datetime.now().astimezone()
    entry = {"name": name, "score": int(score), "nights_won": int(nights_won),
             "achieved_at": now.isoformat(timespec="seconds"), "seed": int(seed)}
    entries = sort_entries(load_leaderboard() + [entry])
    _save("leaderboard.json", {"entries": entries})
    return entry in entries


def export_leaderboard(out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"entries": load_leaderboard()}, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ------------------------------------------------------------------ settings
def load_settings():
    s = dict(DEFAULT_SETTINGS)
    s.update(_load("settings.json", {}))
    keys = dict(DEFAULT_KEYS)
    keys.update({k: v for k, v in s.get("keys", {}).items() if k in ACTIONS})
    s["keys"] = keys
    return s


def save_settings(s):
    _save("settings.json", s)


def key_conflicts(keys):
    """Return {key: [actions...]} for keys bound to more than one action."""
    seen = {}
    for a in ACTIONS:
        seen.setdefault(keys.get(a), []).append(a)
    return {k: v for k, v in seen.items() if len(v) > 1}


def reset_keys(s):
    s["keys"] = dict(DEFAULT_KEYS)
    return s
