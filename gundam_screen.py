"""
gundam_screen.py - Showcase screen: pixel-art RX-78-2 vs Char's Zaku II (MS-06S).

Sprites are 44x52 character grids, one char per pixel, drawn at 3x.
Each scaled row is built in a small buffer and sent with one SPI write
(see draw_sprite). The grids were composed from shapes (boxes, mirrored
parts, auto outline) on the host, then pasted here.
"""
import gundam_theme as gt

SCALE = 3

# Char's Zaku colours
PINK  = const(0xFA0C)  # Char pink          #FF4060
HANGAR_LINE = const(0x4228)  # backdrop panel seam #404540

_COLORS = {
    "K": gt.BLACK, "W": gt.ARMOR, "B": gt.BLUE, "R": gt.RED, "Y": gt.YELLOW,
    "w": 0xAD98,  # armor shade      #A8B0C0
    "b": 0x0154,  # blue shade       #0028A0
    "r": 0xA000,  # red shade        #A00000
    "G": 0x73D0,  # joint gray       #707880
    "g": 0x4229,  # dark gray        #404448
    "E": 0xB7E6,  # RX-78 eyes       #B0FF30
    "e": 0xFFFF,  # eye highlight
    "P": PINK,
    "p": 0xFC12,  # pink highlight   #FF8096
    "D": 0x9804,  # dark red         #980020
    "d": 0x6002,  # darker red       #640014
    "S": 0xCE5A,  # spike/horn steel #C8C8D0
    "M": 0xFB16,  # mono-eye glow    #FF60B0
}

RX78 = (
    ".........KYYYKK..............KKYYYK.........",
    "..........KKYYYKK..........KKYYYKK..........",
    "............KKYYYKK......KKYYYKK............",
    "............KKKKYYYKKKKKKYYYKKKK............",
    "...........KPPKKwYYYYRRYYYYwKKPPK...........",
    "...........KwwKKwYWYYYYYYWYwKKwwK...........",
    "...........KwwKKwWWYYYYYYWWwKKwwK...........",
    "...........KwwKKwWKKKKKKKKWwKKwwK...........",
    "...........KwwKKwWEEEKKEEEWwKKwwK...........",
    "...........KwwKKwWKEEKKEEKWwKKwwK...........",
    ".KKKKKKKKKKKwwKKwWWKWWWWKWWwKKwwKKKKKKKKKKK.",
    ".KwWWWWWWWWKwwKKwWWKRRRRKWWwKKwwKWWWWWWWWwK.",
    ".KwWwwwwwWWKKKKKKKKKRRRRKKKKKKKKKWWwwwwwWwK.",
    ".KwWWWWWWWWKbBBBBBKWWWWWWKBBBBBbKWWWWWWWWwK.",
    ".KwWWWWWWWWKbBBBBBKWBBBBWKBBBBBbKWWWWWWWWwK.",
    ".KwWWWWWWWWKbYYYYYKKBBBBKKYYYYYbKWWWWWWWWwK.",
    ".KwWWWWWWWWKbKKKKKBBBbbBBBKKKKKbKWWWWWWWWwK.",
    ".KwWWWWWWWWKbYYYYYBBBbbBBBYYYYYbKWWWWWWWWwK.",
    ".KwWWWWWWWWKbKKKKKBBBbbBBBKKKKKbKWWWWWWWWwK.",
    ".KwWWWWWWWWKbYYYYYBBBbbBBBYYYYYbKWWWWWWWWwK.",
    ".KwwwwwwwwwKbBBBBBBBBbbBBBBBBBBbKwwwwwwwwwK.",
    ".KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK.",
    "...KWWWWWK...KrrrrrrrrrrrrrrrrK...KWWWWWK...",
    "...KWWWWWK...KRRRRRRRRRRRRRRRRK...KWWWWWK...",
    "...KWWWWWK..KKKKKKKKKKKKKKKKKKKK..KWWWWWK...",
    "...KWWWWWK..KWWWWWWWYYYYWWWWWWWK..KWWWWWK...",
    "...KKKKKKK..KWWWWWWWYYYYWWWWWWWK..KKKKKKK...",
    "...KGGGGGK.KKKKKKKKKKKKKKKKKKKKKK.KGGGGGK...",
    "..KKKKKKKKKKWWWWWWKRYYYYRKWWWWWWKKKKKKKKKK..",
    "..KwWWWWWWKKWYYYYWKRYYYYRKWYYYYWKKWWWWWWwK..",
    "..KwWWWWWWKKWYYYYWKRRRRRRKWYYYYWKKWWWWWWwK..",
    "..KwWWWWWWKKWWWWWWKRRRRRRKWWWWWWKKWWWWWWwK..",
    "..KwWWWWWWKKWWWWWWKRRRRRRKWWWWWWKKWWWWWWwK..",
    "..KwwwwwwwKKKKKKKKKRRRRRRKKKKKKKKKwwwwwwwK..",
    "..KKKKKKKKK..KwWWWKKKKKKKKWWWwK..KKKKKKKKK..",
    "....KGGGK....KwWWWWWK..KWWWWWwK....KGGGK....",
    "....KGGGK....KwWWWWWK..KWWWWWwK....KGGGK....",
    "....KKKKK....KwWWWWWK..KWWWWWwK....KKKKK....",
    ".............KwWWWWWK..KWWWWWwK.............",
    "............KKKKKKKKKKKKKKKKKKKK............",
    "............KwWwwwwWWKKWWwwwwWwK............",
    "............KwWwwwwWWKKWWwwwwWwK............",
    "............KwWWWWWWWKKWWWWWWWwK............",
    "............KwWWWWWWWKKWWWWWWWwK............",
    "............KwWwwwwWWKKWWwwwwWwK............",
    "............KwWWWWWWWKKWWWWWWWwK............",
    "............KwWWWWWWWKKWWWWWWWwK............",
    "..........KKKKKKKKKKKKKKKKKKKKKKKK..........",
    "..........KRRRRRRRRRRKKRRRRRRRRRRK..........",
    "..........KRRRRRRRRRRKKRRRRRRRRRRK..........",
    "..........KrrrrrrrrrrKKrrrrrrrrrrK..........",
    "..........KKKKKKKKKKKKKKKKKKKKKKKK..........",
)

ZAKU = (
    "....................KSSK....................",
    "...................KKSSKK...................",
    "................KKKPSSSSPKK.................",
    "...............KppPPSSSSPPPK................",
    "...............KppPPPPPPPPPPK...............",
    "..............KPppPPPPPPPPPPPK..............",
    "...............KKKMMMKKKKKKKK.....K..K..K...",
    "...............KKKMeMKKKKKKKK....KSKKSKKSK..",
    "...............KKKMMMKKKKKKKK....KSKKSKKSK..",
    "..............KPppPPPPPPPPPPPK..KSSSSSSSSSK.",
    "..............KPppPggggggPPPPK..KSSSSSSSSSK.",
    ".KKKKKKKKKK....KPPPgGGGGgPPPK...KSSSSSSSSSK.",
    "KpPPPPPPPPPKKKKKKPPKgKKgKPPKKKKKKKKKKKKKKKKK",
    "KpPPPPPPPPPKKpPPGGPgGGGGgPGGPPpKdDDDDDDDDDDK",
    "KpPDDDDDDPPKKpPggPPPPPPPPPPggPpKdDDDDDDDDDDK",
    "KpPDDDDDDPPKKpGGPPPPPPPPPPPPGGpKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKggPPPPPPPPPPPPPPggKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKGGPKKKKKKKKKKKKPGGKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKdDDDDDDDDDDK",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKKKKKKKKKKKKK",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKGGKDDDDDK...",
    "KpPPPPPPPPPKKpPPKDDDDddDDDDKPPpKggKDDDDDK...",
    "KpPPPPPPPPPKKKKKKKKKKKKKKKKKKKKKGGKDDDDDK...",
    "KpPPPPPPPPPK.KDDDDDDDDDDDDDDDDKKggKDDDDDK...",
    "KDDDDDDDDDDKKKDDDDDDDDDDDDDDDDKKGKKKKKKKKK..",
    ".KKKKKKKKKKKpKKKKKKKKKKKKKKKKKKpgKpPPPPPPK..",
    "...KpPPPPPKGpPPPPPKDDDDDDKPPPPPpGKpPPPPPPK..",
    "...KpPPPPPKKpPPPPPKDDDDDDKPPPPPpKKpPPPPPPK..",
    "...KpPPPPPKKpPPPPPKDDDDDDKPPPPPpKKpPPPPPPK..",
    "...KpPPPPPKKpPPPPPKDDDDDDKPPPPPpKKpPPPPPPK..",
    "...KpPPPPPKKKKKKKKKKKKKKKKKKKKKKKKpPPPPPPK..",
    "...KKKKKKKK..KdDDDDDK..KDDDDDdK..KKKKKKKKK..",
    "....KgggK....KdDDDDDK..KDDDDDdK....KgggK....",
    "....KgggK....KdDDDDDK..KDDDDDdK....KgggK....",
    "....KKKKK...KKKKKKKKKKKKKKKKKKKK...KKKKK....",
    "............KpPPPPPPPKKPPPPPPPpK............",
    "............KpPPPPPPPKKPPPPPPPpK............",
    "............KpPDDDDPPKKPPDDDDPpK............",
    "............KpPDDDDPPKKPPDDDDPpK............",
    "............KpPPPPPPPKKPPPPPPPpK............",
    "...........KKKKKKKKKKKKKKKKKKKKKK...........",
    "...........KpPPPPPPPPKKPPPPPPPPpK...........",
    "...........KpPPPPPPPPKKPPPPPPPPpK...........",
    "...........KpPPPPPPPPKKPPPPPPPPpK...........",
    "..........KKKKKKKKKKKKKKKKKKKKKKKK..........",
    "..........KDDDDDDDDDDKKDDDDDDDDDDK..........",
    "..........KDDDDDDDDDDKKDDDDDDDDDDK..........",
    "..........KddddddddddKKddddddddddK..........",
    "..........KKKKKKKKKKKKKKKKKKKKKKKK..........",
)


_row_cache = {}


def _row_bytes(line, scale, bg):
    buf = bytearray(len(line) * scale * 2)
    i = 0
    for ch in line:
        c = bg if ch == "." else _COLORS[ch]
        hi, lo = c >> 8, c & 0xFF
        for _ in range(scale):
            buf[i] = hi
            buf[i + 1] = lo
            i += 2
    return buf


def draw_sprite(disp, sprite, x, y, scale=SCALE, bg=gt.PANEL, cache=False):
    """
    Send each scaled sprite row with a single SPI write per display row
    ("." pixels take the bg colour). With cache=True the row buffers are
    kept (~4.5 KB for a 1x sprite) so animated redraws skip the rebuild.
    """
    w = len(sprite[0]) * scale
    rows = _row_cache.get((id(sprite), scale, bg)) if cache else None
    if rows is None:
        rows = [_row_bytes(line, scale, bg) for line in sprite] if cache else None
        if cache:
            _row_cache[(id(sprite), scale, bg)] = rows
    for r in range(len(sprite)):
        buf = rows[r] if rows else _row_bytes(sprite[r], scale, bg)
        yy = y + r * scale
        for sr in range(scale):
            disp.blit_row(x, yy + sr, w, buf)


def _hangar(disp, x, y, w, h):
    """Gray hangar bay so the black sprite outlines read on screen."""
    gt.chamfer_rect(disp, x, y, w, h, gt.PANEL, cut=6)
    disp.fill_rect(x + 6, y + h - 5, w - 12, 3, HANGAR_LINE)  # deck floor


def draw_screen(disp):
    gt.begin(disp, "MOBILE SUIT")
    disp.draw_text("RX-78-2", 24, 36, gt.ARMOR, gt.BG, scale=2)
    disp.draw_text("MS-06S", 192, 36, PINK, gt.BG, scale=2)
    _hangar(disp, 10, 54, 140, 164)
    _hangar(disp, 170, 54, 140, 164)
    draw_sprite(disp, RX78, 14, 58)
    draw_sprite(disp, ZAKU, 174, 58)
    disp.draw_text("VS", 152, 128, gt.YELLOW, gt.BG, scale=1)
    gt.draw_footer(disp, "E.F.S.F. vs ZEON", "03")
