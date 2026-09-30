"""
cockpit_screen.py - RX-78-2 cockpit view: panoramic monitor + control console.

draw_screen() paints the full frame once; tick() is called from the main
loop every ~100 ms and redraws only the small regions that animate:
  radar sweep + approaching blip, heading tape, bobbing Zaku with lock box,
  blinking LOCK ON / ALERT / lamps, closing range, E-CAP/THRUST gauges,
  mission clock, beam-rifle shots and Zaku muzzle flashes.

Layout:
  y=0   top strip: unit code, system name, mission clock, status lamps
  y=18  panoramic monitor: stars, Earth limb, heading tape, reticle, target
  y=180 console: radar, weapon/energy readouts, warning lamps
"""
import math
import time
import gundam_theme as gt
import gundam_screen as gs

try:
    import urandom as random
except ImportError:
    import random

HUD      = const(0x47F0)  # HUD green          #40FF80
HUD_DIM  = const(0x0B03)  # radar screen green #086018
EARTH    = const(0x1A7A)  # ocean blue         #184CD0
ATMOS    = const(0x7DFF)  # atmosphere glow    #78BCFF
STAR     = const(0xC618)  # dim star           #C0C0C0
DIM_RED  = const(0x7800)  # unlit red lamp     #780000
DIM_YEL  = const(0x7BC0)  # unlit yellow lamp  #787800
BEAM     = const(0xFB16)  # beam rifle pink    #FF60B0

MON_Y = 18
MON_H = 160
CONSOLE_Y = 180

RET_X, RET_Y = 140, 96                 # reticle centre
ZX, ZY = 200, 34                       # Zaku sprite origin (before bob)
ZW, ZH = 44, 52
TAPE_X, TAPE_Y, TAPE_W = 70, 22, 110   # heading tape
RADAR_X, RADAR_Y, RADAR_R = 32, 210, 24
BLIP_ANGLE = 1.0                       # radians, upper right
LAMP_X = 268


def _make_stars():
    """Fixed pseudo-random star field, kept so erased stars can be restored."""
    stars = []
    seed = 7
    for _ in range(46):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        x = seed % 316 + 2
        y = MON_Y + 4 + (seed >> 9) % 110
        size = 2 if (seed >> 20) % 5 == 0 else 1
        stars.append((x, y, size))
    return stars


STARS = _make_stars()
_st = {}  # animation state, reset by draw_screen


# -- Static layers ------------------------------------------------------------

def _draw_stars(disp, x0=0, y0=0, x1=319, y1=239):
    for x, y, size in STARS:
        if x0 <= x <= x1 and y0 <= y <= y1:
            disp.fill_rect(x, y, size, size, gt.ARMOR if size == 2 else STAR)


def _earth(disp):
    """Earth limb: a big circle centred below the monitor, with cloud streaks."""
    cx, cy, r = 160, 430, 300
    top = cy - r
    for y in range(top, MON_Y + MON_H):
        half = int(math.sqrt(r * r - (cy - y) * (cy - y)))
        x0 = max(cx - half, 2)
        w = min(cx + half, 318) - x0
        color = ATMOS if y - top < 2 else EARTH
        disp.fill_rect(x0, y, w, 1, color)
    for x, y, w in ((100, 142, 30), (110, 150, 44), (190, 140, 26), (220, 156, 40),
                    (40, 164, 34), (150, 166, 28), (250, 170, 30)):
        disp.fill_rect(x, y, w, 2, STAR)


def _reticle(disp):
    cx, cy = RET_X, RET_Y
    disp.fill_rect(cx - 24, cy, 16, 2, HUD)
    disp.fill_rect(cx + 9, cy, 16, 2, HUD)
    disp.fill_rect(cx, cy - 20, 2, 12, HUD)
    disp.fill_rect(cx, cy + 10, 2, 12, HUD)
    disp.fill_rect(cx - 1, cy - 1, 4, 4, HUD)
    for bx, by in ((cx - 30, cy - 26), (cx + 24, cy - 26), (cx - 30, cy + 20), (cx + 24, cy + 20)):
        disp.fill_rect(bx, by + (0 if by < cy else 6), 8, 1, HUD)      # reticle box corners
        disp.fill_rect(bx + (0 if bx < cx else 7), by, 1, 7, HUD)


def _ladder(disp):
    cy = RET_Y
    for dy in (-40, -20, 0, 20, 40):
        w = 14 if dy == 0 else 8
        disp.fill_rect(40, cy + dy, w, 1, HUD)
        disp.fill_rect(280 - w, cy + dy, w, 1, HUD)
        disp.draw_text("{:+d}".format(-dy // 2), 12, cy + dy - 3, HUD, gt.BG, scale=1)
    disp.fill_rect(56, cy - 44, 1, 90, HUD)
    disp.fill_rect(263, cy - 44, 1, 90, HUD)
    disp.draw_text("SPD", 284, cy - 20, HUD, gt.BG, scale=1)
    disp.draw_text("ALT", 284, cy + 12, HUD, gt.BG, scale=1)


def _corner_marks(disp):
    """Panoramic monitor corner accents."""
    for x, y, dx, dy in ((4, MON_Y + 4, 1, 1), (315, MON_Y + 4, -1, 1),
                         (4, MON_Y + MON_H - 5, 1, -1), (315, MON_Y + MON_H - 5, -1, -1)):
        disp.fill_rect(min(x, x + dx * 12), y, 12, 1, gt.MUTED)
        disp.fill_rect(x, min(y, y + dy * 12), 1, 12, gt.MUTED)


def _brackets(disp, x, y, w, h, color, arm=10):
    """Four corner brackets (target lock box)."""
    for bx, dx in ((x, 1), (x + w - 2, -1)):
        disp.fill_rect(min(bx, bx + dx * arm), y, arm, 2, color)
        disp.fill_rect(bx, y, 2, arm, color)
        disp.fill_rect(min(bx, bx + dx * arm), y + h - 2, arm, 2, color)
        disp.fill_rect(bx, y + h - arm, 2, arm, color)


def _monitor(disp):
    disp.fill_rect(0, MON_Y, gt.SCREEN_W, MON_H, gt.BG)
    _draw_stars(disp)
    _earth(disp)
    _ladder(disp)
    _reticle(disp)
    _corner_marks(disp)
    disp.draw_text("MS-06S", ZX - 6, ZY + 86, gt.RED, gt.BG, scale=1)
    disp.rect(0, MON_Y, gt.SCREEN_W, MON_H, gt.PANEL)
    disp.rect(1, MON_Y + 1, gt.SCREEN_W - 2, MON_H - 2, gt.PANEL)


def _radar_base(disp):
    cx, cy, r = RADAR_X, RADAR_Y, RADAR_R
    for dy in range(-r, r + 1):
        half = int(math.sqrt(r * r - dy * dy))
        disp.fill_rect(cx - half, cy + dy, 2 * half + 1, 1, HUD_DIM)
        disp.fill_rect(cx - half, cy + dy, 1, 1, HUD)
        disp.fill_rect(cx + half, cy + dy, 1, 1, HUD)
    _radar_axes(disp)


def _radar_axes(disp):
    cx, cy, r = RADAR_X, RADAR_Y, RADAR_R
    disp.fill_rect(cx - r, cy, 2 * r + 1, 1, HUD)
    disp.fill_rect(cx, cy - r, 1, 2 * r + 1, HUD)
    disp.fill_rect(cx - 1, cy - 1, 3, 3, gt.ARMOR)


def _console(disp):
    disp.fill_rect(0, CONSOLE_Y, gt.SCREEN_W, gt.SCREEN_H - CONSOLE_Y, gt.PANEL)
    disp.fill_rect(0, CONSOLE_Y, gt.SCREEN_W, 1, gt.MUTED)
    _radar_base(disp)
    disp.draw_text("BEAM RIFLE", 68, 186, gt.YELLOW, gt.PANEL, scale=1)
    disp.draw_text("E-CAP", 68, 202, gt.ARMOR, gt.PANEL, scale=1)
    disp.draw_text("THRUST", 68, 216, gt.ARMOR, gt.PANEL, scale=1)
    disp.draw_text("SHIELD OK", 68, 229, gt.MUTED, gt.PANEL, scale=1)
    gt.tag(disp, 244, 202, "MS-06S", gt.YELLOW, fg=gt.BLACK)
    gt.tag(disp, 244, 220, "SYS OK", HUD, fg=gt.BLACK)


def _top_strip(disp):
    disp.fill_rect(0, 0, gt.SCREEN_W, MON_Y, gt.PANEL)
    disp.draw_text("RX-78-2", 4, 5, gt.YELLOW, gt.PANEL, scale=1)
    disp.draw_text("CORE BLOCK SYS", 68, 5, gt.ARMOR, gt.PANEL, scale=1)
    gt.chamfer_rect(disp, LAMP_X, 4, 10, 10, HUD, cut=2)
    gt.chamfer_rect(disp, LAMP_X + 12, 4, 10, 10, HUD, cut=2)


# -- Animated elements --------------------------------------------------------

def _draw_tape(disp, heading):
    x0, y0, w = TAPE_X, TAPE_Y, TAPE_W
    cx = x0 + w // 2
    disp.fill_rect(x0, y0, w, 18, gt.BG)
    disp.fill_rect(x0, y0 + 17, w, 1, HUD)
    first = int(heading - 30) // 5 * 5
    for deg in range(first, int(heading) + 32, 5):
        x = cx + int((deg - heading) * 2)
        if x < x0 or x >= x0 + w:
            continue
        tall = deg % 15 == 0
        disp.fill_rect(x, y0 + (10 if tall else 13), 1, 7 if tall else 4, HUD)
        if deg % 30 == 0 and x0 <= x - 12 and x + 12 <= x0 + w:
            disp.draw_text("{:03d}".format(deg % 360), x - 12, y0, HUD, gt.BG, scale=1)
    disp.fill_rect(cx - 1, y0 + 18, 3, 3, gt.YELLOW)


def _sweep_points(angle):
    ca, sa = math.cos(angle), math.sin(angle)
    return [(RADAR_X + int(ca * d), RADAR_Y - int(sa * d)) for d in range(3, RADAR_R - 2, 3)]


def _blip_pos(range_m):
    d = 4 + int(18 * range_m / 1200)
    return RADAR_X + int(math.cos(BLIP_ANGLE) * d), RADAR_Y - int(math.sin(BLIP_ANGLE) * d)


def _update_radar(disp, st):
    for x, y in st["sweep"]:
        disp.fill_rect(x, y, 2, 2, HUD_DIM)
    bx, by = st["blip"]
    disp.fill_rect(bx - 1, by - 1, 3, 3, HUD_DIM)
    st["angle"] = (st["angle"] - 0.35) % (2 * math.pi)
    st["sweep"] = _sweep_points(st["angle"])
    st["blip"] = _blip_pos(st["range"])
    _radar_axes(disp)
    for x, y in st["sweep"]:
        disp.fill_rect(x, y, 2, 2, HUD)
    lit = (BLIP_ANGLE - st["angle"]) % (2 * math.pi) < 0.9
    bx, by = st["blip"]
    disp.fill_rect(bx - 1, by - 1, 3, 3, gt.RED if lit else DIM_RED)


def _draw_zaku(disp, st, new_y):
    old_y = st["zy"]
    if new_y > old_y:
        disp.fill_rect(ZX, old_y, ZW, new_y - old_y, gt.BG)
    elif new_y < old_y:
        disp.fill_rect(ZX, new_y + ZH, ZW, old_y - new_y, gt.BG)
    _brackets(disp, ZX - 6, old_y - 6, 56, 64, gt.BG)
    gs.draw_sprite(disp, gs.ZAKU, ZX, new_y, scale=1, bg=gt.BG, cache=True)
    _brackets(disp, ZX - 6, new_y - 6, 56, 64, gt.RED)
    st["zy"] = new_y


def _beam_points(st):
    x0, y0 = RET_X + 8, RET_Y - 8
    x1, y1 = ZX - 10, st["zy"] + 26
    n = max(abs(x1 - x0), abs(y1 - y0)) // 2        # 2px steps -> solid streak
    return [(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n) for i in range(n + 1)]


def _fire_beam(disp, st):
    pts = _beam_points(st)
    for x, y in pts:
        disp.fill_rect(x - 1, y - 1, 3, 3, BEAM)
        disp.fill_rect(x, y, 1, 1, gt.ARMOR)
    st["beam"] = pts
    st["ammo"] = st["ammo"] - 1 if st["ammo"] > 1 else 16
    disp.draw_text("{:2d}/16".format(st["ammo"]), 180, 186, HUD, gt.PANEL, scale=1)


def _clear_beam(disp, st):
    pts = st["beam"]
    for x, y in pts:
        disp.fill_rect(x - 1, y - 1, 3, 3, gt.BG)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    _draw_stars(disp, min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)
    _reticle(disp)
    st["beam"] = None


def _gauge(disp, y, percent, color):
    bx, bw = 124, 96
    disp.fill_rect(bx, y, bw, 8, gt.BLACK)
    cells = bw * percent // 100
    cx = bx + 1
    while cx < bx + cells:
        disp.fill_rect(cx, y + 1, min(6, bx + cells - cx), 6, color)
        cx += 8


def _blink(disp, st):
    on = st["blink"] = not st["blink"]
    disp.draw_text("LOCK ON" if on else "       ", ZX - 6, ZY + 64, gt.RED, gt.BG, scale=1)
    gt.tag(disp, 244, 184, "ALERT", gt.RED if on else DIM_RED)
    gt.chamfer_rect(disp, LAMP_X + 24, 4, 10, 10, gt.YELLOW if on else DIM_YEL, cut=2)
    gt.chamfer_rect(disp, LAMP_X + 36, 4, 10, 10, DIM_RED if on else gt.RED, cut=2)


def _due(st, key, now, period):
    if time.ticks_diff(now, st[key]) >= period:
        st[key] = now
        return True
    return False


def draw_screen(disp):
    _top_strip(disp)
    _monitor(disp)
    _console(disp)
    now = time.ticks_ms()
    _st.clear()
    _st.update({
        "start": now, "heading": 0.0, "angle": 0.0, "range": 1200,
        "ecap": 87, "ammo": 16, "blink": False, "phase": 0.0,
        "zy": ZY, "beam": None, "sweep": [], "blip": _blip_pos(1200),
        # stagger first updates so they don't all land on one tick
        "flash": False,
        # everything due on the first tick so the frame is complete at once
        "t_radar": now - 100, "t_tape": now - 100, "t_blink": now - 400,
        "t_bob": now - 250, "t_range": now - 300, "t_gauge": now - 500,
        "t_clock": now - 1000, "t_fire": now, "t_beam": now,
    })
    _draw_tape(disp, 0.0)
    gs.draw_sprite(disp, gs.ZAKU, ZX, ZY, scale=1, bg=gt.BG, cache=True)
    _brackets(disp, ZX - 6, ZY - 6, 56, 64, gt.RED)
    disp.draw_text("16/16", 180, 186, HUD, gt.PANEL, scale=1)
    _gauge(disp, 202, 87, gt.BLUE)
    _gauge(disp, 216, 62, gt.YELLOW)
    tick(disp)


def tick(disp):
    """Advance the animation; cheap enough to call every main-loop pass."""
    st = _st
    if not st:
        return
    now = time.ticks_ms()

    if st["beam"] and _due(st, "t_beam", now, 120):
        _clear_beam(disp, st)

    if _due(st, "t_radar", now, 100):
        _update_radar(disp, st)

    if _due(st, "t_tape", now, 200):
        st["heading"] = (st["heading"] + 1.0) % 360
        _draw_tape(disp, st["heading"])

    if _due(st, "t_blink", now, 400):
        _blink(disp, st)

    if _due(st, "t_bob", now, 250):
        st["phase"] += 0.6
        new_y = ZY + int(round(3 * math.sin(st["phase"])))
        if new_y != st["zy"] or st["flash"]:
            _draw_zaku(disp, st, new_y)
        st["flash"] = random.getrandbits(3) == 0                 # Zaku machine gun
        if st["flash"]:
            disp.fill_rect(ZX + 36, st["zy"] + 37, 4, 4, gt.YELLOW)
            disp.fill_rect(ZX + 37, st["zy"] + 38, 2, 2, gt.ARMOR)

    if _due(st, "t_range", now, 300):
        st["range"] -= 4 + random.getrandbits(4)
        if st["range"] < 300:
            st["range"] = 1200
        disp.draw_text("{:4d}m".format(st["range"]), ZX - 2, ZY + 74, HUD, gt.BG, scale=1)
        spd = 60 + (1200 - st["range"]) // 20
        disp.draw_text("{:3d}".format(spd), 284, RET_Y - 10, gt.ARMOR, gt.BG, scale=1)
        disp.draw_text("{:3d}".format(st["range"] // 10), 284, RET_Y + 22, gt.ARMOR, gt.BG, scale=1)

    if _due(st, "t_gauge", now, 500):
        st["ecap"] = max(20, min(100, st["ecap"] + random.getrandbits(3) - 4))
        _gauge(disp, 202, st["ecap"], gt.BLUE)
        _gauge(disp, 216, 40 + random.getrandbits(5) + random.getrandbits(4), gt.YELLOW)

    if _due(st, "t_fire", now, 5000) and not st["beam"]:
        _fire_beam(disp, st)
        st["t_beam"] = now

    if _due(st, "t_clock", now, 1000):
        secs = time.ticks_diff(now, st["start"]) // 1000
        disp.draw_text("T+{:02d}:{:02d}".format(secs // 60 % 100, secs % 60),
                       184, 5, HUD, gt.PANEL, scale=1)
