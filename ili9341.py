"""
MicroPython ILI9341 TFT Display Driver
Hardware: ILI9341 240x320 RGB565, SPI interface
"""
from machine import Pin, SPI
import framebuf
import time

# ILI9341 Command Set
_SWRESET = const(0x01)
_SLPOUT = const(0x11)
_NORON = const(0x13)
_DISPON = const(0x29)
_CASET = const(0x2A)
_PASET = const(0x2B)
_RAMWR = const(0x2C)
_MADCTL = const(0x36)
_COLMOD = const(0x3A)
_FRMCTR1 = const(0xB1)
_DFUNCTR = const(0xB6)
_PWCTR1 = const(0xC0)
_PWCTR2 = const(0xC1)
_VMCTR1 = const(0xC5)
_VMCTR2 = const(0xC7)
_GMCTRP1 = const(0xE0)
_GMCTRN1 = const(0xE1)

# Colors — RGB565 big-endian (as sent to ILI9341)
BLACK = const(0x0000)
WHITE = const(0xFFFF)
RED = const(0xF800)
GREEN = const(0x07E0)
BLUE = const(0x001F)
YELLOW = const(0xFFE0)
CYAN = const(0x07FF)
ORANGE = const(0xFD20)
DARK_GRAY = const(0x4208)


def _swap_bytes(color):
    """Byte-swap a 16-bit color for use with MicroPython framebuf (little-endian)."""
    return ((color & 0xFF) << 8) | (color >> 8)


class ILI9341:
    def __init__(self, spi, cs_pin, dc_pin, rst_pin, width=320, height=240):
        self.spi = spi
        self.cs = Pin(cs_pin,  Pin.OUT, value=1)
        self.dc = Pin(dc_pin,  Pin.OUT)
        self.rst = Pin(rst_pin, Pin.OUT)
        self.width = width
        self.height = height
        self._init_display()

    # ---- Low-level SPI helpers ----------------------------------------

    def _cmd(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytes([cmd]))
        self.cs(1)

    def _data(self, data):
        self.dc(1)
        self.cs(0)
        self.spi.write(data if isinstance(
            data, (bytes, bytearray)) else bytes([data]))
        self.cs(1)

    # ---- Initialisation sequence --------------------------------------

    def _init_display(self):
        self.rst(0)
        time.sleep_ms(100)
        self.rst(1)
        time.sleep_ms(100)

        self._cmd(_SWRESET)
        time.sleep_ms(150)
        self._cmd(_SLPOUT)
        time.sleep_ms(150)

        self._cmd(_COLMOD)
        self._data(bytes([0x55]))          # 16-bit/pixel
        self._cmd(_MADCTL)
        self._data(bytes([0x68]))          # Landscape MV=1 MX=1, BGR

        self._cmd(_FRMCTR1)
        self._data(bytes([0x00, 0x1B]))
        self._cmd(_DFUNCTR)
        self._data(bytes([0x0A, 0x82, 0x27]))
        self._cmd(_PWCTR1)
        self._data(bytes([0x23]))
        self._cmd(_PWCTR2)
        self._data(bytes([0x10]))
        self._cmd(_VMCTR1)
        self._data(bytes([0x3E, 0x28]))
        self._cmd(_VMCTR2)
        self._data(bytes([0x86]))

        self._cmd(_GMCTRP1)
        self._data(bytes([0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08,
                          0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03,
                          0x0E, 0x09, 0x00]))
        self._cmd(_GMCTRN1)
        self._data(bytes([0x00, 0x0E, 0x14, 0x03, 0x11, 0x07,
                          0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C,
                          0x31, 0x36, 0x0F]))

        self._cmd(_NORON)
        self._cmd(_DISPON)
        time.sleep_ms(100)

    # ---- Window + raw pixel write ------------------------------------

    def _set_window(self, x0, y0, x1, y1):
        # MV=1 landscape: CASET addresses the physical-row (Y) axis,
        # PASET addresses the physical-column (X) axis.
        self._cmd(_CASET)
        self._data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._cmd(_PASET)
        self._data(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._cmd(_RAMWR)

    # ---- Drawing primitives -----------------------------------------

    def fill(self, color):
        """Fill the entire screen with a solid colour."""
        self._set_window(0, 0, self.width - 1, self.height - 1)
        hi, lo = (color >> 8) & 0xFF, color & 0xFF
        chunk = bytes([hi, lo] * 64)
        total = self.width * self.height
        self.dc(1)
        self.cs(0)
        for _ in range(total // 64):
            self.spi.write(chunk)
        rem = total % 64
        if rem:
            self.spi.write(bytes([hi, lo] * rem))
        self.cs(1)

    def fill_rect(self, x, y, w, h, color):
        """Fill a rectangle with a solid colour."""
        if w <= 0 or h <= 0:
            return
        x1 = min(x + w - 1, self.width - 1)
        y1 = min(y + h - 1, self.height - 1)
        self._set_window(x, y, x1, y1)
        hi, lo = (color >> 8) & 0xFF, color & 0xFF
        chunk = bytes([hi, lo] * 32)
        total = (x1 - x + 1) * (y1 - y + 1)
        self.dc(1)
        self.cs(0)
        for _ in range(total // 32):
            self.spi.write(chunk)
        rem = total % 32
        if rem:
            self.spi.write(bytes([hi, lo] * rem))
        self.cs(1)

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def rect(self, x, y, w, h, color):
        self.hline(x,         y,         w, color)
        self.hline(x,         y + h - 1, w, color)
        self.vline(x,         y,         h, color)
        self.vline(x + w - 1, y,         h, color)

    # ---- Text rendering ---------------------------------------------

    def draw_text(self, string, x, y, fg=WHITE, bg=BLACK, scale=1):
        """
        Draw a string at (x, y) in landscape coordinate space.
        Each display row is sent with its own window so that PASET
        increments horizontally — correct for MV=1 landscape mode.
        """
        if not string or x >= self.width or y >= self.height:
            return

        chars = len(string)
        small_w = chars * 8
        draw_w = min(small_w * scale, self.width - x)
        draw_h = min(8 * scale, self.height - y)
        row_w = min(draw_w, self.width - x)

        # --- Render 1× sentinel buffer (bg=0x0000, fg=0xFFFF) ---
        small_buf = bytearray(small_w * 8 * 2)
        small_fb = framebuf.FrameBuffer(small_buf, small_w, 8, framebuf.RGB565)
        small_fb.fill(0x0000)
        small_fb.text(string, 0, 0, 0xFFFF)

        if scale == 1:
            fg_le = _swap_bytes(fg)
            bg_le = _swap_bytes(bg)
            out_buf = bytearray(small_w * 8 * 2)
            out_fb = framebuf.FrameBuffer(out_buf, small_w, 8, framebuf.RGB565)
            out_fb.fill(bg_le)
            out_fb.text(string, 0, 0, fg_le)
            # Write one display row at a time — PASET spans the full width
            # so consecutive pixels go left-to-right on screen (correct).
            for row in range(min(8, self.height - y)):
                self._set_window(x, y + row, x + row_w - 1, y + row)
                self.dc(1)
                self.cs(0)
                offset = row * small_w * 2
                self.spi.write(out_buf[offset: offset + row_w * 2])
                self.cs(1)
            return

        # --- Scale > 1: expand each source pixel to scale×scale block ---
        fg_hi, fg_lo = (fg >> 8) & 0xFF, fg & 0xFF
        bg_hi, bg_lo = (bg >> 8) & 0xFF, bg & 0xFF

        cols_src = min(small_w, draw_w // scale)
        rows_src = min(8,       draw_h // scale)
        scaled_buf = bytearray(draw_w * draw_h * 2)

        for row in range(rows_src):
            for col in range(cols_src):
                src_i = (row * small_w + col) * 2
                is_set = small_buf[src_i] | small_buf[src_i + 1]
                c_hi = fg_hi if is_set else bg_hi
                c_lo = fg_lo if is_set else bg_lo
                for sr in range(scale):
                    for sc in range(scale):
                        br = row * scale + sr
                        bc = col * scale + sc
                        if br < draw_h and bc < draw_w:
                            bi = (br * draw_w + bc) * 2
                            scaled_buf[bi] = c_hi
                            scaled_buf[bi + 1] = c_lo

        # Write one display row at a time.
        for br in range(draw_h):
            self._set_window(x, y + br, x + draw_w - 1, y + br)
            self.dc(1)
            self.cs(0)
            offset = br * draw_w * 2
            self.spi.write(scaled_buf[offset: offset + draw_w * 2])
            self.cs(1)
