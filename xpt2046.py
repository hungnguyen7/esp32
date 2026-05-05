"""
xpt2046.py — XPT2046 resistive touch controller driver for MicroPython.

ESP32 CYD wiring (VSPI / SPI bus 2):
  CLK  → GPIO 25   MOSI → GPIO 32
  MISO → GPIO 39   CS   → GPIO 33   IRQ  → GPIO 36

Note: GPIO 36 and 39 are input-only pins on ESP32 and do NOT support
internal pull-ups. The CYD PCB has a 10kΩ hardware pull-up on IRQ,
so no software pull-up is needed or possible.
"""
from machine import Pin, SPI
import time

_CMD_READ_X = const(0xD0)
_CMD_READ_Y = const(0x90)

# Debounce: minimum ms between consecutive tap events
_DEBOUNCE_MS = const(600)


class XPT2046:
    # Raw 12-bit ADC calibration range — tune if touch offset is visible.
    _X_MIN = const(200)
    _X_MAX = const(3900)
    _Y_MIN = const(200)
    _Y_MAX = const(3900)

    def __init__(self, spi, cs_pin, irq_pin):
        self.spi = spi
        self.cs = Pin(cs_pin,  Pin.OUT, value=1)
        # GPIO 36 is input-only; no pull mode argument.
        self.irq = Pin(irq_pin, Pin.IN)
        self._was_pressed = False
        self._last_tap_ms = 0

    def is_pressed(self):
        """Return True when the panel is being touched (IRQ pulled low)."""
        return self.irq.value() == 0

    def tapped(self):
        """
        Returns True exactly once per tap — fires on the FALLING edge
        (finger touches screen) with a debounce guard.
        Firing on press-start (not release) means it is never missed
        even when the main loop is slow due to screen redraws.
        """
        now = time.ticks_ms()
        pressed = self.is_pressed()

        if pressed and not self._was_pressed:
            # Falling edge detected — new finger contact.
            if time.ticks_diff(now, self._last_tap_ms) > _DEBOUNCE_MS:
                self._last_tap_ms = now
                self._was_pressed = True
                return True
        elif not pressed:
            self._was_pressed = False

        return False

    def _read_adc(self, cmd):
        """Send one XPT2046 command and return the 12-bit ADC result."""
        tx = bytearray([cmd, 0x00, 0x00])
        rx = bytearray(3)
        self.cs(0)
        self.spi.write_readinto(tx, rx)
        self.cs(1)
        # Result sits in bits [14:3] of the 16-bit word starting at rx[1].
        return ((rx[1] << 8) | rx[2]) >> 3

    def read(self):
        """
        Return (x, y) in display pixel coordinates (0–319, 0–239),
        or None if the panel is not being touched.
        Takes three samples and returns the median to reduce noise.
        """
        if not self.is_pressed():
            return None
        xs, ys = [], []
        for _ in range(3):
            xs.append(self._read_adc(_CMD_READ_X))
            ys.append(self._read_adc(_CMD_READ_Y))
            time.sleep_ms(2)
        raw_x = sorted(xs)[1]
        raw_y = sorted(ys)[1]
        x = int((raw_x - self._X_MIN) * 320 / (self._X_MAX - self._X_MIN))
        y = int((raw_y - self._Y_MIN) * 240 / (self._Y_MAX - self._Y_MIN))
        return max(0, min(319, x)), max(0, min(239, y))
