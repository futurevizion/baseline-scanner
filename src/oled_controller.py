#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — oled_controller.py
# Controls the 0.96" SSD1306 OLED display over I2C.
# All screen text uses Blade Runner 2049 language and tone.
#
# HEADLESS-SAFE: if luma isn't installed OR no physical screen is
# wired, the controller runs in simulation mode (prints to console)
# instead of crashing the whole scanner. Wire the OLED later and it
# lights up automatically — no code change needed.
# ================================================================

import time

try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    from luma.core.render import canvas
    OLED_AVAILABLE = True
except ImportError:
    print("  [OLED] luma.oled not found — running in simulation mode.")
    OLED_AVAILABLE = False


class OLEDController:
    def __init__(self):
        # Default to headless; only attach a real device if both the
        # library is present AND the hardware actually responds on I2C.
        self.device = None
        if OLED_AVAILABLE:
            try:
                serial = i2c(port=1, address=0x3C)
                self.device = ssd1306(serial)
                print("  [OLED] Display detected — screen active.")
            except Exception as e:
                print(f"  [OLED] No display on I2C ({e.__class__.__name__}) — running headless.")
                self.device = None

    def _draw(self, fn):
        if not self.device:
            return
        with canvas(self.device) as draw:
            fn(draw)

    def clear(self):
        self._draw(lambda d: None)

    def show_idle(self):
        if not self.device:
            print("  [OLED] Idle")
            return
        with canvas(self.device) as draw:
            draw.text((2, 0),  "NEXUS DIVISION",    fill="white")
            draw.text((2, 10), "BASELINE SCANNER",  fill="white")
            draw.line([(0,22),(127,22)],fill="white",width=1)
            draw.text((2, 26), "MONITORING...",     fill="white")
            draw.text((2, 38), "ENTRY POINT ACTIVE",fill="white")
            draw.text((2, 50), "> AWAITING SUBJECT",fill="white")

    def show_scanning(self):
        if not self.device:
            print("  [OLED] Scanning...")
            return
        frames = [
            ("BASELINE TEST",   "INITIATING...  "),
            ("RETINAL SCAN",    "[>>          ] "),
            ("RETINAL SCAN",    "[>>>>>       ] "),
            ("CELLULAR MAP",    "[>>>>>>>>    ] "),
            ("INTERLINK CHECK", "[>>>>>>>>>>>]  "),
            ("ANALYZING...",    "CELLS INTERLINKED"),
            ("CROSS-REFERENCE", "MEMORY ARCHIVE  "),
        ]
        for line1, line2 in frames:
            with canvas(self.device) as draw:
                draw.text((2, 0),  "NEXUS DIVISION",  fill="white")
                draw.line([(0,12),(127,12)],fill="white",width=1)
                draw.text((2, 16), line1,             fill="white")
                draw.text((2, 30), line2,             fill="white")
                draw.text((2, 44), "STAND BY...",     fill="white")
            time.sleep(0.22)

    def show_granted(self, name):
        if not self.device:
            print(f"  [OLED] Confirmed: {name}")
            return
        with canvas(self.device) as draw:
            draw.text((2, 0),  "BASELINE CONFIRMED", fill="white")
            draw.line([(0,12),(127,12)],fill="white",width=1)
            # Name — truncate if too long for screen
            display = name[:16] if len(name) > 16 else name
            draw.text((2, 16), display,              fill="white")
            draw.text((2, 30), "CELLS INTERLINKED",  fill="white")
            draw.text((2, 42), "ACCESS: GRANTED",    fill="white")
            draw.ellipse([(118,44),(126,52)],         fill="white")

    def show_denied(self):
        if not self.device:
            print("  [OLED] DENIED")
            return
        with canvas(self.device) as draw:
            draw.text((2, 0),  "!! ALERT !!",        fill="white")
            draw.line([(0,12),(127,12)],fill="white",width=1)
            draw.text((2, 16), "UNKNOWN SUBJECT",    fill="white")
            draw.text((2, 30), "BASELINE FAILURE",   fill="white")
            draw.text((2, 42), "NOT INTERLINKED",    fill="white")
            draw.text((2, 54), "ACCESS: DENIED",     fill="white")

