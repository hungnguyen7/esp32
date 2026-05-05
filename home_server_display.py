"""
home_server_display.py - Server metrics screen (Prometheus).

Responsibilities:
  - WiFi connection
  - Prometheus data fetching
  - Server screen drawing
"""
import network
import time

try:
    import urequests as requests
except ImportError:
    import requests

try:
    import ujson as json
except ImportError:
    import json

from config import WIFI_SSID, WIFI_PASSWORD, PROMETHEUS_HOST, PROMETHEUS_PORT
from ili9341 import BLACK, WHITE, RED, GREEN, BLUE, YELLOW, DARK_GRAY

SCREEN_W = 320
SCREEN_H = 240
UPDATE_INTERVAL_SEC = 15
WIFI_TIMEOUT_SEC = 20

QUERY_CPU = '100-(avg(rate(node_cpu_seconds_total{mode="idle"}[2m]))*100)'
QUERY_RAM = '(1-node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)*100'
QUERY_DISK = ('(1-node_filesystem_avail_bytes{mountpoint="/"}'
              '/node_filesystem_size_bytes{mountpoint="/"})*100')
QUERY_LOAD = 'node_load1'


# -- Helpers ------------------------------------------------------------------

def url_encode(s):
    safe = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789-_.~")
    return "".join(c if c in safe else "%{:02X}".format(ord(c)) for c in s)


def format_uptime(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return "Up {:02d}:{:02d}:{:02d}".format(h, m, s)


# -- WiFi ---------------------------------------------------------------------

def init_wifi():
    """Connect to WiFi. Returns (True, ip) or (False, '')."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True, wlan.ifconfig()[0]
    print("Connecting to '{}'...".format(WIFI_SSID))
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(WIFI_TIMEOUT_SEC):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("WiFi connected:", ip)
            return True, ip
        time.sleep(1)
    print("WiFi timeout")
    return False, ""


# -- Prometheus ---------------------------------------------------------------

def query_prometheus(promql):
    """Run instant PromQL query. Returns float or None."""
    url = "http://{}:{}/api/v1/query?query={}".format(
        PROMETHEUS_HOST, PROMETHEUS_PORT, url_encode(promql)
    )
    try:
        resp = requests.get(url, timeout=5)
        data = json.loads(resp.content)
        resp.close()
        if data.get("status") == "success":
            results = data["data"]["result"]
            if results:
                return float(results[0]["value"][1])
    except Exception as e:
        print("Prometheus error:", e)
    return None


def fetch_metrics():
    return {
        "cpu":  query_prometheus(QUERY_CPU),
        "ram":  query_prometheus(QUERY_RAM),
        "disk": query_prometheus(QUERY_DISK),
        "load": query_prometheus(QUERY_LOAD),
    }


# -- Drawing ------------------------------------------------------------------

def _bar_color(percent):
    if percent is None:
        return DARK_GRAY
    if percent < 60:
        return GREEN
    if percent < 80:
        return YELLOW
    return RED


def _draw_progress_bar(disp, x, y, w, h, percent):
    disp.rect(x, y, w, h, DARK_GRAY)
    inner_x, inner_y = x + 2, y + 2
    inner_w, inner_h = w - 4, h - 4
    disp.fill_rect(inner_x, inner_y, inner_w, inner_h, BLACK)
    if percent is not None and percent > 0:
        filled = max(1, int(inner_w * min(percent, 100) / 100))
        disp.fill_rect(inner_x, inner_y, filled, inner_h, _bar_color(percent))


def _draw_metric(disp, y, label, value_str, percent=None):
    line = "{:<5}{}".format(label, value_str)[:20]
    disp.draw_text(line, 0, y, WHITE, BLACK, scale=2)
    if percent is not None:
        _draw_progress_bar(disp, 5, y + 18, SCREEN_W - 10, 12, percent)


def draw_boot_screen(disp, message, detail=""):
    disp.fill(BLACK)
    disp.fill_rect(0, 0, SCREEN_W, 28, BLUE)
    disp.draw_text("HOME SERVER", 80, 6, WHITE, BLUE, scale=2)
    disp.draw_text(message[:20], 5, 60, WHITE, BLACK, scale=2)
    if detail:
        disp.draw_text(detail[:40], 5, 90, YELLOW, BLACK, scale=1)


def draw_screen(disp, metrics, wifi_ip, uptime_str):
    disp.fill(BLACK)
    disp.fill_rect(0, 0, SCREEN_W, 28, BLUE)
    disp.draw_text("HOME SERVER", 80, 6, WHITE, BLUE, scale=2)

    cpu  = metrics.get("cpu")
    ram  = metrics.get("ram")
    disk = metrics.get("disk")
    load = metrics.get("load")

    _draw_metric(disp, 30,  "CPU: ", "{:.1f}%".format(cpu)  if cpu  is not None else "N/A", cpu)
    _draw_metric(disp, 65,  "RAM: ", "{:.1f}%".format(ram)  if ram  is not None else "N/A", ram)
    _draw_metric(disp, 100, "DISK:", "{:.1f}%".format(disk) if disk is not None else "N/A", disk)
    _draw_metric(disp, 135, "LOAD:", "{:.2f}".format(load)  if load is not None else "N/A", None)

    disp.hline(0, 162, SCREEN_W, DARK_GRAY)
    disp.draw_text("Prometheus", 5, 166, DARK_GRAY, BLACK, scale=1)
    disp.draw_text("{}:{}".format(PROMETHEUS_HOST, PROMETHEUS_PORT),
                   5, 176, DARK_GRAY, BLACK, scale=1)
    disp.draw_text(wifi_ip[:40],     5, 188, DARK_GRAY, BLACK, scale=1)
    disp.draw_text(uptime_str[:40],  5, 200, DARK_GRAY, BLACK, scale=1)
