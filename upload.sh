#!/usr/bin/env bash
# upload.sh — Upload MicroPython files to ESP32 and reboot
#
# USAGE
#   ./upload.sh              # upload all files and reboot
#   ./upload.sh --no-reboot  # upload without rebooting
#
# PREREQUISITES
#   pip install adafruit-ampy
#   source .venv/bin/activate
#
# HOW TO REBOOT MANUALLY
#   ampy --port /dev/ttyUSB0 reset
#
# HOW TO OPEN SERIAL CONSOLE (to see print/errors)
#   screen /dev/ttyUSB0 115200
#   (exit: Ctrl-A then K, or Ctrl-A then \)
#
# HOW TO UPLOAD A SINGLE FILE
#   ampy --port /dev/ttyUSB0 put <file.py>
#
# HOW TO LIST FILES ON ESP32
#   ampy --port /dev/ttyUSB0 ls
#
# HOW TO DELETE A FILE FROM ESP32
#   ampy --port /dev/ttyUSB0 rm <file.py>

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AMPY="$SCRIPT_DIR/.venv/bin/ampy"
PORT="${AMPY_PORT:-/dev/ttyUSB0}"

# Files to upload — order matters: dependencies first
FILES=(
    "config.py"              # env: WiFi + Prometheus credentials
    "board_config.py"        # hardware reference
    "xpt2046.py"             # touch controller driver
    "market_data.py"         # market data fetcher
    "ili9341.py"             # display driver
    "home_server_display.py" # server screen + Prometheus helpers
    "market_screen.py"       # market screen drawing
    "terminal_screen.py"     # terminal screen + serial input
    "app.py"                 # main loop
    "main.py"                # boot entry point
)

echo "Port: $PORT"
echo ""

for f in "${FILES[@]}"; do
    if [[ -f "$f" ]]; then
        echo -n "  Uploading $f ... "
        "$AMPY" --port "$PORT" put "$f"
        echo "done"
    else
        echo "  SKIP $f (not found)"
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
