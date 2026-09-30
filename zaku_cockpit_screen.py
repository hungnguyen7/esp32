"""
zaku_cockpit_screen.py - Char's Zaku II (MS-06S) cockpit view, Zeon style.

Amber HUD on black, Zeon red accents, olive military console. The target is
the RX-78-2. Like cockpit_screen, draw_screen() paints the full frame once and
tick() redraws only the animated regions:
  mono-eye scanner, fan radar sweep, bobbing Gundam in a rotating lock ring,
  blinking WARNING / lamps, closing range, speed/alt pointers, gauges,
  mission clock, Zaku MG tracer bursts and incoming beam hits.

Layout:
  y=0   top strip: MS-06S ZAKU II, mission clock, lamps
  y=18  monitor: stars, lunar surface, mono-eye rail, reticle, target ring
  y=180 console: fan radar, weapons / propellant, warning plates
"""
import math
import time
import gundam_theme as gt
import gundam_screen as gs
import cockpit_screen as ck

try:
    import urandom as random
except ImportError:
    import random

AMBER     = const(0xFD60)  # Zeon HUD amber     #FFAC00
AMBER_DIM = const(0x61E0)  # radar field        #603C00
ZEON_RED  = const(0xB003)  # Zeon red           #B00018
ZEON_DK   = const(0x5001)  # dark Zeon red      #500008
OLIVE     = const(0x29A4)  # console olive      #2C3420
OLIVE_LT  = const(0x5307)  # bezel olive        #56603E
MOON      = const(0x6B6E)  # lunar gray         #6C6C70
CRATER    = const(0x4A49)  # crater shadow      #48484C
MONO      = const(0xFB16)  # mono-eye pink      #FF60B0
BEAM      = const(0xFB16)
DIM_RED   = const(0x7800)

MON_Y, MON_H, CONSOLE_Y = 18, 160, 180

RET_X, RET_Y = 120, 100                 # Zeon circular reticle
ZX, ZY = 196, 54                        # RX-78-2 sprite origin (before bob)
ZW, ZH = 44, 52
RING_X, RING_Y, RING_R = 218, 80, 40    # target lock ring
RAIL_X, RAIL_Y, RAIL_W = 70, 24, 180    # mono-eye scanner rail
FAN_X, FAN_Y, FAN_R = 46, 236, 40       # fan radar (upper half circle)
BLIP_ANGLE = 0.9
SCALE_TOP, SCALE_BOT = 48, 140          # side speed / alt scales
LAMP_X = 268

_st = {}


# -- Static layers ------------------------------------------------------------

def _moon(disp):
    cx, cy, r = 160, 470, 320
    top = cy - r
    for y in range(top, MON_Y + MON_H):
        half = int(math.sqrt(r * r - (cy - y) * (cy - y)))
        x0 = max(cx - half, 2)
        disp.fill_rect(x0, y, min(cx + half, 318) - x0, 1, gt.ARMOR if y == top else MOON)
    for x, y, w in ((96, 156, 18), (150, 164, 26), (214, 158, 14), (40, 170, 22),
                    (250, 168, 20), (120, 172, 12)):
        disp.fill_rect(x + 2, y, w - 4, 1, CRATER)
        disp.fill_rect(x, y + 1, w, 2, CRATER)
        disp.fill_rect(x + 2, y + 3, w - 4, 1, gt.ARMOR)


def _circle_points(cx, cy, r, step_deg):
    pts = []
    for d in range(0, 360, step_deg):
        a = math.radians(d)
        pts.append((cx + int(r * math.cos(a)), cy - int(r * math.sin(a))))
    return pts


RET_PTS = _circle_points(RET_X, RET_Y, 18, 12)
RING_PTS = _circle_points(RING_X, RING_Y, RING_R, 15)


def _reticle(disp):
    for x, y in RET_PTS:
        disp.fill_rect(x, y, 2, 2, AMBER)
    cx, cy = RET_X, RET_Y
    disp.fill_rect(cx - 30, cy, 10, 2, AMBER)
    disp.fill_rect(cx + 21, cy, 10, 2, AMBER)
    disp.fill_rect(cx, cy - 30, 2, 10, AMBER)
    disp.fill_rect(cx, cy + 21, 2, 10, AMBER)
    disp.fill_rect(cx - 1, cy - 1, 4, 4, ZEON_RED)


def _ring(disp, angle):
    for x, y in RING_PTS:
        disp.fill_rect(x, y, 2, 2, ZEON_RED)
    for k in range(4):
        a = angle + k * math.pi / 2
        x = RING_X + int((RING_R + 4) * math.cos(a))
        y = RING_Y - int((RING_R + 4) * math.sin(a))
        disp.fill_rect(x - 2, y - 2, 5, 5, gt.RED)


def _ring_markers_erase(disp, angle):
    for k in range(4):
        a = angle + k * math.pi / 2
        x = RING_X + int((RING_R + 4) * math.cos(a))
        y = RING_Y - int((RING_R + 4) * math.sin(a))
        disp.fill_rect(x - 2, y - 2, 5, 5, gt.BG)


def _scales(disp):
    for x, label in ((30, "SPD"), (288, "ALT")):
        disp.fill_rect(x, SCALE_TOP, 1, SCALE_BOT - SCALE_TOP, AMBER)
        for y in range(SCALE_TOP, SCALE_BOT + 1, 10):
            w = 6 if (y - SCALE_TOP) % 20 == 0 else 3
            disp.fill_rect(x - w if x < 160 else x + 1, y, w, 1, AMBER)
        disp.draw_text(label, x - 12, SCALE_BOT + 4, AMBER, gt.BG, scale=1)


def _scale_pointer(disp, x, value, old):
    """Triangle pointer next to a side scale; value 0..1 maps bottom..top."""
    side = 4 if x < 160 else -8
    for v, color in ((old, gt.BG), (value, AMBER)):
        if v is None:
            continue
        y = SCALE_BOT - int((SCALE_BOT - SCALE_TOP) * v)
        disp.fill_rect(x + side, y - 3, 2, 7, color)
        disp.fill_rect(x + side + (2 if side > 0 else -2), y - 2, 2, 5, color)
        disp.fill_rect(x + side + (4 if side > 0 else -4), y - 1, 2, 3, color)


def _rail(disp):
    disp.fill_rect(RAIL_X, RAIL_Y, RAIL_W, 9, gt.BLACK)
    disp.fill_rect(RAIL_X, RAIL_Y, RAIL_W, 1, ZEON_RED)
    disp.fill_rect(RAIL_X, RAIL_Y + 8, RAIL_W, 1, ZEON_RED)
    disp.draw_text("MONO-EYE", RAIL_X - 66, RAIL_Y + 1, AMBER, gt.BG, scale=1)


def _mono_eye(disp, x, old_x):
    if old_x is not None:
        disp.fill_rect(old_x - 4, RAIL_Y + 1, 10, 7, gt.BLACK)
    disp.fill_rect(x - 4, RAIL_Y + 2, 10, 5, ZEON_RED)
    disp.fill_rect(x - 2, RAIL_Y + 1, 6, 7, MONO)
    disp.fill_rect(x, RAIL_Y + 3, 2, 3, gt.ARMOR)


def _monitor(disp):
    disp.fill_rect(0, MON_Y, gt.SCREEN_W, MON_H, gt.BG)
    ck._draw_stars(disp)
    _moon(disp)
    _scales(disp)
    _rail(disp)
    _reticle(disp)
    disp.draw_text("RX-78-2", ZX - 6, RING_Y + RING_R + 6, gt.RED, gt.BG, scale=1)
    for r in (0, 1):
        disp.rect(r, MON_Y + r, gt.SCREEN_W - 2 * r, MON_H - 2 * r, OLIVE_LT)


def _fan_base(disp):
    cx, cy, r = FAN_X, FAN_Y, FAN_R
    for dy in range(-r, 1):
        half = int(math.sqrt(r * r - dy * dy))
        disp.fill_rect(cx - half, cy + dy, 2 * half + 1, 1, AMBER_DIM)
        disp.fill_rect(cx - half, cy + dy, 1, 1, AMBER)
        disp.fill_rect(cx + half, cy + dy, 1, 1, AMBER)
    _fan_axes(disp)


def _fan_axes(disp):
    cx, cy, r = FAN_X, FAN_Y, FAN_R
    disp.fill_rect(cx - r, cy, 2 * r + 1, 1, AMBER)
    disp.fill_rect(cx, cy - r, 1, r, AMBER)
    for rr in (14, 28):                                   # range marks on baseline
        disp.fill_rect(cx - rr, cy - 2, 1, 2, AMBER)
        disp.fill_rect(cx + rr, cy - 2, 1, 2, AMBER)
    disp.fill_rect(cx - 1, cy - 2, 3, 3, gt.ARMOR)


def _console(disp):
    disp.fill_rect(0, CONSOLE_Y, gt.SCREEN_W, gt.SCREEN_H - CONSOLE_Y, OLIVE)
    disp.fill_rect(0, CONSOLE_Y, gt.SCREEN_W, 1, OLIVE_LT)
    for x in (4, 312):                                     # rivets
        for y in (184, 232):
            disp.fill_rect(x, y, 3, 3, OLIVE_LT)
    _fan_base(disp)
    disp.draw_text("ZAKU MG", 96, 186, AMBER, OLIVE, scale=1)
    disp.draw_text("PROPEL", 96, 200, gt.ARMOR, OLIVE, scale=1)
    disp.draw_text("GEN", 96, 214, gt.ARMOR, OLIVE, scale=1)
    disp.draw_text("HEAT HAWK RDY", 96, 228, gt.MUTED, OLIVE, scale=1)
    gt.tag(disp, 244, 202, "RX-78", gt.YELLOW, fg=gt.BLACK)
    gt.tag(disp, 244, 220, "ZEON", ZEON_RED, fg=AMBER)


def _top_strip(disp):
    disp.fill_rect(0, 0, gt.SCREEN_W, MON_Y, ZEON_DK)
    disp.draw_text("MS-06S", 4, 5, AMBER, ZEON_DK, scale=1)
    disp.draw_text("ZAKU II", 60, 5, gt.ARMOR, ZEON_DK, scale=1)
    disp.draw_text("CHAR", 124, 5, gt.MUTED, ZEON_DK, scale=1)
    gt.chamfer_rect(disp, LAMP_X, 4, 10, 10, AMBER, cut=2)
    gt.chamfer_rect(disp, LAMP_X + 12, 4, 10, 10, AMBER, cut=2)


# -- Animated elements --------------------------------------------------------

def _fan_points(angle):
    ca, sa = math.cos(angle), math.sin(angle)
    return [(FAN_X + int(ca * d), FAN_Y - int(sa * d)) for d in range(4, FAN_R - 2, 3)]


def _fan_blip(range_m):
    d = 6 + int(30 * range_m / 1500)
    return FAN_X + int(math.cos(BLIP_ANGLE) * d), FAN_Y - int(math.sin(BLIP_ANGLE) * d)


def _update_fan(disp, st):
    for x, y in st["sweep"]:
        disp.fill_rect(x, y, 2, 2, AMBER_DIM)
    bx, by = st["blip"]
    disp.fill_rect(bx - 1, by - 1, 3, 3, AMBER_DIM)
    a = st["angle"] + 0.2 * st["dir"]
    if a >= math.pi or a <= 0:                     # ping-pong across the fan
        st["dir"] = -st["dir"]
        a = max(0.0, min(math.pi, a))
    st["angle"] = a
    st["sweep"] = _fan_points(a)
    st["blip"] = _fan_blip(st["range"])
    _fan_axes(disp)
    for x, y in st["sweep"]:
        disp.fill_rect(x, y, 2, 2, AMBER)
    lit = abs(a - BLIP_ANGLE) < 0.5
    bx, by = st["blip"]
    disp.fill_rect(bx - 1, by - 1, 3, 3, gt.RED if lit else DIM_RED)


def _draw_target(disp, st, new_y):
    old_y = st["zy"]
    if new_y > old_y:
        disp.fill_rect(ZX, old_y, ZW, new_y - old_y, gt.BG)
    elif new_y < old_y:
        disp.fill_rect(ZX, new_y + ZH, ZW, old_y - new_y, gt.BG)
    gs.draw_sprite(disp, gs.RX78, ZX, new_y, scale=1, bg=gt.BG, cache=True)
    st["zy"] = new_y


def _line(x0, y0, x1, y1, step):
    n = max(abs(x1 - x0), abs(y1 - y0)) // step or 1
    return [(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n) for i in range(n + 1)]


def _fire_mg(disp, st):
    """Tracer burst from the Zaku's gun (lower right) toward the Gundam."""
    pts = _line(262, 146, ZX + 30, st["zy"] + 40, 3)
    shots = [p for i, p in enumerate(pts) if i % 3 != 2]           # dashed tracers
    for x, y in shots:
        disp.fill_rect(x - 1, y - 1, 3, 3, gt.YELLOW)
    st["fx"] = shots
    st["ammo"] = st["ammo"] - 5 if st["ammo"] > 5 else 100
    disp.draw_text("{:3d}/100".format(st["ammo"]), 160, 186, gt.ARMOR, OLIVE, scale=1)


def _incoming_beam(disp, st):
    """Gundam beam rifle shot toward the viewer + red monitor flash."""
    pts = _line(ZX - 2, st["zy"] + 30, 64, 140, 2)
    for x, y in pts:
        disp.fill_rect(x - 1, y - 1, 3, 3, BEAM)
        disp.fill_rect(x, y, 1, 1, gt.ARMOR)
    for r in (0, 1):
        disp.rect(r, MON_Y + r, gt.SCREEN_W - 2 * r, MON_H - 2 * r, gt.RED)
    st["fx"] = pts
    st["hit"] = True


def _clear_fx(disp, st):
    pts = st["fx"]
    for x, y in pts:
        disp.fill_rect(x - 1, y - 1, 3, 3, gt.BG)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ck._draw_stars(disp, min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)
    _reticle(disp)
    _ring(disp, st["ring"])
    gs.draw_sprite(disp, gs.RX78, ZX, st["zy"], scale=1, bg=gt.BG, cache=True)
    disp.draw_text("RX-78-2", ZX - 6, RING_Y + RING_R + 6, gt.RED, gt.BG, scale=1)
    if st["hit"]:
        for r in (0, 1):
            disp.rect(r, MON_Y + r, gt.SCREEN_W - 2 * r, MON_H - 2 * r, OLIVE_LT)
        st["hit"] = False
    st["fx"] = None


def _gauge(disp, y, percent, color):
    bx, bw = 152, 80
    disp.fill_rect(bx, y, bw, 8, gt.BLACK)
    cells = bw * percent // 100
    cx = bx + 1
    while cx < bx + cells:
        disp.fill_rect(cx, y + 1, min(4, bx + cells - cx), 6, color)
        cx += 6


def _blink(disp, st):
    on = st["blink"] = not st["blink"]
    gt.tag(disp, 244, 184, "WARNING", gt.RED if on else ZEON_DK, fg=gt.ARMOR if on else DIM_RED)
    gt.chamfer_rect(disp, LAMP_X + 24, 4, 10, 10, gt.RED if on else DIM_RED, cut=2)
    gt.chamfer_rect(disp, LAMP_X + 36, 4, 10, 10, DIM_RED if on else gt.RED, cut=2)
    disp.draw_text("LOCKED" if on else "      ", 130, 42, gt.RED, gt.BG, scale=1)


def draw_screen(disp):
    _top_strip(disp)
    _monitor(disp)
    _console(disp)
    now = time.ticks_ms()
    _st.clear()
    _st.update({
        "start": now, "angle": 0.0, "dir": 1, "range": 1500, "ammo": 100,
        "prop": 74, "blink": False, "phase": 0.0, "zy": ZY, "ring": 0.0,
        "fx": None, "hit": False, "sweep": [], "blip": _fan_blip(1500),
        "eye": RAIL_X + 10, "eye_dir": 1, "spd": None, "alt": None,
        "t_fan": now - 100, "t_eye": now - 80, "t_blink": now - 400,
        "t_bob": now - 250, "t_range": now - 300, "t_gauge": now - 500,
        "t_clock": now - 1000, "t_mg": now, "t_beam": now, "t_fx": now,
    })
    gs.draw_sprite(disp, gs.RX78, ZX, ZY, scale=1, bg=gt.BG, cache=True)
    _ring(disp, 0.0)
    _mono_eye(disp, _st["eye"], None)
    disp.draw_text("100/100", 160, 186, gt.ARMOR, OLIVE, scale=1)
    tick(disp)


def tick(disp):
    """Advance the animation; cheap enough to call every main-loop pass."""
    st = _st
    if not st:
        return
    now = time.ticks_ms()

    if st["fx"] and ck._due(st, "t_fx", now, 150):
        _clear_fx(disp, st)

    if ck._due(st, "t_fan", now, 100):
        _update_fan(disp, st)

    if ck._due(st, "t_eye", now, 80):                    # mono-eye scanning
        old = st["eye"]
        x = old + 6 * st["eye_dir"]
        if x < RAIL_X + 6 or x > RAIL_X + RAIL_W - 8:
            st["eye_dir"] = -st["eye_dir"]
            x = old + 6 * st["eye_dir"]
        st["eye"] = x
        _mono_eye(disp, x, old)

    if ck._due(st, "t_blink", now, 400):
        _blink(disp, st)

    if ck._due(st, "t_bob", now, 250):
        _ring_markers_erase(disp, st["ring"])
        st["ring"] = (st["ring"] + 0.3) % (2 * math.pi)
        st["phase"] += 0.5
        new_y = ZY + int(round(3 * math.sin(st["phase"])))
        if new_y != st["zy"]:
            _draw_target(disp, st, new_y)
        _ring(disp, st["ring"])

    if ck._due(st, "t_range", now, 300):
        st["range"] -= 5 + random.getrandbits(4)
        if st["range"] < 400:
            st["range"] = 1500
        disp.draw_text("{:4d}m".format(st["range"]), ZX - 2, RING_Y + RING_R + 16, AMBER, gt.BG, scale=1)
        spd = min(1.0, 0.3 + (1500 - st["range"]) / 1600)
        alt = 0.5 + 0.3 * math.sin(st["phase"] * 0.4)
        _scale_pointer(disp, 30, spd, st["spd"])
        _scale_pointer(disp, 288, alt, st["alt"])
        st["spd"], st["alt"] = spd, alt

    if ck._due(st, "t_gauge", now, 500):
        st["prop"] = max(15, min(100, st["prop"] + random.getrandbits(3) - 5))
        _gauge(disp, 200, st["prop"], AMBER)
        _gauge(disp, 214, 55 + random.getrandbits(5), ZEON_RED)

    if not st["fx"]:
        if ck._due(st, "t_mg", now, 3000):
            _fire_mg(disp, st)
            st["t_fx"] = now
        elif ck._due(st, "t_beam", now, 7000):
            _incoming_beam(disp, st)
            st["t_fx"] = now

    if ck._due(st, "t_clock", now, 1000):
        secs = time.ticks_diff(now, st["start"]) // 1000
        disp.draw_text("T+{:02d}:{:02d}".format(secs // 60 % 100, secs % 60),
                       184, 5, AMBER, ZEON_DK, scale=1)
