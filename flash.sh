#!/usr/bin/env bash
# flash.sh — Erase ESP32 and flash fresh MicroPython firmware, then upload files.
#
# USAGE
#   ./flash.sh
#
# PREREQUISITES
#   pip install esptool adafruit-ampy
#   source .venv/bin/activate

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ESPTOOL="$SCRIPT_DIR/.venv/bin/esptool"
AMPY="$SCRIPT_DIR/.venv/bin/ampy"
PORT="${AMPY_PORT:-/dev/ttyUSB0}"
FIRMWARE="$SCRIPT_DIR/esp32-micropython.bin"

if [[ ! -f "$FIRMWARE" ]]; then
    echo "ERROR: firmware not found at $FIRMWARE"
    exit 1
fi

echo "============================================================"
echo " Flashing MicroPython to ESP32"
echo " Port    : $PORT"
echo " Firmware: $(basename "$FIRMWARE")"
echo "============================================================"
echo ""

echo "Step 1: Erasing flash..."
"$ESPTOOL" --chip esp32 --port "$PORT" erase_flash
echo ""

echo "Step 2: Writing firmware..."
"$ESPTOOL" --chip esp32 --port "$PORT" --baud 460800 write_flash -z 0x1000 "$FIRMWARE"
echo ""

echo "Step 3: Waiting for device to reboot..."
sleep 3
echo ""

echo "Step 4: Uploading application files..."
bash "$SCRIPT_DIR/upload.sh" --no-reboot
echo ""

echo "Step 5: Rebooting into new firmware..."
"$AMPY" --port "$PORT" reset

echo ""
echo "Done. Connect to serial console:"
echo "  screen $PORT 115200"
