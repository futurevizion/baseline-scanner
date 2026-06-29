#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — main.py
# Blade Runner 2049 inspired entry scanner
#
#   - Watches the camera for faces (Pi 5 / Camera Module 3)
#   - Plays HAL standby loop while idle; cinematic sequence on recognition
#   - Runs LED + OLED scan animation
#   - Speaks AI voice response (personalized per person)
#   - Saves a photo of every entry event
#   - Sends push notification to your phone with the photo
#   - Logs everything to the web dashboard
#
# To start: python3 main.py
# ================================================================

import cv2
import face_recognition
import numpy as np
import json
import os
import time
import threading
import datetime

from camera import Camera
from led_controller import LEDController
from oled_controller import OLEDController
from voice import speak
from notifier import send_notification
from logger import log_entry
import video_player

# -- Live MJPEG feed (port 8090) imports ----------------------
import threading as _threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# -- Tunable settings -----------------------------------------
SCAN_COOLDOWN   = 8      # seconds between scans (avoid repeat triggers)
MATCH_TOLERANCE = 0.55   # lower = stricter. 0.5 strict, 0.6 loose.
IDLE_SLEEP      = 0.05   # tiny pause between frames when no face (saves heat/CPU)
DETECT_SCALE    = 0.5    # 0.5 = detect on half-size frame (fast + reliable at standing distance)
UPSAMPLE        = 1      # face_locations upsample passes. 1 = reliable at 1-2 meters.
HEARTBEAT_EVERY = 10     # seconds between "watching..." heartbeat prints
CAPTURE_WIDTH   = 1280
CAPTURE_HEIGHT  = 720

# -- Video sequences per subject ------------------------------
# Map each registered subject (folder name under faces/) to the ordered
# list of video clips that should play when they are recognized. The key
# must match the subfolder name in faces/ (lowercase). "unknown" is the
# fallback sequence for anyone who is not recognized.
#
# Supply your own video files in the videos/ folder and list them here.
VIDEO_SEQUENCES = {
    "person1": [
        "welcome_1.mp4",
        "welcome_2.mp4",
    ],
    "unknown": [
        "denied.mp4",
    ],
}

# -- Load config ----------------------------------------------
with open("config.json", "r") as f:
    config = json.load(f)

# -- Load known faces -----------------------------------------
known_encodings = []
known_names = []

print("[ BASELINE SCANNER ] Loading known subjects...")
faces_dir = "faces"
if os.path.isdir(faces_dir):
    for person_name in os.listdir(faces_dir):
        person_dir = os.path.join(faces_dir, person_name)
        if not os.path.isdir(person_dir):
            continue
        for image_file in os.listdir(person_dir):
            image_path = os.path.join(person_dir, image_file)
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(person_name)
                print(f"  Subject loaded: {person_name}")

if not known_names:
    print("  WARNING: no faces registered yet. Everyone will read as UNKNOWN.")
    print("  Run: python3 register_subject.py <name>")
print(f"  {len(known_names)} encoding(s) in memory.\n")

# -- Init hardware --------------------------------------------
leds = LEDController()
oled = OLEDController()
leds.idle()
oled.show_idle()

# -- Camera (Pi 5 -- uses rpicam-still via Camera wrapper) ----
camera = Camera(width=CAPTURE_WIDTH, height=CAPTURE_HEIGHT)
if not camera.is_available():
    print("  WARNING: camera not available. Running without vision.")
else:
    print("  Camera online. Warming up sensor...")
    camera.warm_up(frames=5)

# -- State ----------------------------------------------------
last_scan_time = 0
last_heartbeat = 0
scanning       = False

print("[ BASELINE SCANNER ] System active. Monitoring entry point.\n")

# Start HAL standby loop as the idle screen.
video_player.start_standby()

# -- Live MJPEG feed (port 8090) ------------------------------
# A "for fun" door-cam stream, kept deliberately simple. It runs in a
# daemon thread and is fed frames by the main loop ONLY when the dashboard
# puts the scanner into "live" mode (via scanner_control.json). This keeps
# normal recognition resource-free. Detection runs every Nth frame at 0.25
# scale so the stream stays smooth; green boxes persist between detections.
CONTROL_FILE = "scanner_control.json"
_LIVE_LOCK = _threading.Lock()
_LIVE_JPEG = None
_LIVE = {"boxes": [], "count": 0}
_LIVE_DETECT_EVERY = 8


def _scanner_state():
    """Read scanner_control.json -> 'running' (default), 'paused', or 'live'.
    Fail-safe: any error returns 'running' so the scanner never gets stuck."""
    try:
        with open(CONTROL_FILE, "r") as f:
            return json.load(f).get("state", "running")
    except Exception:
        return "running"


def _set_live_jpeg(jpeg_bytes):
    global _LIVE_JPEG
    with _LIVE_LOCK:
        _LIVE_JPEG = jpeg_bytes


def _get_live_jpeg():
    with _LIVE_LOCK:
        return _LIVE_JPEG


class _StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/stream"):
            self.send_response(200)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=FRAME")
            self.end_headers()
            try:
                while True:
                    jpg = _get_live_jpeg()
                    if jpg is None:
                        time.sleep(0.05)
                        continue
                    self.wfile.write(b"--FRAME\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(
                        f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.03)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                pass
        else:
            self.send_response(404)
            self.end_headers()


def _start_stream_server():
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", 8090), _StreamHandler)
        srv.serve_forever()
    except Exception as e:
        print(f"  [LIVE] stream server error: {e}")


_threading.Thread(target=_start_stream_server, daemon=True).start()
print("  [LIVE] MJPEG stream server on :8090/stream")


def _live_process(frame):
    """Encode a live frame with face boxes. Detection runs every Nth frame.
    Uses the _LIVE dict (no 'global' needed) to avoid the earlier crash."""
    _LIVE["count"] += 1
    if _LIVE["count"] % _LIVE_DETECT_EVERY == 0:
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(
            rgb, number_of_times_to_upsample=0, model="hog"
        )
        _LIVE["boxes"] = [(int(t / 0.25), int(r / 0.25),
                           int(b / 0.25), int(l / 0.25))
                          for (t, r, b, l) in locs]
    for (t, r, b, l) in _LIVE["boxes"]:
        cv2.rectangle(frame, (l, t), (r, b), (0, 255, 120), 3)
    ok, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if ok:
        _set_live_jpeg(enc.tobytes())


# -- Photo save -----------------------------------------------
def save_photo(frame, name):
    """Saves entry photo and returns the filename."""
    os.makedirs(os.path.join("static", "photos"), exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = name.lower().replace(" ", "_")
    filename  = f"{safe_name}_{timestamp}.jpg"
    filepath  = os.path.join("static", "photos", filename)
    cv2.imwrite(filepath, frame)
    return filename

# -- Time-aware greeting selection ----------------------------
def get_time_variant(person_config):
    """Returns a time-aware response if defined, else the default."""
    hour = datetime.datetime.now().hour
    if 0 <= hour < 6 and "response_late_night" in person_config:
        return person_config["response_late_night"]
    elif 6 <= hour < 12 and "response_morning" in person_config:
        return person_config["response_morning"]
    elif 12 <= hour < 18 and "response_afternoon" in person_config:
        return person_config["response_afternoon"]
    elif 18 <= hour < 24 and "response_evening" in person_config:
        return person_config["response_evening"]
    return person_config.get("response", "Baseline confirmed.")

# -- Main scan sequence ---------------------------------------
def run_scan(name, frame):
    """Full scan sequence: video -> photo -> LEDs -> OLED -> log -> notify -> voice."""
    global scanning
    scanning = True

    # 1. Play the cinematic video sequence for this subject.
    sequence = VIDEO_SEQUENCES.get(name, VIDEO_SEQUENCES["unknown"])
    video_player.play_sequence(sequence)

    # 2. Save photo
    photo_filename = save_photo(frame, name)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. Trigger scanning animation
    leds.scan_animation()
    oled.show_scanning()
    time.sleep(1.0)

    if name == "unknown":
        leds.access_denied()
        oled.show_denied()
        person_config = config.get("unknown", {})
        greeting      = get_time_variant(person_config)
        display_name  = "UNKNOWN SUBJECT"
        status        = "DENIED"
    else:
        leds.access_granted()
        person_config = config.get(name, {})
        display_name  = person_config.get("display_name", name.upper())
        oled.show_granted(display_name)
        greeting = get_time_variant(person_config)
        status   = "CONFIRMED"

    print(f"  [{timestamp}] {display_name} -- {status}")

    # 4. Log to dashboard
    log_entry(name=display_name, status=status,
              photo=photo_filename, timestamp=timestamp)

    # 5. Send phone notification with photo
    send_notification(
        title="Baseline Scanner -- Entry Detected",
        message=f"{display_name} -- {status} -- {timestamp}",
        photo_path=os.path.join("static", "photos", photo_filename)
    )

    # 6. Voice greeting intentionally DISABLED — the Baseline video
    #    sequences carry their own audio. Calling speak() here caused a
    #    duplicate robotic espeak greeting to play over/after the videos.
    #    (greeting is still computed above for the dashboard log.)

    # 7. Return to idle
    time.sleep(2)
    leds.idle()
    oled.show_idle()
    scanning = False

# -- Identify a face against known encodings ------------------
def identify(encoding):
    """Returns the best-matching known name, or 'unknown'."""
    if not known_encodings:
        return "unknown"
    distances = face_recognition.face_distance(known_encodings, encoding)
    best = int(np.argmin(distances))
    if distances[best] <= MATCH_TOLERANCE:
        return known_names[best]
    return "unknown"

# -- Main loop ------------------------------------------------
try:
    while True:
        _state = _scanner_state()

        # PAUSED: skip recognition, keep loop + HAL alive, no live stream.
        if _state == "paused":
            _set_live_jpeg(None)
            time.sleep(0.4)
            continue

        if not camera.is_available():
            time.sleep(1)
            continue

        # LIVE: fast door-cam stream with periodic detection boxes.
        # No recognition / no video sequences in this mode (kept lean).
        if _state == "live":
            lframe = camera.get_frame()
            if lframe is None:
                time.sleep(0.02)
                continue
            _live_process(lframe)
            continue
        else:
            # Normal scanning mode: make sure the stream shows nothing stale.
            _set_live_jpeg(None)

        frame = camera.get_frame()
        if frame is None:
            time.sleep(IDLE_SLEEP)
            continue

        now = time.time()
        if scanning or (now - last_scan_time) < SCAN_COOLDOWN:
            time.sleep(IDLE_SLEEP)
            continue

        # Shrink for faster detection -- but only by DETECT_SCALE.
        if DETECT_SCALE != 1.0:
            small = cv2.resize(frame, (0, 0), fx=DETECT_SCALE, fy=DETECT_SCALE)
        else:
            small = frame
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locs  = face_recognition.face_locations(
            rgb, number_of_times_to_upsample=UPSAMPLE, model="hog"
        )

        if not locs:
            if now - last_heartbeat > HEARTBEAT_EVERY:
                print("  [ watching... no face in view ]")
                last_heartbeat = now
            time.sleep(IDLE_SLEEP)
            continue

        encodings = face_recognition.face_encodings(rgb, locs)
        detected  = "unknown"
        for enc in encodings:
            name = identify(enc)
            if name != "unknown":
                detected = name
                break

        print(f"  Subject detected: {detected}")
        last_scan_time = now

        # Run the scan sequence in a thread so the camera loop keeps going.
        t = threading.Thread(target=run_scan, args=(detected, frame.copy()))
        t.daemon = True
        t.start()

except KeyboardInterrupt:
    print("\n[ BASELINE SCANNER ] System offline.")
    video_player.stop_standby()
    camera.close()
    leds.off()
    oled.clear()

