"""
board_config.py — ESP32-CYD hardware configuration (single source of truth).

Board  : ESP32-D0WD-V3 (ESP32 Cheap Yellow Display / CYD), 240 MHz, 4 MB flash
Display: ILI9341 2.8" TFT, 320x240, RGB565 on HSPI (SPI1) at 40 MHz
Touch  : XPT2046 resistive controller on VSPI (SPI2) at 1 MHz
Serial : /dev/ttyUSB0 (CH340 USB-UART), MAC b0:cb:d8:99:39:68

ILI9341 notes (verified on this panel):
  COLMOD = 0x55  16-bit RGB565
  MADCTL = 0x60  MV=1 (landscape) + MX=1 (un-mirror), RGB order.
                 0x68 (BGR=1) swaps red and blue on this panel.
  With MV=1, CASET addresses the Y axis and PASET the X axis, so pixel data
  is written one row at a time (one window per row) to go left -> right.
"""

# -- Display (HSPI, bus 1) ----------------------------------------------------
LCD_SPI_BUS  = 1
LCD_BAUDRATE = 40_000_000
LCD_CLK_PIN  = 14
LCD_MOSI_PIN = 13
LCD_MISO_PIN = 12
LCD_CS_PIN   = 15
LCD_DC_PIN   = 2
LCD_RST_PIN  = 4
LCD_BL_PIN   = 21   # backlight, HIGH = on

DISPLAY_WIDTH  = 320
DISPLAY_HEIGHT = 240

# -- Touch (VSPI, bus 2) ------------------------------------------------------
TOUCH_SPI_BUS  = 2
TOUCH_BAUDRATE = 1_000_000
TOUCH_CLK_PIN  = 25
TOUCH_MOSI_PIN = 32
TOUCH_MISO_PIN = 39
TOUCH_CS_PIN   = 33
TOUCH_IRQ_PIN  = 36
