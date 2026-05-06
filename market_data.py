"""
market_data.py - Live market data fetcher (Gold DOJI HCM, BTC).

Sources:
  BTC  : Binance public ticker API
  Gold : vang.today DOJI HCM API
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


def fetch_all():
    """
    Fetch BTC and DOJI HCM gold.
    Returns dict: btc, gold_buy, gold_sell, gold_change.
    Any value may be None if the source is unreachable.
    """
    btc = fetch_btc()
    gold_buy, gold_sell, gold_change = fetch_gold_doji()
    return {
        "btc":         btc,
        "gold_buy":    gold_buy,
        "gold_sell":   gold_sell,
        "gold_change": gold_change,
    }
