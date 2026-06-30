"""
app.py - Main application loop for ESP32 CYD home display.

Manages hardware init, WiFi, screen state, touch toggling,
and periodic data refresh. Two screens cycle on tap:
  SCREEN_SERVER : Prometheus home server metrics
  SCREEN_MARKET : Gold DOJI HCM + BTC prices
"""
import time
from machine import Pin, SPI

from ili9341 import ILI9341
from xpt2046 import XPT2046
import home_server_display as server
import market_screen as market
import market_data as md

# -- Screen IDs ---------------------------------------------------------------
SCREEN_SERVER = 0
SCREEN_MARKET = 1

# -- Refresh intervals --------------------------------------------------------
SERVER_INTERVAL_SEC = 15
MARKET_INTERVAL_SEC = 60

# -- Hardware pins ------------------------------------------------------------
# Display (HSPI, bus 1)
LCD_CLK_PIN  = 14
LCD_MOSI_PIN = 13
LCD_MISO_PIN = 12
LCD_CS_PIN   = 15
LCD_DC_PIN   = 2
LCD_RST_PIN  = 4
LCD_BL_PIN   = 21

# Touch (VSPI, bus 2)
TOUCH_CLK_PIN  = 25
TOUCH_MOSI_PIN = 32
TOUCH_MISO_PIN = 39
TOUCH_CS_PIN   = 33
TOUCH_IRQ_PIN  = 36


def main():
    # Backlight on
    Pin(LCD_BL_PIN, Pin.OUT).value(1)

    # Display SPI
    display_spi = SPI(
        1, baudrate=40_000_000, polarity=0, phase=0,
        sck=Pin(LCD_CLK_PIN), mosi=Pin(LCD_MOSI_PIN), miso=Pin(LCD_MISO_PIN),
    )
    disp = ILI9341(display_spi, LCD_CS_PIN, LCD_DC_PIN, LCD_RST_PIN)

    # Touch SPI
    touch_spi = SPI(
        2, baudrate=1_000_000, polarity=0, phase=0,
        sck=Pin(TOUCH_CLK_PIN), mosi=Pin(TOUCH_MOSI_PIN), miso=Pin(TOUCH_MISO_PIN),
    )
    touch = XPT2046(touch_spi, TOUCH_CS_PIN, TOUCH_IRQ_PIN)

    # WiFi
    server.draw_boot_screen(disp, "Connecting...", "")
    wifi_ok, wifi_ip = server.init_wifi()
    if not wifi_ok:
        server.draw_boot_screen(disp, "WiFi FAILED", "Check config.py")
        return
    server.draw_boot_screen(disp, "WiFi OK", wifi_ip)
    time.sleep(1)

    # State
    boot_time      = time.time()
    current_screen = SCREEN_MARKET
    redraw         = True
    last_server_t  = time.time() - SERVER_INTERVAL_SEC  # fetch immediately
    last_market_t  = 0
    server_cache   = {}
    market_cache   = None

    while True:
        # Touch: switch screen on falling edge (finger down)
        if touch.tapped():
            current_screen = 1 - current_screen
            redraw = True

        now_s  = time.time()
        uptime = server.format_uptime(now_s - boot_time)

        if current_screen == SCREEN_SERVER:
            if (now_s - last_server_t) >= SERVER_INTERVAL_SEC:
                server_cache  = server.fetch_metrics()
                last_server_t = now_s
                redraw        = True
            if redraw:
                server.draw_screen(disp, server_cache, "IP " + wifi_ip, uptime)
                redraw = False

        else:  # SCREEN_MARKET
            if market_cache is None or (now_s - last_market_t) >= MARKET_INTERVAL_SEC:
                market.draw_loading(disp)
                market_cache  = md.fetch_all()
                last_market_t = now_s
                redraw        = True
            if redraw:
                market.draw_screen(disp, market_cache, uptime)
                redraw = False

        time.sleep_ms(100)
