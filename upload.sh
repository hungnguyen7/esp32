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

PORT="${AMPY_PORT:-/dev/ttyUSB0}"

# Files to upload — order matters: dependencies first
FILES=(
    "config.py"              # env: WiFi + Prometheus credentials
    "ili9341.py"             # display driver
    "home_server_display.py" # main app
    "main.py"                # boot entry point
)

echo "Port: $PORT"
echo ""

for f in "${FILES[@]}"; do
    if [[ -f "$f" ]]; then
        echo -n "  Uploading $f ... "
        ampy --port "$PORT" put "$f"
        echo "done"
    else
        echo "  SKIP $f (not found)"
    fi
done

echo ""

if [[ "$1" != "--no-reboot" ]]; then
    echo -n "  Rebooting ESP32 ... "
    ampy --port "$PORT" reset
    echo "done"
    echo ""
    echo "Connect to serial console:"
    echo "  screen $PORT 115200"
fi
