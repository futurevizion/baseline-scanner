#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER -- camera.py
# Pi Camera Module 3 wrapper.
#
# IMPORTANT: OpenCV's cv2.VideoCapture does NOT work with the Pi
# Camera Module 3. We capture frames with rpicam-still (writes a
# JPEG), then read that JPEG back with cv2 as a BGR numpy array.
#   - is_available() -> True if the camera responds
#   - warm_up(frames) -> take a few throwaway shots to settle exposure
#   - get_frame()  -> returns a BGR numpy frame (OpenCV-style)
#   - close()      -> no-op (rpicam-still is one-shot per call)
# ================================================================
import os
import subprocess
import tempfile
import cv2

class Camera:
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.frame_path = os.path.join(tempfile.gettempdir(), "baseline_frame.jpg")
        self._available = self._check()

    def _check(self):
        """Check the camera responds by listing cameras."""
        try:
            r = subprocess.run(
                ["rpicam-still", "--list-cameras"],
                capture_output=True, timeout=10
            )
            return r.returncode == 0 and b"imx" in (r.stdout + r.stderr).lower()
        except Exception:
            return False

    def is_available(self):
        return self._available

    def _capture(self):
        """Capture one frame to disk via rpicam-still."""
        try:
            subprocess.run(
                ["rpicam-still", "-o", self.frame_path,
                 "--timeout", "400", "--nopreview",
                 "--width", str(self.width), "--height", str(self.height)],
                capture_output=True, timeout=8
            )
            return os.path.exists(self.frame_path)
        except Exception:
            return False

    def warm_up(self, frames=5):
        """Take a few throwaway captures so exposure/white-balance settle."""
        for _ in range(max(1, frames)):
            self._capture()

    def get_frame(self):
        """Capture a frame and return it as a BGR numpy array (or None).
        The camera is mounted upside-down (180). rpicam-still's --rotation
        flag is unreliable on this build, so we rotate in OpenCV after
        reading -- this is the method confirmed to make faces detectable."""
        if not self._capture():
            return None
        frame = cv2.imread(self.frame_path)
        if frame is None:
            return None
        frame = cv2.rotate(frame, cv2.ROTATE_180)
        return frame

    def close(self):
        """Nothing to release -- rpicam-still is one-shot per call."""
        try:
            if os.path.exists(self.frame_path):
                os.remove(self.frame_path)
        except Exception:
            pass

