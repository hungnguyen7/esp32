"""
market_data.py - Live market data fetcher (Gold DOJI HCM, Gold Thanh Tâm, BTC).

Sources:
  BTC       : Binance public ticker API
  DOJI HCM  : vang.today API
  Thanh Tâm : giavangmaothiet.com HTML scrape (table.goldbox-table, row Vàng 9999)
"""
try:
    import urequests as requests
except ImportError:
    import requests

try:
    import ujson as json
except ImportError:
    import json


def fetch_btc():
    """BTC/USDT price in USD. Returns float or None."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=6,
        )
        data = json.loads(r.content)
        r.close()
        return float(data["price"])
    except Exception as e:
        print("BTC error:", e)
    return None


def fetch_gold_doji():
    """
    DOJI HCM gold price from vang.today.
    Response: {"success": true, "buy": 162000000, "sell": 165000000,
               "change_buy": -1300000, ...}
    Returns (buy: int, sell: int, change_buy: int) or (None, None, None).
    """
    try:
        r = requests.get(
            "https://www.vang.today/api/prices?type=DOHCML",
            timeout=8,
        )
        data = json.loads(r.content)
        r.close()
        if data.get("success"):
            buy = int(data["buy"]) / 10
            sell = int(data["sell"]) / 10
            change_buy = int(data.get("change_buy", 0) or 0) / 10
            return buy, sell, change_buy
    except Exception as e:
        print("Gold error:", e)
    return None, None, None


def fetch_gold_thanhtam():
    """
    Vàng 9999 24k Thanh Tâm (Sóc Trăng) from giavangmaothiet.com.
    Streams HTML in 256-byte chunks. Works entirely with bytes to avoid
    Unicode decode issues in MicroPython. All search markers are ASCII.
    Returns (buy: int, sell: int) in VND/chỉ, or (None, None).
    """
    CHUNK = 256
    TAR   = b'class="tar">'
    ENDTD = b"</td>"

    try:
        import gc
        gc.collect()
        r = requests.get(
            "https://giavangmaothiet.com/gia-vang-thanh-tam-soc-trang-hom-nay/",
            timeout=10,
        )
        buf   = b""
        stage = 0   # 0=find table, 1=find 9999, 2=find buy, 3=find sell
        buy   = None
        sell  = None

        while True:
            chunk = r.raw.read(CHUNK)
            if not chunk:
                break
            buf += chunk

            progress = True
            while progress:
                progress = False
                if stage == 0:
                    i = buf.find(b"goldbox-table")
                    if i >= 0:
                        buf = buf[i + 13:]
                        stage = 1; progress = True
                elif stage == 1:
                    i = buf.find(b"9999")
                    if i >= 0:
                        buf = buf[i + 4:]
                        stage = 2; progress = True
                elif stage == 2 or stage == 3:
                    i = buf.find(TAR)
                    if i >= 0:
                        i += 12  # len('class="tar">')
                        j = buf.find(ENDTD, i)
                        if j >= 0:
                            # Price bytes are pure ASCII: "13.050.000"
                            val = int(buf[i:j].strip().replace(b".", b"").replace(b",", b""))
                            if stage == 2:
                                buy = val; buf = buf[j:]; stage = 3
                            else:
                                sell = val; r.close(); return buy, sell
                            progress = True

            if len(buf) > 64:
                buf = buf[-64:]

        r.close()
        return buy, sell
    except Exception as e:
        import gc
        print("Thanh Tam gold error:", type(e).__name__, e, "| free:", gc.mem_free())
    return None, None


def fetch_all():
    """
    Fetch BTC, DOJI HCM gold, and Thanh Tâm gold.
    Returns dict: btc, gold_buy, gold_sell, gold_change, tt_buy, tt_sell.
    Any value may be None if the source is unreachable.
    """
    btc = fetch_btc()
    gold_buy, gold_sell, gold_change = fetch_gold_doji()
    tt_buy, tt_sell = fetch_gold_thanhtam()
    return {
        "btc":         btc,
        "gold_buy":    gold_buy,
        "gold_sell":   gold_sell,
        "gold_change": gold_change,
        "tt_buy":      tt_buy,
        "tt_sell":     tt_sell,
    }
