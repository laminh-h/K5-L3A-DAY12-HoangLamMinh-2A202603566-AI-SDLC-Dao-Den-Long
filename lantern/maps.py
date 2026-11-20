"""Standard maps (Ticket-02 part 2). Angles from +X toward +Z: (r cos a, r sin a)."""
import math


def ring(r, start_deg, step_deg, n, y=0.0, cx=0.0):
    out = []
    for i in range(n):
        a = math.radians(start_deg + step_deg * i)
        out.append((cx + r * math.cos(a), y, r * math.sin(a)))
    return out


class Night:
    num = 0
    start = (0.0, 0.0, 0.0)
    pads = ()          # (center(x,y,z), vy, (vx, vz))
    wind = False
    tower = None       # (cx, cz, radius, top_y)

    def ground(self, x, z):
        raise NotImplementedError


class Night1(Night):
    num, name = 1, "Đảo Bến"
    duration_key = "night1_duration_s"
    lanterns = [(0, 0, 25), (23.8, 0, 7.7), (14.7, 0, -20.2), (-14.7, 0, -20.2), (-23.8, 0, 7.7)]
    mote_points = ring(12, 0, 45, 8) + ring(33, 0, 22.5, 16)
    shade_points = ring(37, 15, 30, 12)
    shade_interval, shade_max, shade_speed_mult = 480, 6, None
    charms = []

    def ground(self, x, z):
        return 0.0 if math.hypot(x, z) <= 40.0 else None


class Night2(Night):
    num, name = 2, "Đảo Cau"
    duration_key = "night2_duration_s"
    lanterns = [(0, 0, 20), (17, 0, -10), (-17, 0, -10), (70, 0, 20), (87, 0, -10), (53, 0, -10)]
    mote_points = (ring(10, 0, 90, 4) + ring(22, 0, 45, 8)
                   + ring(10, 0, 90, 4, cx=70) + ring(22, 0, 45, 8, cx=70))
    shade_points = ring(26, 22.5, 45, 8) + ring(26, 22.5, 45, 8, cx=70)
    shade_interval, shade_max = 420, 8
    charms = [(35, 0, 0)]

    def __init__(self):
        def toward(src, dst):
            dx, dz = dst[0] - src[0], dst[2] - src[2]
            d = math.hypot(dx, dz)
            return (24.0 * dx / d, 24.0 * dz / d)
        a, b = (20.0, 0.0, 18.0), (50.0, 0.0, -18.0)
        self.pads = ((a, 14.0, toward(a, (70, 0, 0))), (b, 14.0, toward(b, (0, 0, 0))))

    def ground(self, x, z):
        if math.hypot(x, z) <= 28 or math.hypot(x - 70, z) <= 28:
            return 0.0
        if 26 <= x <= 44 and -2 <= z <= 2:
            return 0.0
        return None


class Night3(Night):
    num, name = 3, "Đảo Chuông"
    duration_key = "night3_duration_s"
    start = (0.0, 0.0, -30.0)   # (0,0,0) is inside the tier-2 block / bell tower -> assumption
    lanterns = [(0, 6, 6), (18, 3, 10), (-18, 3, 10), (35, 0, -10), (-35, 0, -10),
                (20, 0, -35), (-20, 0, -35)]
    mote_points = (ring(34, 0, 20, 18) + ring(18, 20, 20, 8, y=3.0) + ring(5, 45, 90, 4, y=6.0))
    shade_points = ring(43, 0, 22.5, 16)
    shade_interval, shade_max = 360, 10
    charms = [(30, 0, 25), (-30, 0, 25)]
    pads = (((0.0, 3.0, 13.0), 12.0, (0.0, -8.0)),)
    wind = True
    tower = (0.0, 0.0, 2.0, 14.0)
    RAMPS = [math.radians(30), math.radians(150)]

    def ground(self, x, z):
        r = math.hypot(x, z)
        if r > 45:
            return None
        h = 0.0
        for a in self.RAMPS:
            ux, uz = math.cos(a), math.sin(a)
            s = x * ux + z * uz
            lat = abs(-x * uz + z * ux)
            if lat <= 1.5 and 24 <= s <= 30:
                h = max(h, 3.0 * (30 - s) / 6.0)
        if 12 <= r <= 24 and z > 0:
            h = max(h, 3.0)
        if r <= 8:
            h = max(h, 6.0)
        if r < 2:
            h = max(h, 14.0)
        return h


NIGHTS = {1: Night1, 2: Night2, 3: Night3}


def make_night(n):
    return NIGHTS[n]()
