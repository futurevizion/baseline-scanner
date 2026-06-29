#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — led_controller.py
# Controls all WS2812B LEDs via Pi5Neo (SPI on GPIO 10).
#
# LED chain order on a single data wire:
#   Ring 1 — large hole  (7 LEDs)
#   Ring 2 — small hole  (7 LEDs)
#   Ring 3 — small hole  (7 LEDs)
#   Strip  — scanner bar (32 LEDs, cut from 144LED/m roll at 22cm)
#   TOTAL: 53 LEDs
# ================================================================

import time

try:
    from pi5neo import Pi5Neo
    LEDS_AVAILABLE = True
except ImportError:
    print("  [LED] pi5neo not found — running in simulation mode.")
    LEDS_AVAILABLE = False

RING1_START  = 0;  RING1_COUNT  = 7
RING2_START  = 7;  RING2_COUNT  = 7
RING3_START  = 14; RING3_COUNT  = 7
STRIP_START  = 21; STRIP_COUNT  = 32
TOTAL_LEDS   = 53

# Colours (R, G, B)
BLUE         = (0,   60,  220)
BLUE_DIM     = (0,   15,  60)
CYAN         = (0,   180, 200)
CYAN_DIM     = (0,   40,  50)
RED          = (220, 0,   0)
RED_DIM      = (50,  0,   0)
GREEN        = (0,   180, 0)
GREEN_DIM    = (0,   40,  0)
OFF          = (0,   0,   0)

class LEDController:
    def __init__(self):
        if LEDS_AVAILABLE:
            self.neo = Pi5Neo('/dev/spidev0.0', TOTAL_LEDS, 800)
        else:
            self.neo = None

    def _fill(self, color, start=0, count=None):
        if not self.neo:
            return
        end = start + (count if count else TOTAL_LEDS - start)
        for i in range(start, end):
            self.neo.set_led_color(i, *color)

    def _push(self):
        if self.neo:
            self.neo.update_strip()

    def off(self):
        if not self.neo:
            return
        self._fill(OFF)
        self._push()

    def idle(self):
        """Rings glow very dim blue. Strip off. Waiting state."""
        if not self.neo:
            return
        self._fill(BLUE_DIM, 0, RING1_COUNT + RING2_COUNT + RING3_COUNT)
        self._fill(OFF, STRIP_START, STRIP_COUNT)
        self._push()

    def scan_animation(self):
        """
        Rings pulse bright blue.
        Strip scans top to bottom — the baseline beam.
        Total duration ~2.5 seconds.
        """
        if not self.neo:
            print("  [LED] Scan animation")
            return

        # Rings: bright blue
        self._fill(BLUE, 0, RING1_COUNT + RING2_COUNT + RING3_COUNT)
        self._push()

        # Strip: scanning beam 3 passes
        for _ in range(3):
            for pos in range(STRIP_COUNT):
                for i in range(STRIP_COUNT):
                    dist = abs(i - pos)
                    if   dist == 0: color = CYAN
                    elif dist == 1: color = (0, 70, 80)
                    elif dist == 2: color = (0, 25, 30)
                    else:           color = CYAN_DIM
                    self.neo.set_led_color(STRIP_START + i, *color)
                self._push()
                time.sleep(0.035)

    def access_granted(self):
        """All LEDs: green flash then hold dim green."""
        if not self.neo:
            print("  [LED] Access granted")
            return
        self._fill(GREEN)
        self._push()
        time.sleep(0.3)
        self._fill(GREEN_DIM)
        self._push()

    def access_denied(self):
        """All LEDs: aggressive red strobe."""
        if not self.neo:
            print("  [LED] Access denied")
            return
        for _ in range(5):
            self._fill(RED);     self._push(); time.sleep(0.12)
            self._fill(RED_DIM); self._push(); time.sleep(0.12)
        self._fill(RED_DIM)
        self._push()

