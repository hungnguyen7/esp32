# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroPython firmware for an **ESP32-CYD** (Cheap Yellow Display) board running on the device itself. The device displays five screens cycled by touch (Market → Cockpit → Zaku cockpit → Gundam → Server; `SCREEN_ORDER` in `app.py`):
- **Market screen**: Live Gold DOJI HCM, Gold Thanh Tâm (VND) and BTC/USDT prices. While fetching it shows a White Base catapult loading screen that lights up per source, then launches the RX-78-2
- **Cockpit screen**: Animated RX-78-2 cockpit view (panoramic monitor HUD, radar sweep, heading tape, locked-on Zaku, beam shots)
- **Zaku cockpit screen**: Animated Zeon-style MS-06S cockpit (amber HUD, mono-eye scanner, fan radar, RX-78-2 target, MG tracers, incoming beam hits)
- **Gundam screen**: Static pixel-art RX-78-2 vs Char's Zaku
- **Server screen**: Home server metrics pulled from a local Prometheus instance

All `.py` files in the root run on the ESP32 under MicroPython 1.23.0. `upload.sh` precompiles them to `.mpy` with `mpy-cross` (except `main.py` and `config.py`) and uploads them. The host only needs the venv tools (`ampy`, `mpy-cross`, `esptool`).

## Deploying to the Device

```bash
source .venv/bin/activate
pip install -r requirements.txt     # adafruit-ampy, mpy-cross==1.23.0 (must match firmware), host stubs

# Compile to .mpy, upload everything, reboot
./upload.sh
./upload.sh --no-reboot

# Upload a single module (faster iteration) — compile first, upload as .mpy
mpy-cross -o build/<file>.mpy <file>.py
ampy --port /dev/ttyUSB0 put build/<file>.mpy <file>.mpy

# Full flash (erase + firmware + upload) — requires esp32-micropython.bin in project root
./flash.sh

# Serial console (see print output and errors)
screen /dev/ttyUSB0 115200   # exit: Ctrl-A then K

# Reboot manually (add --hard for a full reset that also clears WiFi/DNS state)
ampy --port /dev/ttyUSB0 reset

# List / remove files on device
ampy --port /dev/ttyUSB0 ls
ampy --port /dev/ttyUSB0 rm <file>
```

Override the default port via `AMPY_PORT=/dev/ttyUSBx ./upload.sh`.

MicroPython imports `foo.py` before `foo.mpy`: never leave a stale `.py` next to its `.mpy` on the device (`upload.sh` removes them). Do not `ampy put` a raw `.py` module unless you also delete its `.mpy`, or vice versa.

## Architecture

```
main.py              → boot entry point, just calls app.main()
app.py               → main loop: hardware init, WiFi, touch polling, screen state machine
config.py            → WiFi credentials + Prometheus host:port + optional DNS_SERVER (NOT in git)
board_config.py      → hardware pins and SPI bus settings (single source of truth, imported by app.py)
ili9341.py           → ILI9341 display driver (SPI, RGB565, draw_text, fill_rect, blit_row)
xpt2046.py           → XPT2046 touch controller driver (tapped() polled in main loop)
home_server_display.py → WiFi init/ensure_wifi/DNS, Prometheus queries, server screen drawing
market_data.py       → BTC (Binance) + Gold DOJI HCM (vang.today) + Gold Thanh Tâm (tuanquangdong.com) HTTP fetchers
gundam_theme.py      → shared RX-78-2 theme: palette, header/footer, chamfered plates, hazard stripes
market_screen.py     → market screen + catapult loading screen (draw_loading / loading_step / launch)
gundam_screen.py     → static RX-78-2 vs Zaku pixel-art screen (sprites as char grids, one SPI write per row)
cockpit_screen.py    → cockpit HUD screen: draw_screen() full frame, tick() partial-region animation called from the main loop
zaku_cockpit_screen.py → Zeon-style Zaku cockpit: same draw_screen()/tick() pattern, reuses cockpit_screen helpers
```

**Data flow**: `app.py` drives the loop → calls fetch functions in `home_server_display.py` / `market_data.py` → passes result dicts to screen drawing functions → drawing functions call `ILI9341` methods directly. `market_data.fetch_all(on_step)` calls `on_step(index, ok, data)` after each source so the loading screen can update between the blocking HTTP calls.

**Redraw pattern**: screens draw the full frame once on screen switch, then redraw only changed regions (`cockpit*.tick()`, `server.update_screen()`), because full-screen redraws are slow (~1 s) and flicker.

**Import compatibility**: All files import with MicroPython-first fallbacks (`urequests`/`requests`, `ujson`/`json`) so they can be partially linted/tested on a host Python environment.

## Hardware

- **Board**: ESP32-CYD (ESP32-D0WD-V3, 240 MHz, 4 MB flash, 520 KB SRAM), MicroPython 1.23.0
- **Display**: ILI9341 2.8" TFT 320×240 RGB565, HSPI bus (SPI1), 40 MHz
- **Touch**: XPT2046 resistive controller, VSPI bus (SPI2), 1 MHz
- **Serial**: `/dev/ttyUSB0` at 115200 baud (CH340 USB-UART)
- **MAC**: `b0:cb:d8:99:39:68`

MADCTL `0x60` (MV=1, MX=1, RGB order) is required for correct landscape orientation and colour order on this specific panel. `0x68` (BGR=1) swaps red and blue.

## Key Constraints

- **MicroPython only** — no CPython stdlib, no pip packages on the device. Stick to `machine`, `network`, `time`, `ujson`, `urequests`, and the project's own drivers.
- **Memory / WiFi**: the GC heap grows into the IDF heap when an allocation fails even after a collection, and never gives it back; the WiFi driver lives on the IDF heap. If it runs out, WiFi drops (status 201) and cannot reconnect. Avoid large contiguous allocations (stream rows with small reused buffers, as `draw_text` and `draw_sprite` do), keep the `gc.collect()` calls in `app.py`, and check `esp32.idf_heap_info(esp32.HEAP_DATA)` when adding heavy features.
- **DNS**: the LAN resolver (192.168.1.199) is unreliable for the ESP32 (fails right after connect, 6–7 s per lookup). `_apply_dns()` switches to `DNS_SERVER` (default `1.1.1.1`) after connect; this makes the IP config static until the next reboot.
- `config.py` contains real credentials and is intentionally excluded via `.gitignore` but **must** be uploaded to the device. Check `.gitignore` before assuming it is committed.
- Screen dimensions are 320×240. All drawing coordinates are hardcoded for this resolution.
- `upload.sh` uploads modules in dependency order — preserve that order if adding new files, and add new modules to its `MODULES` list.
- Refresh intervals: server screen every 15 s, market data every 30 min (constants in `app.py`).

## Data Notes

- Gold prices from `vang.today` API come in VND × 10 (e.g., `1620000000` = 162,000,000 VND). The fetcher divides by 10 before returning. Display formats in millions (e.g., `162.0M`).
- BTC price is raw USD float from Binance.
- All HTTP responses are closed in `try/finally` (`market_data._get_json`, `query_prometheus`) so failed parses do not leak sockets.
