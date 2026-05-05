"""
home_server_display.py — MicroPython ESP32 Prometheus Metrics Display

Hardware : ESP32 + ILI9341 240×320 TFT
Server   : Prometheus at 192.168.1.199:9090
"""
import network
import time
from machine import Pin, SPI

from ili9341 import (
    ILI9341,
    BLACK, WHITE, RED, GREEN, BLUE,
    YELLOW, CYAN, ORANGE, DARK_GRAY,
)

try:
    import urequests as requests
except ImportError:
    import requests

try:
    import ujson as json
except ImportError:
    import json

# ── Configuration (loaded from config.py on the ESP32 filesystem) ────────────

from config import WIFI_SSID, WIFI_PASSWORD, PROMETHEUS_HOST, PROMETHEUS_PORT

UPDATE_INTERVAL_SEC = 15   # seconds between metric refreshes
WIFI_TIMEOUT_SEC = 20   # seconds to wait for WiFi association

# ── Hardware pins (matches mainboard_config.py / esp32.yaml) ──────────────────

SPI_CLK_PIN = 14
SPI_MOSI_PIN = 13
SPI_MISO_PIN = 12
LCD_CS_PIN = 15
LCD_DC_PIN = 2
LCD_RST_PIN = 4
LCD_BL_PIN = 21

# ── Display geometry ──────────────────────────────────────────────────────────

SCREEN_W = 320
SCREEN_H = 240

# ── Prometheus PromQL queries (node_exporter metrics) ─────────────────────────

QUERY_CPU = '100-(avg(rate(node_cpu_seconds_total{mode="idle"}[2m]))*100)'
QUERY_RAM = '(1-node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)*100'
QUERY_DISK = ('(1-node_filesystem_avail_bytes{mountpoint="/"}'
              '/node_filesystem_size_bytes{mountpoint="/"})*100')
QUERY_LOAD = 'node_load1'


# ── Helpers ────────────────────────────────────────────────────────────────────

def url_encode(s):
    """Minimal percent-encoder — MicroPython has no urllib.parse."""
    safe = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789-_.~")
    out = []
    for c in s:
        out.append(c if c in safe else "%{:02X}".format(ord(c)))
    return "".join(out)


def format_uptime(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return "Up {:02d}:{:02d}:{:02d}".format(h, m, s)


# ── WiFi ───────────────────────────────────────────────────────────────────────

def init_wifi():
    """
    Connect to the configured WiFi network.
    Returns (True, ip_string) on success, (False, "") on failure.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True, wlan.ifconfig()[0]

    print("Connecting to '{}'...".format(WIFI_SSID))
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for _ in range(WIFI_TIMEOUT_SEC):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("WiFi connected — IP:", ip)
            return True, ip
        time.sleep(1)

    print("WiFi connection timed out")
    return False, ""


# ── Prometheus ─────────────────────────────────────────────────────────────────

def query_prometheus(promql):
    """
    Execute an instant PromQL query.
    Returns the scalar float value, or None on any error.
    """
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
    except Exception as exc:
        print("Prometheus error:", exc)
    return None


def fetch_metrics():
    """Fetch CPU, RAM, Disk, and Load metrics from Prometheus."""
    return {
        "cpu":  query_prometheus(QUERY_CPU),
        "ram":  query_prometheus(QUERY_RAM),
        "disk": query_prometheus(QUERY_DISK),
        "load": query_prometheus(QUERY_LOAD),
    }


# ── Display drawing ────────────────────────────────────────────────────────────

def _bar_color(percent):
    """Map usage % to a traffic-light colour."""
    if percent is None:
        return DARK_GRAY
    if percent < 60:
        return GREEN
    if percent < 80:
        return YELLOW
    return RED


def _draw_progress_bar(disp, x, y, w, h, percent):
    """Bordered progress bar.  percent may be None (shown as empty)."""
    disp.rect(x, y, w, h, DARK_GRAY)
    inner_x = x + 2
    inner_y = y + 2
    inner_w = w - 4
    inner_h = h - 4
    disp.fill_rect(inner_x, inner_y, inner_w, inner_h, BLACK)
    if percent is not None and percent > 0:
        filled = max(1, int(inner_w * min(percent, 100) / 100))
        disp.fill_rect(inner_x, inner_y, filled, inner_h, _bar_color(percent))


def _draw_metric(disp, y, label, value_str, percent=None):
    """
    Draw one metric block:  label line (scale=2) + optional progress bar.
    y        — top of the label text
    label    — left-aligned, e.g. "CPU: "
    value_str — right portion, e.g. "25.3%"
    percent  — 0-100 for bar, or None to skip bar
    """
    line = "{:<5}{}".format(label, value_str)
    line = line[:20]                           # 20 chars × 16 px = 320 px
    disp.draw_text(line, 0, y, WHITE, BLACK, scale=2)
    if percent is not None:
        _draw_progress_bar(disp, 5, y + 18, SCREEN_W - 10, 12, percent)


def draw_boot_screen(disp, message, detail=""):
    """Simple splash screen shown during startup."""
    disp.fill(BLACK)
    disp.fill_rect(0, 0, SCREEN_W, 28, BLUE)
    disp.draw_text("HOME SERVER", 80, 6, WHITE, BLUE, scale=2)
    disp.draw_text(message[:20], 5, 60, WHITE, BLACK, scale=2)
    if detail:
        disp.draw_text(detail[:40], 5, 90, YELLOW, BLACK, scale=1)


def draw_screen(disp, metrics, wifi_ip, uptime_str):
    """Render the full metrics dashboard."""
    disp.fill(BLACK)

    # ── Title bar ──────────────────────────────────────────────────
    disp.fill_rect(0, 0, SCREEN_W, 28, BLUE)
    disp.draw_text("HOME SERVER", 80, 6, WHITE, BLUE, scale=2)

    # ── Metric rows ────────────────────────────────────────────────
    cpu = metrics.get("cpu")
    ram = metrics.get("ram")
    disk = metrics.get("disk")
    load = metrics.get("load")

    cpu_str = "{:.1f}%".format(cpu) if cpu is not None else "N/A"
    ram_str = "{:.1f}%".format(ram) if ram is not None else "N/A"
    disk_str = "{:.1f}%".format(disk) if disk is not None else "N/A"
    load_str = "{:.2f}".format(load) if load is not None else "N/A"

    # y=30:  CPU
    _draw_metric(disp, 30,  "CPU: ",  cpu_str,  cpu)
    # y=65:  RAM
    _draw_metric(disp, 65,  "RAM: ",  ram_str,  ram)
    # y=100: DISK
    _draw_metric(disp, 100, "DISK:",  disk_str, disk)
    # y=135: LOAD (no bar — not a percentage)
    _draw_metric(disp, 135, "LOAD:",  load_str, None)

    # ── Footer ─────────────────────────────────────────────────────
    disp.hline(0, 162, SCREEN_W, DARK_GRAY)
    server_info = "{}:{}".format(PROMETHEUS_HOST, PROMETHEUS_PORT)
    disp.draw_text("Prometheus",         5, 166, DARK_GRAY, BLACK, scale=1)
    disp.draw_text(server_info,          5, 176, DARK_GRAY, BLACK, scale=1)
    disp.draw_text(wifi_ip[:40],         5, 188, DARK_GRAY, BLACK, scale=1)
    disp.draw_text(uptime_str[:40],      5, 200, DARK_GRAY, BLACK, scale=1)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    # Backlight ON
    Pin(LCD_BL_PIN, Pin.OUT).value(1)

    # Initialise SPI and display
    spi = SPI(
        1,
        baudrate=40_000_000,
        polarity=0,
        phase=0,
        sck=Pin(SPI_CLK_PIN),
        mosi=Pin(SPI_MOSI_PIN),
        miso=Pin(SPI_MISO_PIN),
    )
    disp = ILI9341(spi, LCD_CS_PIN, LCD_DC_PIN, LCD_RST_PIN)

    # Boot: connecting screen
    draw_boot_screen(disp, "Connecting...", WIFI_SSID)

    wifi_ok, wifi_ip = init_wifi()

    if not wifi_ok:
        draw_boot_screen(disp, "WiFi FAILED", "Check SSID/password")
        return

    draw_boot_screen(disp, "WiFi OK", wifi_ip)
    time.sleep(1)

    start_ticks = time.time()

    # Main loop
    while True:
        uptime = format_uptime(time.time() - start_ticks)
        metrics = fetch_metrics()
        draw_screen(disp, metrics, "IP " + wifi_ip, uptime)
        time.sleep(UPDATE_INTERVAL_SEC)


if __name__ == "__main__":
    main()
