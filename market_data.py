"""
market_data.py - Live market data fetcher (Gold DOJI HCM, Gold Thanh Tâm, BTC).

Sources:
  BTC       : Binance public ticker API
  DOJI HCM  : vang.today API
  Thanh Tâm : tuanquangdong.com live-price JSON (row Vàng 9999)
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
    Vàng 9999 24k Thanh Tâm (Sóc Trăng) from tuanquangdong.com.
    Uses the site's live-price JSON endpoint (profile_id=235), the same one
    its page script calls. Response (~700 bytes):
      {"success": true, "data": {"products": [
          {"name": "Vàng 9999 24k Thanh Tâm", "buy": "13.350.000đ",
           "sell": "13.620.000đ"}, ...], "last_updated": "..."}}
    Returns (buy: int, sell: int) in VND/chỉ, or (None, None).
    """
    try:
        r = requests.get(
            "https://tuanquangdong.com/wp-admin/admin-ajax.php"
            "?action=gptqd_get_live_prices&profile_id=235",
            timeout=10,
        )
        data = json.loads(r.content)
        r.close()
        if data.get("success"):
            for p in data["data"]["products"]:
                if "9999" in p["name"]:
                    return _parse_vnd(p["buy"]), _parse_vnd(p["sell"])
    except Exception as e:
        print("Thanh Tam gold error:", type(e).__name__, e)
    return None, None


def _parse_vnd(text):
    """'13.350.000đ' -> 13350000 (keeps digits only)."""
    return int("".join(c for c in text if "0" <= c <= "9"))


def fetch_all(on_step=None):
    """
    Fetch BTC, DOJI HCM gold, and Thanh Tâm gold.
    Returns dict: btc, gold_buy, gold_sell, gold_change, tt_buy, tt_sell.
    Any value may be None if the source is unreachable.

    on_step(index, ok, data) is called after each source (index 0..2) so a
    loading screen can show progress between the blocking HTTP calls.
    """
    data = {}

    def step(i, ok):
        if on_step:
            on_step(i, ok, data)

    data["btc"] = fetch_btc()
    step(0, data["btc"] is not None)
    data["gold_buy"], data["gold_sell"], data["gold_change"] = fetch_gold_doji()
    step(1, data["gold_buy"] is not None)
    data["tt_buy"], data["tt_sell"] = fetch_gold_thanhtam()
    step(2, data["tt_buy"] is not None)
    return data
