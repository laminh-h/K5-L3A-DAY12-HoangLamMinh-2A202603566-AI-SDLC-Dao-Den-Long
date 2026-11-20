"""Ursina 3D client. View + input only: all rules live in lantern.sim (fixed 60 Hz steps)."""
import json
import math
import os
import platform
import random
import time
from pathlib import Path
from types import SimpleNamespace

from ursina import (Audio, Button, Color, Cone, Cylinder, Entity, InputField, Mesh, Slider,
                    Text, Ursina, Vec3, application, camera, color, destroy, held_keys,
                    mouse, scene, window)

from . import bench_scene, config, storage
from .maps import NIGHTS
from .memory import process_start_epoch, rss_mb
from .sim import FU, Game

ASSETS = Path(__file__).parent / "assets"
STEP = 1.0 / 60.0
NAMES = {1: "Đêm 1 – Đảo Bến", 2: "Đêm 2 – Đảo Cau", 3: "Đêm 3 – Đảo Chuông"}
ONG_DANG = {
    1: "Ông Đăng: \"Mây ơi, sương đen nuốt hết đèn rồi. Gom đom đóm, thắp lại đảo Bến nhé!\"",
    2: "Ông Đăng: \"Đảo Cau có hai hòn, nối bằng cầu tre. Coi chừng Gió Lạc cướp đom đóm!\"",
    3: "Ông Đăng: \"Đảo Chuông nhiều tầng, gió mạnh. Giữ đèn sáng tới khi chuông bình minh vang.\"",
}
ACTION_LABEL = {"up": "Lên", "down": "Xuống", "left": "Trái", "right": "Phải", "jump": "Nhảy",
                "dash": "Lướt", "interact": "Tương tác", "pulse": "Tỏa Sáng", "pause": "Tạm dừng"}


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return Color(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def scale_c(c, k):
    return Color(min(1, c[0] * k), min(1, c[1] * k), min(1, c[2] * k), c[3])


P = {k: hexc(v) for k, v in {
    "sky": "#0E1430", "fog": "#1B2350", "grass": "#2F5D50", "sand": "#C9B48A", "wood": "#6B4A2F",
    "sea": "#12384A", "lit": "#FFB347", "core": "#FFE9B0", "off": "#5B5F6E", "mote": "#FFF6C2",
    "halo": "#FFE58A", "shade": "#120A1A", "rim": "#7A3CFF", "stun": "#3A3450", "shirt": "#E8E2D0",
    "scarf": "#C8102E", "gold": "#F2C14E", "drifter": "#8FA3B8", "danger": "#FF5A5F",
    "ui": "#F5F1E6", "rim_cb": "#00B3FF", "white": "#FFFFFF"}.items()}


# ------------------------------------------------------------------ fast shared meshes
def _sphere(cx, cy, cz, r, rings=6, segs=10, sy=1.0):
    v, t = [], []
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(segs + 1):
            ph = 2 * math.pi * j / segs
            v.append((cx + r * math.sin(th) * math.cos(ph), cy + r * sy * math.cos(th),
                      cz + r * math.sin(th) * math.sin(ph)))
    for i in range(rings):
        for j in range(segs):
            a, b = i * (segs + 1) + j, (i + 1) * (segs + 1) + j
            t += [a, b, a + 1, a + 1, b, b + 1]
    return v, t


def _box(cx, cy, cz, sx, sy, sz):
    v = [(cx + dx * sx / 2, cy + dy * sy / 2, cz + dz * sz / 2)
         for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    t = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1, 2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4,
         1, 5, 7, 1, 7, 3]
    return v, t


def geom_node(parts, name="mesh"):
    """parts: [((verts, tris), Color)] in Ursina coords (Y up) -> Panda NodePath (Z up)."""
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
                              GeomVertexWriter, NodePath)
    vd = GeomVertexData(name, GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vw, cw = GeomVertexWriter(vd, "vertex"), GeomVertexWriter(vd, "color")
    tris = GeomTriangles(Geom.UHStatic)
    base = 0
    for (verts, idx), c in parts:
        for x, y, z in verts:
            vw.addData3(x, z, y)
            cw.addData4(c[0], c[1], c[2], c[3])
        for k in range(0, len(idx), 3):
            tris.addVertices(base + idx[k], base + idx[k + 1], base + idx[k + 2])
        base += len(verts)
    g = Geom(vd)
    g.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(g)
    np = NodePath(gn)
    np.setTwoSided(True)
    return np


_MESH = {}


def shade_mesh(stunned, colorblind, spawning=False):
    key = (stunned, colorblind, spawning)
    if key not in _MESH:
        rim = P["rim_cb"] if colorblind else P["rim"]
        body = P["stun"] if stunned else P["shade"]
        r = 0.3 if spawning else 0.7
        ring = []
        for j in range(12):  # rim band around the equator
            a = 2 * math.pi * j / 12
            ring.append((_box(r * math.cos(a), 0, r * math.sin(a), 0.22, 0.08, 0.22), rim))
        _MESH[key] = geom_node([(_sphere(0, 0, 0, r), body),
                                (_box(-0.2 * r / 0.7, 0.12, -r * 0.93, 0.18, 0.1, 0.06), rim),
                                (_box(0.2 * r / 0.7, 0.12, -r * 0.93, 0.18, 0.1, 0.06), rim)] + ring,
                               "shade")
    return _MESH[key]


def mote_mesh():
    if "mote" not in _MESH:
        h = P["halo"]
        _MESH["mote"] = geom_node([(_sphere(0, 0, 0, 0.11, 4, 6), P["mote"]),
                                   (_sphere(0, 0, 0, 0.28, 4, 6), Color(h[0], h[1], h[2], 0.3))], "mote")
    return _MESH["mote"]


class Dyn:
    """Lightweight handle for an instanced dynamic object."""
    __slots__ = ("np", "key", "inst", "phase")

    def __init__(self, np):
        self.np, self.key, self.inst, self.phase = np, None, None, random.random() * 6.28

    def removeNode(self):
        self.np.removeNode()


# =====================================================================================
class World:
    """Static island geometry + entity pools synced from the sim each frame."""

    def __init__(self, night, settings):
        self.night = night
        self.settings = settings
        self.root = Entity()
        self.static = Entity(parent=self.root)   # flattened island geometry, tinted as one node
        self.ground = []
        from panda3d.core import RigidBodyCombiner, TransparencyAttrib
        # RigidBodyCombiner: many moving objects -> one geom per combiner (few draw calls)
        self.dyn_rbc, self.mote_rbc = RigidBodyCombiner("dyn"), RigidBodyCombiner("motes")
        self.dyn = self.root.attachNewNode(self.dyn_rbc)
        self.mote_root = self.root.attachNewNode(self.mote_rbc)
        self.dirty = {"dyn": False, "motes": False}
        self.mote_root.setTransparency(TransparencyAttrib.MAlpha)
        self.last_k = None
        self.shades, self.motes, self.drifters, self.charms, self.lanterns = {}, {}, {}, {}, {}
        self._build_map()

    def _g(self, base, **kw):
        e = Entity(parent=self.static, color=base, **kw)
        self.ground.append((e, base))
        return e

    def _build_map(self):
        n = self.night
        Entity(parent=self.root, model="plane", scale=900, y=-12, color=P["sea"])
        if n == 1:
            self._g(P["sand"], model=Cylinder(48, radius=40, height=1), y=-1.02)
            self._g(P["grass"], model=Cylinder(48, radius=37, height=1), y=-1.0)
        elif n == 2:
            for cx in (0, 70):
                self._g(P["sand"], model=Cylinder(40, radius=28, height=1), x=cx, y=-1.02)
                self._g(P["grass"], model=Cylinder(40, radius=25.5, height=1), x=cx, y=-1.0)
            self._g(P["wood"], model="cube", position=(35, -0.15, 0), scale=(18, 0.3, 4))
        else:
            self._g(P["sand"], model=Cylinder(56, radius=45, height=1), y=-1.02)
            self._g(P["grass"], model=Cylinder(56, radius=42, height=1), y=-1.0)
            for i in range(30):  # tier 1: half annulus 12..24, z > 0, Y = 3
                a = math.radians(3 + 6 * i)
                self._g(P["grass"], model="cube", position=(18 * math.cos(a), 1.5, 18 * math.sin(a)),
                        rotation_y=90 - math.degrees(a), scale=(12, 3, 2.1))
            self._g(P["sand"], model=Cylinder(32, radius=8, height=6), y=0)
            self._g(P["wood"], model=Cylinder(16, radius=2, height=14), y=0)
            for a in (30, 150):
                pivot = Entity(parent=self.static, position=(27 * math.cos(math.radians(a)), 1.5,
                                                           27 * math.sin(math.radians(a))),
                               rotation_y=90 - a)
                e = Entity(parent=pivot, model="cube", scale=(3, 0.25, 6.7), rotation_x=26.6,
                           color=P["wood"])
                self.ground.append((e, P["wood"]))
        for center, _vy, _hv in make_map(n).pads:
            Entity(parent=self.root, model=Cylinder(16, radius=1, height=0.12),
                   position=center, color=P["gold"])
        self.static.flattenStrong()   # dozens of static pieces -> a few draw calls

    # ------------------------------------------------------------------ pools
    def _sync(self, pool, items, make, update, group=None):
        alive = set()
        for it in items:
            alive.add(it["id"])
            if it["id"] not in pool:
                pool[it["id"]] = make(it)
                if group:
                    self.dirty[group] = True
            update(pool[it["id"]], it)
        for k in [k for k in pool if k not in alive]:
            if group:
                self.dirty[group] = True
            e = pool.pop(k)
            if isinstance(e, Entity):
                destroy(e)
            else:
                e.removeNode()

    def _make_shade(self, s):
        return Dyn(self.dyn.attachNewNode("shade"))

    def _upd_shade(self, d, s):
        d.np.setPos(s["pos"][0], s["pos"][2], s["pos"][1] + 0.9)   # Panda is Z-up
        key = (s["state"] == "stunned", self.settings["colorblind"], s["state"] == "spawning")
        if key != d.key:
            if d.inst is not None:
                d.inst.removeNode()
            d.inst = shade_mesh(*key).copyTo(d.np)
            d.key = key
            self.dirty["dyn"] = True

    def _make_mote(self, m):
        d = Dyn(self.mote_root.attachNewNode("mote"))
        mote_mesh().copyTo(d.np)
        return d

    def _upd_mote(self, d, m):
        d.np.setPos(m["pos"][0], m["pos"][2], m["pos"][1] + 0.8 + 0.15 * math.sin(self.now * 3 + d.phase))

    def _make_lantern(self, l):
        e = Entity(parent=self.root, position=l["pos"])
        Entity(parent=e, model="cube", scale=(0.25, 3, 0.25), y=1.5, color=P["wood"])
        e.body = Entity(parent=e, model="sphere", scale=(1.0, 1.3, 1.0), y=3.3)
        e.tear = Entity(parent=e.body, model="cube", scale=(0.08, 0.6, 1.05), x=0.2,
                        color=Color(0.1, 0.1, 0.12, 1))
        e.glow = Entity(parent=e, model="sphere", scale=3.2, y=3.3, color=Color(1, 0.7, 0.28, 0.18))
        e.bar_bg = Entity(parent=e, model="quad", y=4.6, scale=(1.6, 0.18), billboard=True,
                          color=Color(0, 0, 0, 0.6))
        e.bar = Entity(parent=e, model="quad", y=4.6, z=-0.01, scale=(1.6, 0.14), billboard=True,
                       color=P["lit"])
        return e

    def _upd_lantern(self, e, l):
        fuel = l["fuel"] / FU                                                # sim stores 1/60 units
        blink = l["lit"] and fuel < 30 and (self.now % 1.0) < 0.5            # 1 Hz
        e.body.color = (P["core"] if blink else P["lit"]) if l["lit"] else P["off"]
        e.body.scale_y = 1.3 if l["lit"] else 1.3 * 0.8                       # off: squashed 20%
        e.tear.enabled = not l["lit"]                                         # off: torn paper
        e.glow.enabled = l["lit"] and not blink
        e.bar.enabled = e.bar_bg.enabled = l["lit"]
        e.bar.scale_x = 1.6 * max(0.0, fuel) / 100
        e.bar.color = (P["white"] if self.settings["colorblind"] else P["danger"]) if fuel < 30 else P["lit"]

    def _make_drifter(self, d):
        return Entity(parent=self.root, model="quad", double_sided=True, scale=(0.5, 1.8),
                      color=P["drifter"])

    def _upd_drifter(self, e, d):
        e.position = Vec3(*d["pos"])
        e.rotation_y = (time.time() * 240) % 360

    def _make_charm(self, c):
        e = Entity(parent=self.root, model="cube", scale=(0.5, 0.7, 0.08), color=P["scarf"],
                   position=Vec3(c["pos"][0], c["pos"][1] + 1, c["pos"][2]))
        Entity(parent=e, model="cube", scale=1.2, z=0.02, color=P["gold"])
        return e

    def _upd_charm(self, e, c):
        e.enabled = c["available"]
        e.rotation_y = (time.time() * 90) % 360

    def sync(self, g):
        self.now = time.time()
        self._sync(self.shades, g.shades, self._make_shade, self._upd_shade, "dyn")
        self._sync(self.motes, g.motes, self._make_mote, self._upd_mote, "motes")
        for grp, rbc in (("dyn", self.dyn_rbc), ("motes", self.mote_rbc)):
            if self.dirty[grp]:
                rbc.collect()
                self.dirty[grp] = False
        self._sync(self.lanterns, g.lanterns, self._make_lantern, self._upd_lantern)
        self._sync(self.drifters, g.drifters, self._make_drifter, self._upd_drifter)
        self._sync(self.charms, g.charms, self._make_charm, self._upd_charm)
        lit = sum(l["lit"] for l in g.lanterns)
        k = (0.15 + 0.55 * lit / len(g.lanterns)) / 0.70   # ambient intensity (Ticket-02)
        if k != self.last_k:
            self.last_k = k
            f = 0.35 + 0.65 * k
            self.static.setColorScale(f, f, f, 1)

    def destroy(self):
        destroy(self.root)


def make_map(n):
    return NIGHTS[n]()


class Mây(Entity):
    """Mây: áo trắng ngà, khăn đỏ, nón lá treo một chiếc đèn lồng nhỏ."""

    def __init__(self):
        super().__init__()
        Entity(parent=self, model="cube", scale=(0.6, 0.9, 0.4), y=0.45, color=P["shirt"])
        Entity(parent=self, model="cube", scale=(0.66, 0.14, 0.46), y=0.95, color=P["scarf"])
        Entity(parent=self, model="sphere", scale=0.45, y=1.25, color=hexc("#F1D2B6"))
        Entity(parent=self, model=Cone(16, radius=0.75, height=0.45), y=1.42, color=hexc("#E3CF95"))
        Entity(parent=self, model="cube", scale=(0.03, 0.35, 0.03), position=(0.6, 1.25, 0.2),
               color=P["wood"])
        self.lamp = Entity(parent=self, model="sphere", scale=0.2, position=(0.6, 1.05, 0.2),
                           color=P["lit"])
        self.trail = [Entity(parent=self, model="sphere", scale=0.1, color=P["mote"])
                      for _ in range(20)]


# =====================================================================================
class Sounds:
    def __init__(self, settings):
        self.settings = settings
        self.s = {}
        for name in ("pickup", "light", "pulse", "hit", "jump", "dash", "win", "lose", "shade",
                     "tick", "wind", "refuel"):
            try:
                self.s[name] = Audio(name, autoplay=False,
                                     loop=False)
            except Exception:  # noqa: BLE001 - audio is optional (headless CI, no device)
                pass
        try:
            self.music = Audio("music", loop=True, autoplay=False)
        except Exception:  # noqa: BLE001
            self.music = None

    def play(self, name):
        a = self.s.get(name)
        if a:
            a.volume = self.settings["volume"]
            a.play()

    def music_on(self, on):
        if self.music:
            self.music.volume = 0.5 * self.settings["volume"]
            if on and not self.music.playing:
                self.music.play()
            elif not on:
                self.music.stop()


def aim_camera(eye, target):
    """Place the camera at eye looking at target with no roll (yaw/pitch only)."""
    dx, dy, dz = target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]
    camera.position = Vec3(*eye)
    camera.rotation = Vec3(math.degrees(math.atan2(-dy, math.hypot(dx, dz))),
                           math.degrees(math.atan2(dx, dz)), 0)


DIM = Color(1, 1, 1, 0.15)


def settext(t, value):
    """Ursina rebuilds text geometry on every assignment: only assign on change."""
    if getattr(t, "_last", None) != value:
        t._last = value
        t.text = value


def setcolor(e, c):
    if getattr(e, "_lastc", None) != tuple(c):
        e._lastc = tuple(c)
        e.color = c


def ui_text(t, pos=(0, 0), scale=1.0, origin=(0, 0), col=None, parent=None, ts=1.0):
    # Text scale 1 == 0.025 * window height == 18 px at 720p (minimum required size)
    return Text(t, parent=parent or camera.ui, position=pos, origin=origin,
                scale=max(1.0, scale) * ts, color=col or P["ui"])


# =====================================================================================
class Controller(Entity):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.settings = storage.load_settings()
        self.tuning = config.load_tuning()
        self.snd = Sounds(self.settings)
        self.mode = "menu"
        self.panel = None
        self.world = None
        self.game = None
        self.may = None
        self.hud = None
        self.cam_yaw = 0.0
        self.acc = 0.0
        self.taps = set()
        self.night = 1
        self.total = 0
        self.nights_won = 0
        self.seed = random.randrange(1, 10 ** 6)
        self.subs = []
        self.shake = 0.0
        self.flash = Entity(parent=camera.ui, model="quad", scale=(4, 2), color=hexc("#FF5A5F"),
                            alpha=0.0, z=-1, enabled=False)
        self.waiting_key = None
        self.low_warned = set()
        self.last_tick_sec = None
        window.color = P["sky"]
        scene.fog_color = P["fog"]
        scene.fog_density = (25, 140)
        if getattr(args, "ui", None):
            if args.ui == "pause":
                self.night = args.night
                self.start_night()
                self.args.screenshot_after = args.screenshot
                self.args.screenshot = None
                self.show_pause()
            else:
                {"menu": self.show_menu, "leaderboard": self.show_leaderboard,
                 "name": self.show_name_entry,
                 "settings": lambda: self.show_settings(self.show_menu),
                 "keys": lambda: self.show_keys(self.show_menu)}[args.ui]()
            if getattr(args, "screenshot_after", None) or args.screenshot:
                from ursina import invoke
                invoke(self.save_shot, getattr(args, "screenshot_after", None) or args.screenshot, delay=1.5)
        elif args.screenshot or args.autoplay:
            self.night = args.night
            self.start_night()
            if getattr(args, "record", None):
                self.start_recording()
        else:
            self.show_menu()

    # ------------------------------------------------------------------ helpers
    @property
    def ts(self):
        return 1.25 if self.settings["large_text"] else 1.0

    def clear_panel(self):
        if self.panel:
            destroy(self.panel)
        self.panel = Entity(parent=camera.ui)
        mouse.locked = False
        return self.panel

    def button(self, label, y, fn, x=0, w=0.42):
        b = Button(parent=self.panel, text="", position=(x, y), scale=(w, 0.065),
                   color=Color(0.1, 0.12, 0.25, 0.9), highlight_color=hexc("#2A3570"))
        b.on_click = fn
        ui_text(label, pos=(x, y), parent=self.panel, ts=self.ts).z = -0.1
        return b

    def title(self, t, y=0.32, scale=2.2, col=None):
        return ui_text(t, pos=(0, y), scale=scale, parent=self.panel, col=col or P["gold"], ts=self.ts)

    # ------------------------------------------------------------------ screens
    def show_menu(self):
        self.end_world()
        self.mode = "menu"
        self.clear_panel()
        self.title("ĐẢO ĐÈN LỒNG", 0.3, 3)
        ui_text("Giữ đảo sáng tới bình minh", pos=(0, 0.2), parent=self.panel, ts=self.ts)
        self.button("Bắt đầu", 0.05, self.new_run)
        self.button("Bảng xếp hạng", -0.05, self.show_leaderboard)
        self.button("Cài đặt", -0.15, lambda: self.show_settings(self.show_menu))
        self.button("Thoát", -0.25, application.quit)

    def new_run(self):
        self.night, self.total, self.nights_won = 1, 0, 0
        self.seed = random.randrange(1, 10 ** 6)
        self.show_intro()

    def show_intro(self):
        self.end_world()
        self.mode = "intro"
        self.clear_panel()
        self.title(NAMES[self.night], 0.2)
        ui_text(ONG_DANG[self.night], pos=(0, 0.05), parent=self.panel, ts=self.ts)
        need = math.ceil(0.6 * len(NIGHTS[self.night].lanterns))
        ui_text("Mục tiêu: lúc bình minh có ít nhất %d/%d đèn đang sáng." % (need, len(NIGHTS[self.night].lanterns)),
                pos=(0, -0.03), parent=self.panel, ts=self.ts)
        self.button("Vào đêm", -0.18, self.start_night)

    def show_leaderboard(self):
        self.mode = "leaderboard"
        self.clear_panel()
        self.title("Bảng xếp hạng", 0.38)
        rows = storage.load_leaderboard()
        if not rows:
            ui_text("Chưa có ai. Hãy là người đầu tiên!", pos=(0, 0.15), parent=self.panel, ts=self.ts)
        for i, e in enumerate(rows):
            ui_text("%2d. %-12s %6d điểm  %d đêm  %s" % (i + 1, e["name"], e["score"], e["nights_won"],
                                                     e["achieved_at"][:16].replace("T", " ")),
                    pos=(-0.5, 0.27 - i * 0.052), origin=(-0.5, 0), parent=self.panel, ts=self.ts)
        self.button("Về menu", -0.4, self.show_menu)

    def show_settings(self, back):
        self.mode = "settings"
        self.clear_panel()
        s = self.settings
        self.title("Cài đặt", 0.4)

        def save():
            storage.save_settings(s)

        ui_text("Âm lượng", pos=(-0.45, 0.27), origin=(-0.5, 0), parent=self.panel, ts=self.ts)
        sv = Slider(0, 1, default=s["volume"], step=0.05, parent=self.panel, x=-0.05, y=0.27,
                    dynamic=True)

        def on_vol():
            s["volume"] = round(sv.value, 2)
            save()
        sv.on_value_changed = on_vol
        ui_text("Độ nhạy chuột", pos=(-0.45, 0.19), origin=(-0.5, 0), parent=self.panel, ts=self.ts)
        ss = Slider(0.2, 3, default=s["mouse_sensitivity"], step=0.1, parent=self.panel, x=-0.05,
                    y=0.19, dynamic=True)

        def on_sens():
            s["mouse_sensitivity"] = round(ss.value, 2)
            save()
        ss.on_value_changed = on_sens

        def toggle(key):
            s[key] = not s[key]
            save()
            self.show_settings(back)
        lab = lambda k, t: "%s: %s" % (t, "BẬT" if s[k] else "TẮT")  # noqa: E731
        self.button(lab("colorblind", "Bảng màu dễ phân biệt"), 0.08, lambda: toggle("colorblind"), w=0.7)
        self.button(lab("reduced_motion", "Giảm chuyển động"), -0.01, lambda: toggle("reduced_motion"), w=0.7)
        self.button(lab("large_text", "Chữ lớn (x1.25)"), -0.10, lambda: toggle("large_text"), w=0.7)
        self.button("Đổi phím", -0.21, lambda: self.show_keys(back), w=0.7)
        self.button("Quay lại", -0.34, back)

    def show_keys(self, back):
        self.mode = "keys"
        self.clear_panel()
        keys = self.settings["keys"]
        self.title("Đổi phím", 0.42)
        conflicts = storage.key_conflicts(keys)
        bad = {a for acts in conflicts.values() for a in acts}
        for i, a in enumerate(storage.ACTIONS):
            y = 0.32 - i * 0.065
            ui_text(ACTION_LABEL[a], pos=(-0.4, y), origin=(-0.5, 0), parent=self.panel, ts=self.ts,
                    col=P["danger"] if a in bad else None)
            label = "... nhấn phím ..." if self.waiting_key == a else keys[a].upper()
            self.button(label, y, (lambda act=a: self._wait_key(act, back)), x=0.2, w=0.32)
        msg = "  ".join("Trùng phím %s: %s" % (k.upper(), ", ".join(ACTION_LABEL[x] for x in v))
                        for k, v in conflicts.items())
        if msg:
            ui_text("(!) " + msg, pos=(0, -0.29), parent=self.panel, col=P["danger"], ts=self.ts)
        self.button("Khôi phục mặc định", -0.36, lambda: self._reset_keys(back), x=-0.24, w=0.44)
        self.button("Quay lại", -0.36, lambda: self.show_settings(back), x=0.24, w=0.3)

    def _wait_key(self, act, back):
        self.waiting_key = act
        self._keys_back = back
        self.show_keys(back)

    def _reset_keys(self, back):
        storage.reset_keys(self.settings)
        storage.save_settings(self.settings)
        self.show_keys(back)

    def show_pause(self):
        self.mode = "paused"
        self.clear_panel()
        Entity(parent=self.panel, model="quad", scale=(4, 2), color=Color(0, 0, 0, 0.55), z=0.1)
        self.title("Tạm dừng", 0.25)
        self.button("Tiếp tục", 0.08, self.resume)
        self.button("Chơi lại Đêm", -0.02, self.start_night)
        self.button("Cài đặt", -0.12, lambda: self.show_settings(self.show_pause))
        self.button("Về menu", -0.22, self.show_menu)

    def resume(self):
        destroy(self.panel)
        self.panel = None
        self.mode = "play"
        mouse.locked = True

    def show_result(self, won, reason):
        self.mode = "result"
        self.clear_panel()
        Entity(parent=self.panel, model="quad", scale=(4, 2), color=Color(0, 0, 0, 0.6), z=0.1)
        sc = self.game.score
        if won:
            self.total += sc
            self.nights_won += 1
            self.snd.play("win")
            if self.night == 3:
                return self.show_dawn()
            self.title("Bình minh! %s vượt qua" % NAMES[self.night], 0.2)
            ui_text("Điểm đêm: %d   ·   Tổng: %d" % (sc, self.total), pos=(0, 0.08), parent=self.panel,
                    ts=self.ts)
            self.button("Đêm kế tiếp", -0.08, self.next_night)
        else:
            self.snd.play("lose")
            why = {"no_flames": "Mây đã hết Ngọn Lửa.", "dawn": "Bình minh tới nhưng đảo chưa đủ sáng."}
            self.title("%s thất bại" % NAMES[self.night], 0.2, col=P["danger"])
            ui_text(why.get(reason, reason) + "   Tổng điểm: %d" % self.total, pos=(0, 0.08),
                    parent=self.panel, ts=self.ts)
            self.button("Chơi lại Đêm", -0.04, self.start_night)
            self.button("Lưu điểm", -0.14, self.show_name_entry)
            self.button("Về menu", -0.24, self.show_menu)

    def next_night(self):
        self.night += 1
        self.show_intro()

    def show_dawn(self):
        self.clear_panel()
        Entity(parent=self.panel, model="quad", scale=(4, 2), color=hexc("#FFB347", 0.25), z=0.1)
        self.title("BÌNH MINH", 0.25, 3)
        ui_text("Mây đã giữ cả ba hòn đảo sáng tới sáng. Tổng điểm: %d" % self.total, pos=(0, 0.1),
                parent=self.panel, ts=self.ts)
        self.button("Lưu điểm", -0.06, self.show_name_entry)
        self.button("Về menu", -0.16, self.show_menu)

    def show_name_entry(self):
        self.mode = "name"
        self.clear_panel()
        self.title("Lưu điểm: %d" % self.total, 0.25)
        ui_text("Tên 3–12 ký tự: chữ, số, _ (có dấu tiếng Việt cũng được)", pos=(0, 0.13),
                parent=self.panel, ts=self.ts)
        field = InputField(parent=self.panel, y=0.04, character_limit=12)
        err = ui_text("", pos=(0, -0.05), parent=self.panel, col=P["danger"], ts=self.ts)

        def submit():
            name = field.text.strip()
            if not storage.valid_name(name):
                err.text = "(!) Tên không hợp lệ"
                return
            storage.add_score(name, self.total, self.nights_won, self.seed)
            self.show_leaderboard()
        self.button("Lưu", -0.15, submit)
        self.button("Bỏ qua", -0.25, self.show_menu)

    # ------------------------------------------------------------------ gameplay
    def end_world(self):
        if self.world:
            self.world.destroy()
            self.world = None
        for e in (self.may, self.hud.root if self.hud else None):
            if e:
                destroy(e)
        self.may = self.hud = None
        self.game = None
        self.snd.music_on(False)

    def start_night(self, scenario=None):
        self.end_world()
        if self.panel:
            destroy(self.panel)
            self.panel = None
        self.game = Game(self.seed + self.night, self.tuning, night=self.night, scenario=scenario)
        self.world = World(self.night, self.settings)
        self.may = Mây()
        self.build_hud()
        self.acc = 0.0
        self.cam_yaw = 0.0
        self.low_warned = set()
        self.subs = []
        self.mode = "play"
        mouse.locked = not (self.args.screenshot or self.args.autoplay)
        self.snd.music_on(True)
        self.subtitle(NAMES[self.night], 3)
        import gc
        gc.collect()
        gc.freeze()

    def build_hud(self):
        ts = self.ts
        self.hud = h = SimpleNamespace(root=Entity(parent=camera.ui))
        ar = window.aspect_ratio
        h.flames = ui_text("Ngọn Lửa", pos=(-ar / 2 + 0.03, 0.46), origin=(-0.5, 0.5), scale=1.3, parent=h.root, ts=ts)
        h.flame_icons = [Entity(parent=h.root, model="circle", scale=0.035, color=P["lit"],
                                position=(-ar / 2 + 0.27 + i * 0.045, 0.437)) for i in range(3)]
        h.clock = ui_text("", pos=(0, 0.46), origin=(0, 0.5), scale=1.8, parent=h.root, ts=ts)
        h.right = ui_text("", pos=(ar / 2 - 0.03, 0.46), origin=(0.5, 0.5), scale=1.3, parent=h.root, ts=ts)
        h.cells = [Entity(parent=h.root, model="quad", scale=(0.028, 0.028), position=(-0.29 + i * 0.031, -0.44))
                   for i in range(20)]
        h.carry = ui_text("", pos=(0.36, -0.44), origin=(-0.5, 0), parent=h.root, ts=ts)
        h.cd = ui_text("", pos=(ar / 2 - 0.03, -0.44), origin=(0.5, 0), parent=h.root, ts=ts)
        h.prompt = ui_text("", pos=(0, -0.3), parent=h.root, ts=ts, col=P["core"])
        h.sub = ui_text("", pos=(0, -0.37), parent=h.root, ts=ts)
        h.arrow = Entity(parent=h.root, model=Mesh(vertices=[(0.03, 0, 0), (-0.02, 0.02, 0), (-0.02, -0.02, 0)],
                                              triangles=[0, 1, 2]), color=P["lit"])
        h.shade_arrow = Entity(parent=h.root, model=Mesh(vertices=[(0.035, 0, 0), (-0.02, 0.025, 0),
                                                              (-0.02, -0.025, 0)], triangles=[0, 1, 2]),
                               color=P["rim"])
        h.shade_arrow.enabled = False
        h.shade_target = None
        h.shade_until = 0

    def subtitle(self, msg, secs=3.0):
        for x in self.subs:
            if x[0] == msg:
                x[1] = time.time() + secs
                return
        self.subs.append([msg, time.time() + secs])

    def leaves(self):
        """Visual wind warning: a few leaves fly across the screen (2 s)."""
        for i in range(8):
            lf = Entity(parent=camera.ui, model="quad", scale=(0.03, 0.015), color=P["grass"],
                        position=(-0.9, random.uniform(-0.3, 0.4)), rotation_z=random.uniform(0, 360))
            lf.animate_x(0.9, duration=2 + i * 0.1)
            destroy(lf, delay=2.5)

    def read_input(self):
        k = self.settings["keys"]
        mx = (1 if held_keys[k["right"]] else 0) - (1 if held_keys[k["left"]] else 0)
        mz = (1 if held_keys[k["up"]] else 0) - (1 if held_keys[k["down"]] else 0)
        inp = {"move": [mx, mz], "cam_yaw_deg": self.cam_yaw}
        for a in ("jump", "dash", "interact", "pulse"):
            inp[a] = bool(held_keys[k[a]]) or a in self.taps or (a == "pulse" and held_keys["left mouse"])
        if self.args.autoplay or self.args.screenshot:
            inp.update(self.bot())
        return inp

    def bot(self):
        """Tiny autopilot for screenshots/demo: collect motes, light lanterns, pulse shades."""
        g, p = self.game, self.game.p
        pos = p["pos"]
        tgt = None
        if p["carried"] >= min(10, g.capacity) or not g.motes:
            ls = [l for l in g.lanterns if not (l["lit"] and l["fuel"] >= 6000)]
            if ls:
                tgt = min(ls, key=lambda l: math.dist(pos, l["pos"]))["pos"]
        elif g.motes:
            tgt = min(g.motes, key=lambda m: math.dist(pos, m["pos"]))["pos"]
        out = {"move": [0, 0], "cam_yaw_deg": 0.0, "interact": g.tick % 20 == 0,
               "pulse": any(math.dist(pos, s["pos"]) < 4 for s in g.shades) and g.tick % 30 == 0}
        if tgt:
            dx, dz = tgt[0] - pos[0], tgt[2] - pos[2]
            d = math.hypot(dx, dz) or 1
            out["move"] = [dx / d, dz / d]
        if tgt:
            want = math.degrees(math.atan2(out["move"][0], out["move"][1]))
            diff = (want - self.cam_yaw + 180) % 360 - 180
            self.cam_yaw += diff * 0.12   # smooth turn for a watchable camera
        out["move"] = [0, 1] if tgt else [0, 0]
        out["cam_yaw_deg"] = self.cam_yaw
        return out

    def handle_events(self, evs):
        for e in evs:
            n, d = e["name"], e["data"]
            if n == "mote_picked":
                self.snd.play("pickup")
            elif n == "lantern_lit":
                self.snd.play("light")
                self.subtitle("Đèn %s %s!" % (d["lantern_id"], "sáng lại" if d.get("relight") else "đã sáng"))
                self.low_warned.discard(d["lantern_id"])
            elif n == "refuel":
                self.snd.play("refuel")
                self.low_warned.discard(d["lantern_id"])
            elif n == "pulse":
                self.snd.play("pulse")
            elif n == "player_hit":
                self.snd.play("hit")
                if not self.settings["reduced_motion"]:
                    self.shake = 0.35
                    self.flash.enabled = True
                    self.flash.alpha = 0.35
                self.subtitle("Mây bị %s! Còn %d Ngọn Lửa" % ("rơi khỏi đảo" if d["by"] == "fall" else "Bóng Mực chạm",
                                                             d["flames"]))
            elif n == "dash":
                self.snd.play("dash")
            elif n == "shade_spawned":
                self.snd.play("shade")
                self.subtitle("(!) Bóng Mực xuất hiện")
                self.hud.shade_target = d["id"]
                self.hud.shade_until = time.time() + 3
            elif n == "lantern_out":
                self.subtitle("Đèn %s đã tắt!" % d["lantern_id"])
            elif n == "drifter_steal":
                self.subtitle("Gió Lạc cướp %d đom đóm!" % d["amount"])
            elif n == "charm_picked":
                self.subtitle("Bùa Gió: chạy nhanh, lướt liên tục 10 giây")
            elif n == "game_over":
                self.show_result(d["result"] == "won", d["reason"])

    def update(self):
        if getattr(self.args, "record", None):
            self._rec_frames = getattr(self, "_rec_frames", 0) + 1
            if self._rec_frames > int(self.args.record_seconds * 30) + 2:
                return application.quit()
        if self.mode == "bench":
            return self.bench_update()
        if self.mode != "play" or not self.game:
            return
        if mouse.locked:
            self.cam_yaw += mouse.velocity[0] * 120 * self.settings["mouse_sensitivity"]
        self.acc = min(self.acc + time.dt, 5 * STEP)
        while self.acc >= STEP and self.mode == "play":
            self.acc -= STEP
            self.game.step(self.read_input())
            self.taps.clear()
            self.handle_events(self.game.drain_events())
            if self.game is None:
                return
        if self.game is None:
            return
        self.render_frame()
        if self.args.screenshot and self.game.tick >= 60 * 6:
            self.save_shot(self.args.screenshot)

    def render_frame(self):
        g = self.game
        self.world.sync(g)
        p = g.p
        self.may.position = Vec3(*p["pos"])
        self.may.rotation_y = math.degrees(math.atan2(p["facing"][0], p["facing"][1]))
        for i, t in enumerate(self.may.trail):
            t.enabled = i < p["carried"]
            a = time.time() * 2 + i * 0.9
            t.position = (0.9 * math.cos(a), 1.0 + 0.3 * math.sin(a * 1.7), 0.9 * math.sin(a))
        yaw = math.radians(self.cam_yaw)
        fx, fz = math.sin(yaw), math.cos(yaw)
        sh = (random.uniform(-1, 1) * self.shake) if self.shake > 0 else 0
        self.shake = max(0, self.shake - time.dt)
        aim_camera((p["pos"][0] - fx * 9 + sh, p["pos"][1] + 4.0, p["pos"][2] - fz * 9),
                   (p["pos"][0] + fx * 4, p["pos"][1] + 1.5, p["pos"][2] + fz * 4))
        a = max(0.0, self.flash.alpha - time.dt)
        self.flash.alpha = a
        if getattr(self.args, "overview", False):
            aim_camera((0, 70, -75), (0, 0, 5))
        self.flash.enabled = a > 0.01
        self.update_hud()

    def update_hud(self):
        g, h, s = self.game, self.hud, self.settings
        danger = P["white"] if s["colorblind"] else P["danger"]
        warn = "(!) " if s["colorblind"] else ""
        for i, f in enumerate(h.flame_icons):
            setcolor(f, P["lit"] if i < g.p["flames"] else DIM)
        tl = max(0, g.time_left)
        settext(h.clock, "%s%02d:%02d" % (warn if tl <= 30 else "", int(tl) // 60, int(tl) % 60))
        setcolor(h.clock, danger if tl <= 30 and (s["reduced_motion"] or time.time() % 0.8 < 0.55)
                 else (Color(danger[0], danger[1], danger[2], 0.45) if tl <= 30 else P["ui"]))
        lit = sum(l["lit"] for l in g.lanterns)
        settext(h.right, "Đèn %d/%d    Điểm %d" % (lit, len(g.lanterns), g.score + self.total))
        cap = g.capacity
        for i, c in enumerate(h.cells):
            if c.enabled != (i < cap):
                c.enabled = i < cap
            setcolor(c, P["halo"] if i < g.p["carried"] else DIM)
        settext(h.carry, "%d/%d" % (g.p["carried"], cap))
        dcd, pcd = g.p["dash_cd"] / 60, g.p["pulse_cd"] / 60
        settext(h.cd, "Lướt %s   Tỏa Sáng %s" % ("SẴN" if dcd == 0 else "%.1fs" % dcd,
                                             "SẴN" if pcd == 0 else "%.1fs" % pcd))
        # interact prompt
        key = s["keys"]["interact"].upper()
        prompt = ""
        for l in g.lanterns:
            if math.hypot(l["pos"][0] - g.p["pos"][0], l["pos"][2] - g.p["pos"][2]) <= 2.0:
                if not l["lit"]:
                    cost = 5 if l["ever_lit"] else 10
                    prompt = "%s — Nạp ánh sáng (%d/%d)" % (key, l["deposited"], cost)
                elif l["fuel"] < 6000:
                    prompt = "%s — Châm dầu (%d/100)" % (key, l["fuel"] // 60)
        settext(h.prompt, prompt)
        # subtitles / visual cues
        now = time.time()
        if g.night == 3 and g.wind_enabled and not g.wind["active"] and g.sim_tick % 1800 >= 1680:
            if not getattr(self, "_wind_warned", False):
                self.subtitle("Gió sắp thổi!", 2)
                self.leaves()
                self.snd.play("wind")
                self._wind_warned = True
        else:
            self._wind_warned = False
        sec = int(tl)
        if 0 < tl <= 10 and sec != self.last_tick_sec:
            self.last_tick_sec = sec
            self.snd.play("tick")
            if sec == 10:
                self.subtitle(warn + "Còn 10 giây tới bình minh!")
        for l in g.lanterns:
            if l["lit"] and l["fuel"] < 30 * FU and l["id"] not in self.low_warned:
                self.low_warned.add(l["id"])
                self.subtitle(warn + "Đèn %s sắp cạn dầu!" % l["id"])
        self.subs = [x for x in self.subs if x[1] > now]
        settext(h.sub, chr(10).join(x[0] for x in self.subs[-3:]))
        # arrow to nearest unlit lantern when it is off-screen
        unlit = [l for l in g.lanterns if not l["lit"]]
        self._edge_arrow(h.arrow, min(unlit, key=lambda l: math.dist(l["pos"], g.p["pos"]))["pos"]
                         if unlit else None)
        tgt = None
        if h.shade_target and now < h.shade_until:
            ss = [x for x in g.shades if x["id"] == h.shade_target]
            tgt = ss[0]["pos"] if ss else None
        h.shade_arrow.color = P["rim_cb"] if s["colorblind"] else P["rim"]
        self._edge_arrow(h.shade_arrow, tgt, force=True)

    def _edge_arrow(self, arrow, wpos, force=False):
        if wpos is None:
            arrow.enabled = False
            return
        rel = Vec3(*wpos) - camera.world_position
        fwd, right, up = camera.forward, camera.right, camera.up
        z = rel.dot(fwd)
        x, y = rel.dot(right), rel.dot(up)
        on_screen = z > 0 and abs(x / max(z, 1e-3)) < 0.9 and abs(y / max(z, 1e-3)) < 0.5
        if on_screen and not force:
            arrow.enabled = False
            return
        if on_screen and force:
            arrow.enabled = False
            return
        ang = math.atan2(y, x if z > 0 else -abs(x) if x < 0 else abs(x))
        ar = window.aspect_ratio
        arrow.enabled = True
        arrow.position = (math.cos(ang) * (ar / 2 - 0.06), math.sin(ang) * 0.42)
        arrow.rotation_z = -math.degrees(ang)

    def start_recording(self):
        """Fixed 30 fps frame capture (game clock advances 1/30 s per frame) -> PREFIX_0000.png..."""
        from ursina import invoke
        base = application.base
        from panda3d.core import Filename
        base.movie(namePrefix=Filename.fromOsSpecific(os.path.abspath(self.args.record)).getFullpath(), duration=self.args.record_seconds, fps=30,
                   format="png", sd=4)
        # quit by captured frame count (not wall clock) so slow PNG writes never shorten a clip

    def save_shot(self, path):
        from panda3d.core import Filename
        application.base.win.saveScreenshot(Filename.fromOsSpecific(os.path.abspath(path)))
        application.quit()

    # ------------------------------------------------------------------ input
    def input(self, key):
        if self.waiting_key and not key.endswith(" up") and "mouse" not in key and key != "scroll up":
            self.settings["keys"][self.waiting_key] = key
            self.waiting_key = None
            storage.save_settings(self.settings)
            return self.show_keys(self._keys_back)
        if self.mode == "play":
            k = self.settings["keys"]
            if key in (k["pause"], "p"):
                return self.show_pause()
            for a in ("jump", "dash", "interact", "pulse"):
                if key == k[a]:
                    self.taps.add(a)   # latch: a tap shorter than one tick still counts
        elif self.mode == "paused" and key in (self.settings["keys"]["pause"], "p"):
            self.resume()
        elif self.mode == "intro" and key in ("enter", "space"):
            self.start_night()

    # ------------------------------------------------------------------ benchmark
    def start_bench(self):
        self.mode = "bench"
        self.game = bench_scene.make_bench_game(self.args.seed, self.tuning)
        self.world = World(1, self.settings)
        self.may = Mây()
        self.build_hud()
        self.snd.music_on(True)
        self.acc = 0.0
        self.t0 = None
        self.dts = []
        self.peak = 0.0
        self.last = None
        self.load_ms = None
        self.minimized_frames = 0
        self.keep_window_up()
        import gc
        gc.collect()
        gc.freeze()

    def keep_window_up(self):
        """Panda3D sleeps 0.1 s per frame while the main window is minimized: keep it restored
        and in front during the benchmark so the measurement reflects real rendering."""
        from panda3d.core import WindowProperties
        wp = WindowProperties()
        wp.setMinimized(False)
        wp.setForeground(True)
        application.base.win.requestProperties(wp)

    def bench_update(self):
        now = time.perf_counter()
        if application.base.mainWinMinimized:
            self.minimized_frames = getattr(self, "minimized_frames", 0) + 1
            self.keep_window_up()
        if self.load_ms is None:
            st = process_start_epoch()
            self.load_ms = int(round((time.time() - st) * 1000)) if st else int(round((now - T_IMPORT) * 1000))
            self.t0 = now
        dt = None if self.last is None else (now - self.last) * 1000.0
        self.last = now
        el = now - self.t0
        self.acc = min(self.acc + time.dt, 5 * STEP)
        while self.acc >= STEP:
            self.acc -= STEP
            self.game.step({"move": [0, 0], "cam_yaw_deg": 0.0})
            self.game.drain_events()
        self.world.sync(self.game)
        self.may.position = Vec3(0, 0, 0)
        aim_camera(bench_scene.camera_pose(el), (0, 0, 0))
        self.update_hud()
        if el >= 3.0 and dt is not None:
            self.dts.append(dt)
            m = rss_mb()
            if m:
                self.peak = max(self.peak, m)
        if self.args.screenshot and el >= 5.0:
            return self.save_shot(self.args.screenshot)
        if el >= 3.0 + self.args.duration:
            self.finish_bench()

    def finish_bench(self):
        from panda3d.core import PandaSystem
        import ursina
        stats = bench_scene.frame_stats(self.dts)
        try:
            gsg = application.base.win.getGsg()
            gpu = "%s / %s" % (gsg.getDriverRenderer(), gsg.getDriverVersion())
        except Exception:  # noqa: BLE001
            gpu = "unknown"
        out = {"contract_version": "1.3", **{k: stats[k] for k in ("avg_fps", "p1_low_fps", "frame_ms_p95", "frames")},
               "load_ms": self.load_ms, "peak_mem_mb": round(self.peak, 1) if self.peak else None,
               "vsync_off": True,
               "renderer": "Ursina %s / Panda3D %s / OpenGL %s" % (ursina.__version__ if hasattr(ursina, "__version__") else "7.0.0",
                                                                   PandaSystem.getVersionString(), gpu),
               "os": "%s %s (%s), Python %s" % (platform.system(), platform.release(), platform.machine(),
                                               platform.python_version()),
               "window": [1280, 720], "duration_s": self.args.duration, "seed": self.args.seed,
               "minimized_frames": self.minimized_frames}
        with open(self.args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
            f.write("\n")
        print(json.dumps(out))
        application.quit()


T_IMPORT = time.perf_counter()


def run(args):
    from panda3d.core import loadPrcFileData
    loadPrcFileData("", "sync-video false")   # vsync off
    loadPrcFileData("", "win-size 1280 720")
    loadPrcFileData("", "audio-library-name p3openal_audio")
    try:
        app = Ursina(title="Đảo Đèn Lồng", size=(1280, 720), borderless=False, fullscreen=False,
                     vsync=False, development_mode=False, show_ursina_splash=False)
    except TypeError:
        app = Ursina(title="Đảo Đèn Lồng", borderless=False, fullscreen=False, vsync=False,
                     development_mode=False)
    application.asset_folder = ASSETS
    camera.fov = 70
    window.size = (1280, 720)
    window.fps_counter.enabled = False
    window.exit_button.visible = False
    window.cog_button.enabled = False if hasattr(window, "cog_button") else None
    ctl = Controller(args) if not args.bench else Controller.__new__(Controller)
    if args.bench:
        Entity.__init__(ctl)
        ctl.args = args
        ctl.settings = storage.load_settings()
        ctl.settings.update(colorblind=False, reduced_motion=False, large_text=False)
        ctl.tuning = config.load_tuning()
        ctl.snd = Sounds(ctl.settings)
        ctl.subs, ctl.low_warned, ctl.last_tick_sec, ctl.total = [], set(), None, 0
        ctl.flash = Entity(parent=camera.ui, model="quad", scale=(4, 2), color=hexc("#FF5A5F"),
                           alpha=0.0, enabled=False)
        window.color = P["sky"]
        scene.fog_color = P["fog"]
        scene.fog_density = (25, 140)
        ctl.waiting_key = None
        ctl.panel = None
        ctl.start_bench()
        if getattr(args, "record", None):
            from panda3d.core import Filename
            application.base.movie(namePrefix=Filename.fromOsSpecific(os.path.abspath(args.record)).getFullpath(), duration=args.record_seconds, fps=30,
                                   format="png", sd=4)
            pass  # quits by frame count in Controller.update
    app.run()
    return 0
