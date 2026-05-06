"""
terminal_screen.py - Terminal display via USB serial on ESP32.

Receives terminal output from home server via serial port (UART2)
and renders it on ILI9341 display.
"""
from ili9341 import BLACK, WHITE, GREEN, DARK_GRAY
from machine import UART
import time

SCREEN_W = 320
SCREEN_H = 240
LINES_PER_SCREEN = 15
LINE_HEIGHT = 14

# Serial UART for communication (RX=16, TX=17 on ESP32-CYD)
# UART2 is used for terminal communication from home server
uart = UART(2, baudrate=115200, tx=17, rx=16)

# Buffer to hold recent terminal lines
terminal_lines = []


def read_serial_lines():
    """Read available serial data and update buffer."""
    global terminal_lines

    if uart.any():
        try:
            data = uart.read(256)  # Read up to 256 bytes
            text = data.decode('utf-8', errors='ignore')
            lines = text.split('\n')

            for line in lines:
                line = line.rstrip('\r')
                if line:
                    terminal_lines.append(line)
                    # Keep only last 50 lines in memory
                    if len(terminal_lines) > 50:
                        terminal_lines.pop(0)
        except Exception as e:
            print("Serial read error:", e)


def draw_terminal_screen(disp):
    """Render terminal output on display."""
    disp.fill(BLACK)

    # Title bar
    disp.fill_rect(0, 0, SCREEN_W, 20, DARK_GRAY)
    disp.draw_text("TERMINAL", 10, 4, WHITE, DARK_GRAY, scale=1)

    # Terminal content
    y = 24

    if not terminal_lines:
        disp.draw_text("Waiting for terminal...", 10, y, WHITE, BLACK, scale=1)
        return

    # Show last LINES_PER_SCREEN lines
    start_idx = max(0, len(terminal_lines) - LINES_PER_SCREEN)
    for line in terminal_lines[start_idx:]:
        # Truncate long lines (max 40 chars for 320px width at scale=1)
        display_line = line[:40] if len(line) > 40 else line
        disp.draw_text(display_line, 4, y, GREEN, BLACK, scale=1)
        y += LINE_HEIGHT
        if y > SCREEN_H - 10:
            break

    # Status bar
    disp.hline(0, SCREEN_H - 12, SCREEN_W, DARK_GRAY)
    num_lines = len(terminal_lines)
    status_text = "Lines: {}".format(num_lines)
    disp.draw_text(status_text, 200, SCREEN_H - 8, WHITE, BLACK, scale=1)
