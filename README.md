# ESP32-CYD Gundam Home Display

MicroPython firmware for an **ESP32 Cheap Yellow Display** (ILI9341 320×240 touch screen) that shows
live market prices and home-server metrics, dressed in an RX-78-2 Gundam theme.

Tap the screen to cycle through five screens:

| # | Screen | What it shows |
|---|--------|---------------|
| 1 | **Market** | Gold DOJI HCM, Gold Thanh Tâm 9999 (VND) and BTC/USDT. Refreshes every 30 min with a White Base catapult loading screen: each data source lights green (or red `NO SIGNAL`), then the RX-78-2 launches. |
| 2 | **RX-78-2 cockpit** | Animated HUD: star field, Earth limb, heading tape, radar sweep, locked-on Zaku, beam-rifle shots. |
| 3 | **Zaku cockpit** | Zeon-style amber HUD from Char's MS-06S: mono-eye scanner, fan radar, RX-78-2 target, MG tracers, incoming beam hits. |
| 4 | **Mobile suits** | Pixel-art RX-78-2 vs Char's Zaku II. |
| 5 | **Home server** | CPU / RAM / disk / load from a local Prometheus (node_exporter), every 15 s. |

## Hardware

- ESP32-CYD (ESP32-D0WD-V3, 4 MB flash) with ILI9341 2.8" display and XPT2046 touch
- MicroPython **1.23.0** firmware
- USB cable on `/dev/ttyUSB0` (CH340). Use a good cable/port: weak USB power can reset the board when WiFi starts.

Pin assignments live in [`board_config.py`](board_config.py).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `config.py` (not tracked in git):

```python
WIFI_SSID = "your-ssid"
WIFI_PASSWORD = "your-password"
PROMETHEUS_HOST = "192.168.1.10"
PROMETHEUS_PORT = 9090
DNS_SERVER = "1.1.1.1"   # optional; overrides the DHCP resolver ("" keeps DHCP's)
```

## Deploy

```bash
./upload.sh              # compile modules to .mpy, upload, reboot
./upload.sh --no-reboot
screen /dev/ttyUSB0 115200   # serial log (Ctrl-A then K to exit)
```

`upload.sh` precompiles every module except `main.py` and `config.py` with `mpy-cross` (version must
match the firmware) and removes stale `.py` copies on the device, since MicroPython would import the
`.py` first.

First-time flash (erase + firmware + upload, needs `esp32-micropython.bin`): `./flash.sh`.

## Data sources

| Data | Source |
|------|--------|
| BTC/USDT | `api.binance.com` ticker |
| Gold DOJI HCM | `vang.today` API |
| Gold Thanh Tâm 9999 | `tuanquangdong.com` live-price JSON |
| Server metrics | Local Prometheus HTTP API |

## Troubleshooting

- **Data only loads on the first boot, then `EHOSTUNREACH` / `-202`** — WiFi dropped because the IDF
  heap ran out (the MicroPython heap grows into it and never shrinks). Avoid big contiguous
  allocations; see the memory notes in `CLAUDE.md`. The app also reconnects WiFi before each fetch.
- **Fetching takes 15–30 s** — slow LAN DNS. Set `DNS_SERVER` in `config.py` (default `1.1.1.1`).
- **Red and blue swapped** — the display needs `MADCTL = 0x60` (RGB order), see `ili9341.py`.
- **USB keeps disconnecting** — reseat the cable or use another port; the board draws a current
  spike when WiFi starts.
