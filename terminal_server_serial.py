#!/usr/bin/env python3
"""
Terminal to Serial Bridge - streams terminal output to ESP32 via USB serial.

This script runs on your home server and sends terminal output to the ESP32
connected via USB. Terminal commands will appear on the ESP32 display in real-time.

USAGE
    python3 terminal_server_serial.py          # use default /dev/ttyUSB0
    python3 terminal_server_serial.py --port /dev/ttyUSB1

REQUIREMENTS
    pip install pyserial

NOTES
    - Terminal output is truncated to 60 chars per line (for display)
    - Baud rate: 115200
    - Data format: UTF-8
    - Sends one line per serial write
"""

import serial
import subprocess
import sys
import time
import argparse
from threading import Thread


class TerminalSerialBridge:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False

    def connect(self):
        """Connect to serial port."""
        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1,
                write_timeout=1
            )
            print(f"✓ Connected to {self.port} @ {self.baudrate} baud")
            return True
        except Exception as e:
            print(f"✗ Failed to open {self.port}: {e}")
            print(f"  Check that ESP32 is connected and {self.port} exists")
            return False

    def send_line(self, text):
        """Send a line to ESP32, max 60 chars."""
        if not self.ser:
            return

        # Truncate to 60 chars, strip ANSI codes
        text = self._strip_ansi(text)
        text = text[:60] if len(text) > 60 else text

        try:
            self.ser.write(text.encode('utf-8', errors='ignore') + b'\n')
            self.ser.flush()
        except serial.SerialException as e:
            print(f"✗ Serial write error: {e}")
            self.running = False

    @staticmethod
    def _strip_ansi(text):
        """Remove ANSI escape codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def capture_and_stream(self):
        """Capture interactive bash and stream to ESP32."""
        print("\nStarting terminal capture (Ctrl+C to stop)...")
        print("=" * 60)

        self.running = True

        # Start interactive bash shell
        proc = subprocess.Popen(
            ['bash', '-i'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        try:
            for line in proc.stdout:
                if not self.running:
                    break

                line = line.rstrip('\n\r')
                if line:
                    # Show on home server terminal
                    print(line)
                    # Send to ESP32
                    self.send_line(line)

        except KeyboardInterrupt:
            print("\n" + "=" * 60)
            print("Shutting down...")
            self.running = False

        finally:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                proc.kill()

            if self.ser:
                self.ser.close()
                print(f"✓ Closed {self.port}")


def main():
    parser = argparse.ArgumentParser(
        description='Stream terminal to ESP32 via USB serial',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 terminal_server_serial.py
  python3 terminal_server_serial.py --port /dev/ttyUSB1
        '''
    )
    parser.add_argument(
        '--port',
        default='/dev/ttyUSB0',
        help='Serial port (default: /dev/ttyUSB0)'
    )
    parser.add_argument(
        '--baud',
        type=int,
        default=115200,
        help='Baud rate (default: 115200)'
    )

    args = parser.parse_args()

    bridge = TerminalSerialBridge(args.port, args.baud)
    if bridge.connect():
        bridge.capture_and_stream()
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
