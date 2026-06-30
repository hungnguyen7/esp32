"""
market_screen.py - Market data screen drawing (Gold DOJI HCM, BTC).
"""
from ili9341 import BLACK, WHITE, RED, GREEN, CYAN, YELLOW, ORANGE, DARK_GRAY

SCREEN_W = 320
SCREEN_H = 240


def _fmt_millions(vnd):
    """162000000 -> '162.0M'"""
    return "{:.1f}M".format(vnd / 1_000_000)


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


def draw_loading(disp):
    disp.fill(BLACK)
    disp.fill_rect(0, 0, SCREEN_W, 28, ORANGE)
    disp.draw_text("MARKET DATA", 80, 6, BLACK, ORANGE, scale=2)
    disp.draw_text("Fetching...", 40, 110, WHITE, BLACK, scale=2)


def draw_screen(disp, data, uptime_str):
    """
    Render the market screen.
    data keys: btc, gold_buy, gold_sell, gold_change, tt_buy, tt_sell
    Layout (320×240):
      y=0   title bar (28px)
      y=30  DOJI HCM label (scale=1) + Mua/Ban (scale=2 each line)
      y=90  divider
      y=94  THANH TAM label (scale=1) + Mua/Ban (scale=2 each line)
      y=144 divider
      y=148 BTC label (scale=1) + price (scale=2)
      y=178 divider
      y=182 uptime (scale=1, single line)
    """
    disp.fill(BLACK)

    btc         = data.get("btc")
    gold_buy    = data.get("gold_buy")
    gold_sell   = data.get("gold_sell")
    gold_change = data.get("gold_change") or 0
    tt_buy      = data.get("tt_buy")
    tt_sell     = data.get("tt_sell")

    # -- Title bar ------------------------------------------------------------
    disp.fill_rect(0, 0, SCREEN_W, 28, ORANGE)
    disp.draw_text("MARKET DATA", 80, 6, BLACK, ORANGE, scale=2)

    # -- Gold DOJI HCM --------------------------------------------------------
    disp.draw_text("GOLD DOJI HCM", 0, 30, YELLOW, BLACK, scale=1)
    if gold_buy is not None:
        change_color = GREEN if gold_change >= 0 else RED
        disp.draw_text("Mua: " + _fmt_millions(gold_buy),  0, 40, YELLOW, BLACK, scale=2)
        disp.draw_text("Ban: " + _fmt_millions(gold_sell),  0, 58, YELLOW, BLACK, scale=2)
        disp.draw_text("Change: " + _fmt_change(gold_change), 0, 78, change_color, BLACK, scale=1)
    else:
        disp.draw_text("N/A", 0, 40, DARK_GRAY, BLACK, scale=2)
    disp.hline(0, 90, SCREEN_W, DARK_GRAY)

    # -- Gold Thanh Tâm 9999 --------------------------------------------------
    disp.draw_text("GOLD THANH TAM 9999", 0, 94, YELLOW, BLACK, scale=1)
    if tt_buy is not None:
        disp.draw_text("Mua: " + _fmt_millions(tt_buy),  0, 104, YELLOW, BLACK, scale=2)
        disp.draw_text("Ban: " + _fmt_millions(tt_sell), 0, 122, YELLOW, BLACK, scale=2)
    else:
        disp.draw_text("N/A", 0, 104, DARK_GRAY, BLACK, scale=2)
    disp.hline(0, 144, SCREEN_W, DARK_GRAY)

    # -- Bitcoin --------------------------------------------------------------
    disp.draw_text("BITCOIN", 0, 148, WHITE, BLACK, scale=1)
    if btc is not None:
        disp.draw_text("$" + _fmt_commas(int(btc)), 0, 158, CYAN, BLACK, scale=2)
    else:
        disp.draw_text("N/A", 0, 158, DARK_GRAY, BLACK, scale=2)
    disp.hline(0, 178, SCREEN_W, DARK_GRAY)

    # -- Footer ---------------------------------------------------------------
    disp.draw_text(uptime_str, 0, 182, DARK_GRAY, BLACK, scale=1)
