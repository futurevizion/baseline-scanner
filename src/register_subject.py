#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — register_subject.py
# Run this once for each person you want the scanner to recognize.
# Takes several good photos and saves them to the faces/ folder.
#
# Usage:
#   python3 register_subject.py alice
#   python3 register_subject.py bob
#
# The name you use here MUST match the name in config.json exactly.
#
# NOTE: Uses Picamera2 (the Pi 5 camera library). It validates that
# each photo actually contains a detectable face before saving, so
# you don't end up with blank or faceless images that break
# recognition later.
# ================================================================

import os
import sys
import time

from camera import Camera

# face_recognition is only needed to verify a face is present.
try:
    import face_recognition
    CAN_VERIFY = True
except ImportError:
    CAN_VERIFY = False

TARGET_PHOTOS = 5      # how many good photos we want
MAX_ATTEMPTS  = 25     # give up after this many tries total

if len(sys.argv) < 2:
    print("Usage: python3 register_subject.py <name>")
    print("Example: python3 register_subject.py alice")
    sys.exit(1)

name     = sys.argv[1].lower().strip()
save_dir = os.path.join("faces", name)
os.makedirs(save_dir, exist_ok=True)

print(f"\n[ BASELINE SCANNER ] Registering subject: {name}")
print("The camera will take several photos.")
print("Face the camera directly, in good light. Move your head a")
print("little between shots (slight left, right, up) for better")
print("recognition.\n")

# -- Start camera --------------------------------------------
camera = Camera(width=1280, height=720)   # higher res for registration
if not camera.is_available():
    print("ERROR: camera not available.")
    print("Check the ribbon cable is seated and try: rpicam-hello")
    sys.exit(1)

print("Warming up camera...")
camera.warm_up(frames=8)

print("Starting in 3 seconds...")
time.sleep(3)

taken    = 0
attempts = 0

while taken < TARGET_PHOTOS and attempts < MAX_ATTEMPTS:
    attempts += 1
    frame = camera.get_frame()
    if frame is None:
        print("  (no frame — retrying)")
        time.sleep(0.3)
        continue

    # Verify a face is actually present before saving.
    if CAN_VERIFY:
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Shrink a little for speed during the check.
        small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)
        locs = face_recognition.face_locations(small)
        if not locs:
            print(f"  Attempt {attempts}: no face detected — reposition and hold still.")
            time.sleep(0.6)
            continue

    # Good frame — save it.
    import cv2
    path = os.path.join(save_dir, f"{name}_{taken+1}.jpg")
    cv2.imwrite(path, frame)
    taken += 1
    print(f"  Photo {taken}/{TARGET_PHOTOS} saved. (move slightly for the next one)")
    time.sleep(1.2)

camera.close()

if taken == 0:
    print("\n  No usable photos captured. Nothing saved.")
    print("  Tips: more light, face the lens, ~1m away, hold still.")
    sys.exit(1)

print(f"\n  {taken} photo(s) saved to faces/{name}/")
if taken < TARGET_PHOTOS:
    print("  (fewer than wanted — recognition still works, but more is better.")
    print("   You can re-run this command to add more angles.)")
print(f"  Restart main.py — {name} will now be recognized.\n")

