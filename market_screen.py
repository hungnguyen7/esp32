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
    data keys: btc, gold_buy, gold_sell, gold_change
    """
    disp.fill(BLACK)

    btc         = data.get("btc")
    gold_buy    = data.get("gold_buy")
    gold_sell   = data.get("gold_sell")
    gold_change = data.get("gold_change") or 0

    # -- Title bar ------------------------------------------------------------
    disp.fill_rect(0, 0, SCREEN_W, 28, ORANGE)
    disp.draw_text("MARKET DATA", 80, 6, BLACK, ORANGE, scale=2)

    # -- Gold DOJI HCM --------------------------------------------------------
    disp.draw_text("GOLD DOJI HCM", 0, 34, YELLOW, BLACK, scale=2)
    if gold_buy is not None:
        change_color = GREEN if gold_change >= 0 else RED
        disp.draw_text(
            "Buy:{}  Sell:{}".format(_fmt_millions(gold_buy), _fmt_millions(gold_sell)),
            0, 56, YELLOW, BLACK, scale=1,
        )
        disp.draw_text(
            "Change: {}".format(_fmt_change(gold_change)),
            0, 68, change_color, BLACK, scale=1,
        )
    else:
        disp.draw_text("N/A", 0, 56, DARK_GRAY, BLACK, scale=1)
    disp.hline(0, 82, SCREEN_W, DARK_GRAY)

    # -- Bitcoin --------------------------------------------------------------
    disp.draw_text("BITCOIN", 0, 88, WHITE, BLACK, scale=2)
    if btc is not None:
        disp.draw_text("$" + _fmt_commas(int(btc)), 0, 110, CYAN, BLACK, scale=2)
    else:
        disp.draw_text("N/A", 0, 110, DARK_GRAY, BLACK, scale=2)
    disp.hline(0, 136, SCREEN_W, DARK_GRAY)

    # -- Footer ---------------------------------------------------------------
    disp.draw_text("Updated: " + uptime_str, 0, 142, DARK_GRAY, BLACK, scale=1)
    disp.draw_text("Tap to go back",          0, 154, DARK_GRAY, BLACK, scale=1)
