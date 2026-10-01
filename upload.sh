#!/usr/bin/env bash
# upload.sh — Precompile MicroPython modules to .mpy, upload to ESP32, reboot
#
# USAGE
#   ./upload.sh              # compile, upload all files and reboot
#   ./upload.sh --no-reboot  # compile and upload without rebooting
#
# WHY .mpy
#   Compiling .py source on the device needs a lot of RAM. On ESP32 the
#   MicroPython GC heap grows into the IDF heap (which the WiFi driver uses)
#   and never shrinks, so compiling the big screen modules at import time
#   leaves WiFi short of memory. mpy-cross compiles on the host instead.
#   mpy-cross must match the firmware (MicroPython 1.23.0 -> mpy v6.3).
#
#   MicroPython imports foo.py before foo.mpy, so a stale foo.py on the
#   device is removed when foo.mpy is uploaded.
#
# PREREQUISITES
#   pip install -r requirements.txt   (adafruit-ampy, mpy-cross==1.23.0)
#   source .venv/bin/activate
#
# HOW TO REBOOT MANUALLY
#   ampy --port /dev/ttyUSB0 reset
#
# HOW TO OPEN SERIAL CONSOLE (to see print/errors)
#   screen /dev/ttyUSB0 115200
#   (exit: Ctrl-A then K, or Ctrl-A then \)
#
# HOW TO UPLOAD A SINGLE MODULE
#   .venv/bin/mpy-cross -o build/<file>.mpy <file>.py
#   ampy --port /dev/ttyUSB0 put build/<file>.mpy <file>.mpy
#
# HOW TO LIST FILES ON ESP32
#   ampy --port /dev/ttyUSB0 ls

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
AMPY="$SCRIPT_DIR/.venv/bin/ampy"
MPY_CROSS="$SCRIPT_DIR/.venv/bin/mpy-cross"
PORT="${AMPY_PORT:-/dev/ttyUSB0}"
BUILD="$SCRIPT_DIR/build"

# Uploaded as plain .py: main.py is the boot entry point, config.py holds
# credentials you may want to edit on the device.
SOURCE_FILES=(
    "config.py"              # env: WiFi + Prometheus credentials (+ DNS_SERVER)
    "main.py"                # boot entry point
)

# Precompiled to .mpy — order matters: dependencies first
MODULES=(
    "board_config.py"        # hardware pins / bus settings
    "xpt2046.py"             # touch controller driver
    "market_data.py"         # market data fetcher
    "ili9341.py"             # display driver
    "gundam_theme.py"        # shared RX-78-2 theme (palette + shapes)
    "home_server_display.py" # WiFi + server screen + Prometheus helpers
    "market_screen.py"       # market screen + catapult loading screen
    "gundam_screen.py"       # RX-78-2 vs Zaku pixel-art screen
    "cockpit_screen.py"      # RX-78-2 cockpit HUD screen (uses gundam_screen)
    "zaku_cockpit_screen.py" # Zaku cockpit HUD screen (uses cockpit_screen)
    "app.py"                 # main loop
)

echo "Port: $PORT"
echo ""

mkdir -p "$BUILD"
for f in "${MODULES[@]}"; do
    "$MPY_CROSS" -o "$BUILD/${f%.py}.mpy" "$f"
done
echo "  Compiled ${#MODULES[@]} modules -> build/*.mpy"

DEVICE_FILES="$("$AMPY" --port "$PORT" ls)"

for f in "${SOURCE_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        echo -n "  Uploading $f ... "
        "$AMPY" --port "$PORT" put "$f"
        echo "done"
    else
        echo "  SKIP $f (not found)"
    fi
done

for f in "${MODULES[@]}"; do
    m="${f%.py}.mpy"
    echo -n "  Uploading $m ... "
    "$AMPY" --port "$PORT" put "$BUILD/$m" "$m"
    if grep -qx "/$f" <<< "$DEVICE_FILES"; then
        "$AMPY" --port "$PORT" rm "$f"   # stale source would shadow the .mpy
        echo "done (removed old $f)"
    else
        echo "done"
    fi
done

echo ""

if [[ "$1" != "--no-reboot" ]]; then
    echo -n "  Rebooting ESP32 ... "
    "$AMPY" --port "$PORT" reset
    echo "done"
    echo ""
    echo "Connect to serial console:"
    echo "  screen $PORT 115200"
fi
