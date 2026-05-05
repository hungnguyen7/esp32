"""
board_config.py — ESP32-CYD Hardware Configuration
Verified working as of May 5, 2026.

Board  : ESP32-D0WD-V3 (ESP32 Cheap Yellow Display / CYD)
Display: ILI9341 2.8" TFT, 320×240, SPI, RGB565

-----------------------------------------------------------------
  DISPLAY WIRING (SPI2 / HSPI)
-----------------------------------------------------------------
  GPIO 14  CLK   SPI clock
  GPIO 13  MOSI  SPI data out
  GPIO 12  MISO  SPI data in  (not used for write-only display)
  GPIO 15  CS    Chip select  (active LOW)
  GPIO  2  DC    Data / Command select
  GPIO  4  RST   Hardware reset (active LOW)
  GPIO 21  BL    Backlight PWM  (HIGH = on)

-----------------------------------------------------------------
  ILI9341 INITIALISATION — VERIFIED SETTINGS
-----------------------------------------------------------------
  COLMOD  = 0x55   16-bit / pixel (RGB565)
  MADCTL  = 0x68   Landscape 320×240, correct orientation
                     MV=1  row/col swap  → landscape
                     MX=1  col mirror    → un-mirrors image
                     BGR=1 panel is BGR  → correct colours
  Pixel write order: one row at a time with individual
    CASET(y,y) + PASET(x0,x1) windows.
    With MV=1, CASET addresses the Y axis and PASET the X axis.
    Writing each row separately ensures pixels go left→right.

-----------------------------------------------------------------
  SPI CONFIGURATION
-----------------------------------------------------------------
  Bus      : SPI(1)  (HSPI)
  Baudrate : 40 MHz
  Polarity : 0
  Phase    : 0
  MSB first

-----------------------------------------------------------------
  MICROPYTHON INITIALISATION SNIPPET
-----------------------------------------------------------------

  from machine import Pin, SPI
  from ili9341 import ILI9341

  Pin(21, Pin.OUT).value(1)          # backlight on

  spi = SPI(
      1,
      baudrate=40_000_000,
      polarity=0, phase=0,
      sck=Pin(14), mosi=Pin(13), miso=Pin(12),
  )
  disp = ILI9341(spi, cs_pin=15, dc_pin=2, rst_pin=4)
  # disp.width=320, disp.height=240

-----------------------------------------------------------------
  BOARD SPECS
-----------------------------------------------------------------
  MCU           : Xtensa LX6 dual-core, 240 MHz
  Flash         : 4 MB
  SRAM          : 520 KB
  WiFi          : 802.11 b/g/n 2.4 GHz
  Bluetooth     : 4.2 BR/EDR + BLE
  Serial port   : /dev/ttyUSB0  (CH340 USB-UART)
  MAC address   : b0:cb:d8:99:39:68
"""

# ── GPIO pin numbers ──────────────────────────────────────────────────────────

SPI_CLK_PIN = 14
SPI_MOSI_PIN = 13
SPI_MISO_PIN = 12
LCD_CS_PIN = 15
LCD_DC_PIN = 2
LCD_RST_PIN = 4
LCD_BL_PIN = 21

# ── Display properties ────────────────────────────────────────────────────────

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
DISPLAY_MADCTL = 0x68   # MV=1, MX=1, BGR=1  →  landscape, correct orientation
DISPLAY_COLMOD = 0x55   # 16-bit RGB565
SPI_BAUDRATE = 40_000_000
SPI_BUS = 1      # HSPI

# ── Board identity ────────────────────────────────────────────────────────────

BOARD_NAME = "ESP32-CYD"
CHIP = "ESP32-D0WD-V3"
SERIAL_PORT = "/dev/ttyUSB0"
MAC_ADDRESS = "b0:cb:d8:99:39:68"
