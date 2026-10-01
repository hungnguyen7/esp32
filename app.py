"""
app.py - Main application loop for ESP32 CYD home display.

Manages hardware init, WiFi, screen state, touch toggling,
and periodic data refresh. Five screens cycle on tap
(Market -> Cockpit -> Zaku cockpit -> Gundam -> Server -> Market):
  SCREEN_SERVER : Prometheus home server metrics
  SCREEN_MARKET : Gold DOJI HCM, Gold Thanh Tam + BTC prices
  SCREEN_GUNDAM : static RX-78-2 vs Zaku pixel-art showcase
  SCREEN_COCKPIT: animated RX-78-2 cockpit HUD view (tick() each loop)
  SCREEN_ZAKU_COCKPIT: animated Zeon-style Zaku cockpit view (tick() each loop)
"""
import gc
import time
from machine import Pin, SPI

# Memory note: on ESP32 the MicroPython GC heap grows into the IDF heap when
# an allocation fails even after a collection, and never gives it back. The
# WiFi driver lives on the IDF heap, so letting the GC heap grow (compiling
# big modules, fragmentation) starves WiFi until it drops. Collect between
# imports and around heavy work to keep the GC heap from growing.
from ili9341 import ILI9341
from xpt2046 import XPT2046
gc.collect()
import home_server_display as server
gc.collect()
import market_data as md
gc.collect()
import market_screen as market
gc.collect()
import gundam_screen as gundam
gc.collect()
import cockpit_screen as cockpit
gc.collect()
import zaku_cockpit_screen as zaku_cockpit
gc.collect()

# -- Screen IDs ---------------------------------------------------------------
SCREEN_SERVER  = 0
SCREEN_MARKET  = 1
SCREEN_GUNDAM  = 2
SCREEN_COCKPIT = 3
SCREEN_ZAKU_COCKPIT = 4

# Tap order (first entry is the boot screen)
SCREEN_ORDER = (SCREEN_MARKET, SCREEN_COCKPIT, SCREEN_ZAKU_COCKPIT,
                SCREEN_GUNDAM, SCREEN_SERVER)

# -- Refresh intervals --------------------------------------------------------
SERVER_INTERVAL_SEC = 15
MARKET_INTERVAL_SEC = 30 * 60  # market data refresh: every 30 minutes

# -- Hardware pins ------------------------------------------------------------
from board_config import (
    LCD_SPI_BUS, LCD_BAUDRATE, LCD_CLK_PIN, LCD_MOSI_PIN, LCD_MISO_PIN,
    LCD_CS_PIN, LCD_DC_PIN, LCD_RST_PIN, LCD_BL_PIN,
    TOUCH_SPI_BUS, TOUCH_BAUDRATE, TOUCH_CLK_PIN, TOUCH_MOSI_PIN,
    TOUCH_MISO_PIN, TOUCH_CS_PIN, TOUCH_IRQ_PIN,
)


def main():
    # Backlight on
    Pin(LCD_BL_PIN, Pin.OUT).value(1)

    # Display SPI
    display_spi = SPI(
        LCD_SPI_BUS, baudrate=LCD_BAUDRATE, polarity=0, phase=0,
        sck=Pin(LCD_CLK_PIN), mosi=Pin(LCD_MOSI_PIN), miso=Pin(LCD_MISO_PIN),
    )
    disp = ILI9341(display_spi, LCD_CS_PIN, LCD_DC_PIN, LCD_RST_PIN)

    # Touch SPI
    touch_spi = SPI(
        TOUCH_SPI_BUS, baudrate=TOUCH_BAUDRATE, polarity=0, phase=0,
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
    current_screen = SCREEN_ORDER[0]
    redraw         = True
    last_server_t  = time.time() - SERVER_INTERVAL_SEC  # fetch immediately
    last_market_t  = 0
    server_cache   = {}
    market_cache   = None

    while True:
        # Touch: switch screen on falling edge (finger down)
        if touch.tapped():
            nxt = SCREEN_ORDER.index(current_screen) + 1
            current_screen = SCREEN_ORDER[nxt % len(SCREEN_ORDER)]
            redraw = True
            gc.collect()

        now_s  = time.time()
        uptime = server.format_uptime(now_s - boot_time)

        if current_screen == SCREEN_SERVER:
            if (now_s - last_server_t) >= SERVER_INTERVAL_SEC:
                gc.collect()
                server.ensure_wifi()
                server_cache  = server.fetch_metrics()
                # stamp after the fetch so a slow/failed fetch still leaves a
                # full interval for touch polling before the next one
                last_server_t = time.time()
                if not redraw:
                    server.update_screen(disp, server_cache, uptime)
            if redraw:
                server.draw_screen(disp, server_cache, "IP " + wifi_ip, uptime)
                redraw = False

        elif current_screen == SCREEN_GUNDAM:
            if redraw:
                gundam.draw_screen(disp)
                redraw = False

        elif current_screen == SCREEN_COCKPIT:
            if redraw:
                cockpit.draw_screen(disp)
                redraw = False
            else:
                cockpit.tick(disp)  # partial redraws only (radar, HUD, target)

        elif current_screen == SCREEN_ZAKU_COCKPIT:
            if redraw:
                zaku_cockpit.draw_screen(disp)
                redraw = False
            else:
                zaku_cockpit.tick(disp)

        else:  # SCREEN_MARKET
            if market_cache is None or (now_s - last_market_t) >= MARKET_INTERVAL_SEC:
                gc.collect()
                server.ensure_wifi()
                market.draw_loading(disp)
                market_cache  = md.fetch_all(
                    lambda i, ok, data: market.loading_step(disp, i, ok, data))
                market.launch(disp)
                gc.collect()
                last_market_t = now_s
                redraw        = True
            if redraw:
                market.draw_screen(disp, market_cache, uptime)
                redraw = False

        time.sleep_ms(100)
