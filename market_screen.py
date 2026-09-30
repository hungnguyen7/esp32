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


def draw_loading(disp):
    gt.begin(disp, "MARKET DATA")
    gt.hazard_stripe(disp, 0, 96, gt.SCREEN_W)
    disp.draw_text("LAUNCHING...", 64, 112, gt.ARMOR, gt.BG, scale=2)
    gt.hazard_stripe(disp, 0, 136, gt.SCREEN_W)
    gt.draw_footer(disp, "Fetching market data", "01")


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
