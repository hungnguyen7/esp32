# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroPython firmware for an **ESP32-CYD** (Cheap Yellow Display) board running on the device itself. The device displays two screens toggled by touch:
- **Server screen**: Home server metrics pulled from a local Prometheus instance
- **Market screen**: Live Gold DOJI HCM (VND) and BTC/USDT prices

All `.py` files in the root are uploaded to the ESP32 filesystem and run under MicroPython. The host machine only needs the venv tools (`ampy`, `esptool`) to flash/upload.

## Deploying to the Device

```bash
source .venv/bin/activate

# Upload all files and reboot
./upload.sh

# Upload a single file (faster iteration)
ampy --port /dev/ttyUSB0 put <file.py>

# Full flash (erase + firmware + upload) — requires esp32-micropython.bin in project root
./flash.sh

# Serial console (see print output and errors)
screen /dev/ttyUSB0 115200   # exit: Ctrl-A then K

# Reboot manually
ampy --port /dev/ttyUSB0 reset

# List / remove files on device
ampy --port /dev/ttyUSB0 ls
ampy --port /dev/ttyUSB0 rm <file.py>
```

Override the default port via `AMPY_PORT=/dev/ttyUSBx ./upload.sh`.

## Architecture

```
main.py              → boot entry point, just calls app.main()
app.py               → main loop: hardware init, WiFi, touch polling, screen state machine
config.py            → WiFi credentials + Prometheus/terminal host:port (NOT in git)
board_config.py      → hardware constants (GPIO pins, SPI settings, display geometry)
ili9341.py           → ILI9341 display driver (SPI, RGB565, draw_text, fill_rect, etc.)
xpt2046.py           → XPT2046 touch controller driver (tapped() polled in main loop)
home_server_display.py → WiFi init, Prometheus queries, server screen drawing
market_data.py       → BTC (Binance) + Gold DOJI HCM (vang.today) HTTP fetchers
market_screen.py     → market screen drawing
```

**Data flow**: `app.py` drives the loop → calls fetch functions in `home_server_display.py` / `market_data.py` → passes result dicts to screen drawing functions → drawing functions call `ILI9341` methods directly.

**Import compatibility**: All files import with MicroPython-first fallbacks (`urequests`/`requests`, `ujson`/`json`) so they can be partially linted/tested on a host Python environment.

## Hardware

- **Board**: ESP32-CYD (ESP32-D0WD-V3, 240 MHz, 4 MB flash, 520 KB SRAM)
- **Display**: ILI9341 2.8" TFT 320×240 RGB565, HSPI bus (SPI1), 40 MHz
- **Touch**: XPT2046 resistive controller, VSPI bus (SPI2), 1 MHz
- **Serial**: `/dev/ttyUSB0` at 115200 baud (CH340 USB-UART)
- **MAC**: `b0:cb:d8:99:39:68`

MADCTL `0x68` (MV=1, MX=1, BGR=1) is required for correct landscape orientation and colour order on this specific panel.

## Key Constraints

- **MicroPython only** — no CPython stdlib, no pip packages on the device. Stick to `machine`, `network`, `time`, `ujson`, `urequests`, and the project's own drivers.
- `config.py` contains real credentials and is intentionally excluded from `.gitignore` tracking but **must** be uploaded to the device. Check `.gitignore` before assuming it is committed.
- Screen dimensions are 320×240. All drawing coordinates are hardcoded for this resolution.
- `upload.sh` uploads files in dependency order — preserve that order if adding new files.
- Refresh intervals: server screen every 15 s, market screen every 60 s (constants in `app.py`).

## Data Notes

- Gold prices from `vang.today` API come in VND × 10 (e.g., `1620000000` = 162,000,000 VND). The fetcher divides by 10 before returning. Display formats in millions (e.g., `162.0M`).
- BTC price is raw USD float from Binance.
