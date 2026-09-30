"""
gundam_theme.py - RX-78-2 style theme shared by all screens.

Palette follows the RX-78-2 armor: white panels, blue chest, red
accents, yellow V-fin. Every shape is built from fill_rect so it works
with the plain ILI9341 driver (no line/polygon primitives needed).
"""
SCREEN_W = 320
SCREEN_H = 240

# -- Palette (RGB565) ---------------------------------------------------------
BG     = const(0x0000)  # space black       #000000
PANEL  = const(0x2124)  # frame gray        #202420
ARMOR  = const(0xFFFF)  # armor white       #FFFFFF
BLUE   = const(0x023F)  # chest cobalt      #0046FF
RED    = const(0xF800)  # shield red        #FF0000
YELLOW = const(0xFE40)  # V-fin gold        #FFC800
MUTED  = const(0x8C71)  # dim label gray    #8C8C8C
UP     = const(0x07E0)  # price up green    #00FF00
BLACK  = const(0x0000)

HEADER_H = 30
FOOTER_Y = 220


def chamfer_rect(disp, x, y, w, h, color, cut=4):
    """Filled rectangle with 45-degree cut corners (armor plate look)."""
    for i in range(cut):
        inset = cut - i
        disp.fill_rect(x + inset, y + i,         w - 2 * inset, 1, color)
        disp.fill_rect(x + inset, y + h - 1 - i, w - 2 * inset, 1, color)
    disp.fill_rect(x, y + cut, w, h - 2 * cut, color)


def tag(disp, x, y, text, color, fg=ARMOR):
    """Chamfered label plate with scale-1 text, e.g. [ DOJI HCM ]."""
    w = len(text) * 8 + 12
    chamfer_rect(disp, x, y, w, 12, color, cut=3)
    disp.draw_text(text, x + 6, y + 2, fg, color, scale=1)
    return w


def hazard_stripe(disp, x, y, w, h=6):
    """Diagonal yellow/black caution stripe."""
    disp.fill_rect(x, y, w, h, BLACK)
    period = 12
    for row in range(h):
        start = (row % period) - period
        while start < w:
            x0 = max(start, 0)
            x1 = min(start + period // 2, w)
            if x1 > x0:
                disp.fill_rect(x + x0, y + row, x1 - x0, 1, YELLOW)
            start += period


def _v_fin(disp, cx, bottom, arm=14):
    """Yellow V antenna: two 2px-thick diagonal arms meeting at (cx, bottom)."""
    for i in range(0, arm, 2):
        disp.fill_rect(cx - 2 - i, bottom - i - 2, 3, 2, YELLOW)
        disp.fill_rect(cx + i,     bottom - i - 2, 3, 2, YELLOW)
    disp.fill_rect(cx - 3, bottom - 2, 6, 4, YELLOW)


def draw_header(disp, title, code="RX-78-2"):
    """White armor header: blue unit-code plate, title, red crest with V-fin."""
    disp.fill_rect(0, 0, SCREEN_W, HEADER_H, ARMOR)
    chamfer_rect(disp, 0, 3, 76, 24, BLUE, cut=5)
    disp.draw_text(code, 38 - len(code) * 4, 11, ARMOR, BLUE, scale=1)
    disp.draw_text(title, 84, 7, BLUE, ARMOR, scale=2)
    chamfer_rect(disp, 274, 3, 44, 24, RED, cut=5)
    _v_fin(disp, 296, 22)
    disp.fill_rect(0, HEADER_H, SCREEN_W, 2, RED)


def draw_footer(disp, text, unit="01"):
    """Frame-gray footer: E.F.S.F. plate, status text, unit number."""
    disp.fill_rect(0, FOOTER_Y, SCREEN_W, SCREEN_H - FOOTER_Y, PANEL)
    disp.fill_rect(0, FOOTER_Y, SCREEN_W, 1, MUTED)
    tag(disp, 4, FOOTER_Y + 4, "E.F.S.F.", YELLOW, fg=BLACK)
    disp.draw_text(text[:22], 94, FOOTER_Y + 6, ARMOR, PANEL, scale=1)
    chamfer_rect(disp, 286, FOOTER_Y + 4, 30, 12, RED, cut=3)
    disp.draw_text(unit[:2], 293, FOOTER_Y + 6, ARMOR, RED, scale=1)


def section(disp, y, h, label, color, fg=ARMOR):
    """Section frame: colored side rail + label plate. Returns content x."""
    disp.fill_rect(0, y, 4, h, color)
    tag(disp, 8, y, label, color, fg)
    return 12


def begin(disp, title, code="RX-78-2"):
    """Clear to space background and draw the header."""
    disp.fill(BG)
    draw_header(disp, title, code)
