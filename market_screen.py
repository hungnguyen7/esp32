"""
market_screen.py - Market data screen drawing (Gold DOJI HCM, Gold Thanh Tam, BTC).
RX-78-2 Gundam theme, see gundam_theme.py.
"""
import gundam_theme as gt


def _fmt_millions(vnd):
    """162000000 -> '162.0M', 13350000 -> '13.35M' (2 decimals below 100M)"""
    m = vnd / 1_000_000
    return ("{:.1f}M" if m >= 100 else "{:.2f}M").format(m)


def _fmt_change(vnd):
    """Format signed VND change: -1300000 -> '-1.3M', 500000 -> '+0.5M'"""
    m = vnd / 1_000_000
    return "{:+.1f}M".format(m)


def _fmt_commas(n):
    """95234 -> '95,234'"""
    s = str(int(n))
    result = []
    for i, ch in enumerate(reversed(s)):
        if i and i % 3 == 0:
            result.append(',')
        result.append(ch)
    return ''.join(reversed(result))


# -- Loading: White Base catapult launch -------------------------------------
# draw_loading() sets the deck, loading_step() is called by
# market_data.fetch_all() after each source, launch() plays the take-off.

_LINKS = ("BINANCE BTC", "DOJI HCM", "THANH TAM 9999")
_LINK_Y = (38, 52, 66)
GO_GREEN  = const(0x07E0)
LAMP_OFF  = const(0x4208)
RX_X, RX_Y = 12, 82             # RX-78-2 standing on the catapult shuttle
RAIL_Y = 138
_LIGHTS = tuple(range(66, 316, 22))


def _deck_light(disp, i, color):
    disp.fill_rect(_LIGHTS[i], RAIL_Y + 6, 8, 4, color)


def draw_loading(disp):
    import gundam_screen as gs
    gt.begin(disp, "CATAPULT")
    for name, y in zip(_LINKS, _LINK_Y):
        gt.chamfer_rect(disp, 8, y, 10, 10, LAMP_OFF, cut=2)
        disp.draw_text(name, 24, y + 1, gt.ARMOR, gt.BG, scale=1)
        disp.draw_text("STANDBY", 256, y + 1, gt.MUTED, gt.BG, scale=1)
    # catapult deck: rail, shuttle, deck plate with guide lights
    disp.fill_rect(0, RAIL_Y, gt.SCREEN_W, 2, gt.YELLOW)
    disp.fill_rect(0, RAIL_Y + 2, gt.SCREEN_W, 14, gt.PANEL)
    for i in range(len(_LIGHTS)):
        _deck_light(disp, i, LAMP_OFF)
    disp.fill_rect(RX_X - 2, RAIL_Y - 4, 48, 4, gt.MUTED)            # shuttle
    gs.draw_sprite(disp, gs.RX78, RX_X, RX_Y, scale=1, bg=gt.BG, cache=True)
    disp.draw_text("WHITE BASE", 70, 96, gt.MUTED, gt.BG, scale=1)
    disp.draw_text("MS DECK 1", 70, 108, gt.MUTED, gt.BG, scale=1)
    disp.draw_text("PILOT: AMURO RAY", 70, 120, gt.ARMOR, gt.BG, scale=1)
    gt.hazard_stripe(disp, 0, 160, gt.SCREEN_W)
    disp.draw_text("STANDBY...", 80, 180, gt.YELLOW, gt.BG, scale=2)
    gt.draw_footer(disp, "Fetching market data", "01")


def loading_step(disp, i, ok, data):
    """Light link i green (with its value) or red NO SIGNAL; advance deck lights."""
    y = _LINK_Y[i]
    if ok:
        if i == 0:
            value = "$" + _fmt_commas(int(data["btc"]))
        elif i == 1:
            value = _fmt_millions(data["gold_buy"])
        else:
            value = _fmt_millions(data["tt_buy"])
        color = GO_GREEN
    else:
        value, color = "NO SIGNAL", gt.RED
    gt.chamfer_rect(disp, 8, y, 10, 10, color, cut=2)
    disp.fill_rect(160, y, 160, 10, gt.BG)
    disp.draw_text(value, 312 - len(value) * 8, y + 1, color, gt.BG, scale=1)
    n = len(_LIGHTS)
    for k in range(n * i // 3, n * (i + 1) // 3):
        _deck_light(disp, k, GO_GREEN if ok else gt.RED)


def launch(disp):
    """Take-off: call-out, then the RX-78-2 rides the catapult off screen."""
    import time
    import gundam_screen as gs
    disp.fill_rect(0, 176, gt.SCREEN_W, 24, gt.BG)
    disp.draw_text("AMURO, IKIMASU!", 40, 180, gt.YELLOW, gt.BG, scale=2)
    gt.draw_footer(disp, "LAUNCH!", "01")
    time.sleep_ms(500)
    x = RX_X
    while x < gt.SCREEN_W - 44:
        step = min(10 + (x - RX_X) // 3, gt.SCREEN_W - 44 - x)  # accelerate
        disp.fill_rect(x - 2, RAIL_Y - 4, step + 2, 4, gt.BG)        # old shuttle
        disp.fill_rect(x, RX_Y, step, 52, gt.BG)                      # trail
        for k, dy in enumerate((10, 24, 38)):                         # speed lines
            disp.fill_rect(max(0, x - 40 + k * 8), RX_Y + dy, 30, 1, gt.ARMOR)
        x += step
        disp.fill_rect(x - 2, RAIL_Y - 4, 48, 4, gt.MUTED)
        gs.draw_sprite(disp, gs.RX78, x, RX_Y, scale=1, bg=gt.BG, cache=True)
    time.sleep_ms(250)


def _draw_gold(disp, y, label, color, buy, sell):
    """Label plate + BUY/SELL lines (scale 2). Occupies y..y+50."""
    x = gt.section(disp, y, 50, label, color)
    if buy is not None:
        disp.draw_text("BUY  " + _fmt_millions(buy),  x, y + 16, gt.ARMOR, gt.BG, scale=2)
        disp.draw_text("SELL " + _fmt_millions(sell), x, y + 34, gt.YELLOW, gt.BG, scale=2)
    else:
        disp.draw_text("N/A", x, y + 16, gt.MUTED, gt.BG, scale=2)


def draw_screen(disp, data, uptime_str):
    """
    Render the market screen.
    data keys: btc, gold_buy, gold_sell, gold_change, tt_buy, tt_sell
    Layout (320x240):
      y=0   header (30px) + red trim
      y=36  DOJI HCM plate (blue) + BUY/SELL (scale=2), change at right
      y=92  hazard stripe
      y=104 THANH TAM 9999 plate (red) + BUY/SELL (scale=2)
      y=160 panel divider
      y=166 BITCOIN plate (yellow) + price (scale=2)
      y=220 footer: E.F.S.F. plate + uptime
    """
    gt.begin(disp, "MARKET DATA")

    gold_change = data.get("gold_change") or 0

    # -- Gold DOJI HCM --------------------------------------------------------
    _draw_gold(disp, 36, "DOJI HCM", gt.BLUE,
               data.get("gold_buy"), data.get("gold_sell"))
    if data.get("gold_buy") is not None:
        change = _fmt_change(gold_change)
        color = gt.UP if gold_change >= 0 else gt.RED
        disp.draw_text(change, 312 - len(change) * 8, 38, color, gt.BG, scale=1)

    gt.hazard_stripe(disp, 0, 92, gt.SCREEN_W)

    # -- Gold Thanh Tam 9999 --------------------------------------------------
    _draw_gold(disp, 104, "THANH TAM 9999", gt.RED,
               data.get("tt_buy"), data.get("tt_sell"))

    disp.fill_rect(0, 160, gt.SCREEN_W, 2, gt.PANEL)

    # -- Bitcoin --------------------------------------------------------------
    btc = data.get("btc")
    x = gt.section(disp, 166, 34, "BITCOIN", gt.YELLOW, fg=gt.BLACK)
    if btc is not None:
        disp.draw_text("$" + _fmt_commas(int(btc)), x, 182, gt.ARMOR, gt.BG, scale=2)
    else:
        disp.draw_text("N/A", x, 182, gt.MUTED, gt.BG, scale=2)

    # -- Footer ---------------------------------------------------------------
    gt.draw_footer(disp, uptime_str, "01")
