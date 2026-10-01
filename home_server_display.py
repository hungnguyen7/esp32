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
try:
    from config import DNS_SERVER
except ImportError:
    DNS_SERVER = "1.1.1.1"
import gundam_theme as gt

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
        _apply_dns(wlan)
        return True, wlan.ifconfig()[0]
    print("Connecting to '{}'...".format(WIFI_SSID))
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(WIFI_TIMEOUT_SEC):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("WiFi connected:", ip)
            _apply_dns(wlan)
            return True, ip
        time.sleep(1)
    print("WiFi timeout")
    return False, ""


def _apply_dns(wlan):
    """
    Use DNS_SERVER instead of the DHCP-provided resolver. Measured on this
    network: the LAN resolver failed (-202) right after connect and took
    6-7 s per lookup otherwise; 1.1.1.1 answers in ~60-200 ms.
    Note: MicroPython 1.23 ifconfig() keeps the DHCP address but makes the
    config static, so the lease is not renewed; a reboot re-runs DHCP.
    """
    if not DNS_SERVER:
        return
    ip, mask, gw, dns = wlan.ifconfig()
    if dns != DNS_SERVER:
        wlan.ifconfig((ip, mask, gw, DNS_SERVER))
        print("DNS:", dns, "->", DNS_SERVER)


def ensure_wifi(timeout_sec=10):
    """Reconnect if the link dropped (the app only connects once at boot)."""
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True
    print("WiFi lost (status {}), reconnecting...".format(wlan.status()))
    try:
        wlan.disconnect()  # stop the driver's own retry loop before connect()
    except OSError:
        pass
    try:
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    except OSError as e:
        print("WiFi reconnect error:", e)
        return False
    for _ in range(timeout_sec * 5):
        if wlan.isconnected():
            print("WiFi reconnected:", wlan.ifconfig()[0])
            _apply_dns(wlan)
            return True
        time.sleep_ms(200)
    print("WiFi reconnect timeout")
    return False


# -- Prometheus ---------------------------------------------------------------

def query_prometheus(promql):
    """Run instant PromQL query. Returns float or None."""
    url = "http://{}:{}/api/v1/query?query={}".format(
        PROMETHEUS_HOST, PROMETHEUS_PORT, url_encode(promql)
    )
    try:
        resp = requests.get(url, timeout=5)
        try:
            data = json.loads(resp.content)
        finally:
            resp.close()  # close even if the body is not valid JSON
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
        return gt.MUTED
    if percent < 60:
        return gt.BLUE
    if percent < 80:
        return gt.YELLOW
    return gt.RED


BAR_X, BAR_W, BAR_H = 12, gt.SCREEN_W - 20, 12
VALUE_X = 12 + 6 * 16
# (y, label, metrics key, value format, has gauge)
_METRICS = (
    (36,  "CPU",  "cpu",  "{:.1f}%", True),
    (70,  "RAM",  "ram",  "{:.1f}%", True),
    (104, "DISK", "disk", "{:.1f}%", True),
    (138, "LOAD", "load", "{:.2f}",  False),
)


def _draw_bar_fill(disp, y, percent):
    """Segmented energy gauge cells inside the armor frame."""
    inner_x, inner_y = BAR_X + 2, y + 2
    inner_w, inner_h = BAR_W - 4, BAR_H - 4
    disp.fill_rect(inner_x, inner_y, inner_w, inner_h, gt.BLACK)
    if percent is None or percent <= 0:
        return
    filled = max(1, int(inner_w * min(percent, 100) / 100))
    color = _bar_color(percent)
    cx = inner_x
    while cx < inner_x + filled:
        disp.fill_rect(cx, inner_y, min(8, inner_x + filled - cx), inner_h, color)
        cx += 10


def _draw_value(disp, y, fmt, value):
    text = fmt.format(value) if value is not None else "N/A"
    # pad to a fixed width so a shorter value fully covers the previous one
    disp.draw_text("{:<7}".format(text[:7]), VALUE_X, y, gt.ARMOR, gt.BG, scale=2)


def draw_boot_screen(disp, message, detail=""):
    gt.begin(disp, "HOME SERVER")
    gt.hazard_stripe(disp, 0, 50, gt.SCREEN_W)
    x = gt.section(disp, 66, 50, "SYSTEM BOOT", gt.BLUE)
    disp.draw_text(message[:18], x, 84, gt.ARMOR, gt.BG, scale=2)
    if detail:
        disp.draw_text(detail[:37], x, 104, gt.YELLOW, gt.BG, scale=1)
    gt.hazard_stripe(disp, 0, 128, gt.SCREEN_W)
    gt.draw_footer(disp, "RX-78-2 GUNDAM", "00")


def draw_screen(disp, metrics, wifi_ip, uptime_str):
    """
    Full redraw (on screen switch). Layout (320x240):
      y=0   header (30px) + red trim
      y=36/70/104  CPU/RAM/DISK value (scale=2) + segmented gauge
      y=138 LOAD (scale=2)
      y=160 panel divider
      y=166 Prometheus host, y=180 IP (scale=1)
      y=220 footer: E.F.S.F. plate + uptime
    """
    gt.begin(disp, "HOME SERVER")
    for y, label, key, fmt, gauge in _METRICS:
        disp.fill_rect(0, y, 4, 30 if gauge else 16, gt.BLUE)
        disp.draw_text(label, 12, y, gt.YELLOW, gt.BG, scale=2)
        if gauge:
            disp.rect(BAR_X, y + 18, BAR_W, BAR_H, gt.ARMOR)

    disp.fill_rect(0, 160, gt.SCREEN_W, 2, gt.PANEL)
    w = gt.tag(disp, 8, 164, "PROM", gt.PANEL)
    disp.draw_text("{}:{}".format(PROMETHEUS_HOST, PROMETHEUS_PORT)[:32],
                   8 + w + 6, 166, gt.MUTED, gt.BG, scale=1)
    w = gt.tag(disp, 8, 180, "LINK", gt.PANEL)
    disp.draw_text(wifi_ip[:32], 8 + w + 6, 182, gt.MUTED, gt.BG, scale=1)
    update_screen(disp, metrics, uptime_str)


def update_screen(disp, metrics, uptime_str):
    """Partial redraw after a refresh: values, gauge cells and uptime only (no flicker)."""
    for y, label, key, fmt, gauge in _METRICS:
        value = metrics.get(key)
        _draw_value(disp, y, fmt, value)
        if gauge:
            _draw_bar_fill(disp, y + 18, value)
    gt.draw_footer(disp, uptime_str, "02")
