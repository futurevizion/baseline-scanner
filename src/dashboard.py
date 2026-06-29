#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — dashboard.py
# Web control terminal: entry log, live-feed mode control,
# pause/resume scanning, and browser face registration.
#
# Run alongside main.py:   python3 dashboard.py
# Open on your phone/PC:   http://scanner.local:5000
# (The live video itself is served by main.py on port 8090;
#  this dashboard just flips the mode and embeds that stream.)
# ================================================================
from flask import Flask, render_template, jsonify, send_from_directory, request
import json
import os
import re
import subprocess

app = Flask(__name__)

PROJECT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_FILE     = os.path.join(PROJECT_DIR, "entry_log.json")
CONTROL_FILE = os.path.join(PROJECT_DIR, "scanner_control.json")
FACES_DIR    = os.path.join(PROJECT_DIR, "faces")
PHOTOS_DIR   = os.path.join(PROJECT_DIR, "static", "photos")

VALID_STATES = {"running", "paused", "live"}


# ---------- Entry log ----------
@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/entries")
def entries():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    try:
        with open(LOG_FILE, "r") as f:
            log = json.load(f)
    except json.JSONDecodeError:
        log = []
    return jsonify(log)


@app.route("/photos/<filename>")
def photo(filename):
    return send_from_directory(PHOTOS_DIR, filename)


# ---------- Mode control (live / pause / running) ----------
@app.route("/api/mode", methods=["GET", "POST"])
def mode():
    if request.method == "POST":
        data  = request.get_json(silent=True) or {}
        state = data.get("state", "running")
        if state not in VALID_STATES:
            return jsonify({"ok": False, "message": "invalid state"}), 400
        with open(CONTROL_FILE, "w") as f:
            json.dump({"state": state}, f)
        return jsonify({"ok": True, "state": state})
    # GET -> current state
    try:
        with open(CONTROL_FILE, "r") as f:
            state = json.load(f).get("state", "running")
    except Exception:
        state = "running"
    return jsonify({"state": state})


# ---------- Add subject from browser ----------
@app.route("/api/add_subject", methods=["POST"])
def add_subject():
    name = (request.form.get("name") or "").strip().lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)   # safe folder name
    if not name:
        return jsonify({"ok": False, "message": "no valid name"}), 400
    if "photo" not in request.files:
        return jsonify({"ok": False, "message": "no photo uploaded"}), 400

    file = request.files["photo"]
    if not file.filename:
        return jsonify({"ok": False, "message": "empty filename"}), 400

    # Save to a temp path first, validate a face is present, then keep it.
    person_dir = os.path.join(FACES_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    # Pick next index for this person.
    existing = [f for f in os.listdir(person_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    idx = len(existing) + 1
    save_path = os.path.join(person_dir, f"{name}_{idx}.jpg")

    tmp_path = os.path.join(PROJECT_DIR, "_upload_tmp.jpg")
    file.save(tmp_path)

    # Validate the photo actually contains a detectable face.
    try:
        import face_recognition
        img  = face_recognition.load_image_file(tmp_path)
        locs = face_recognition.face_locations(img, model="hog")
        if not locs:
            os.remove(tmp_path)
            return jsonify({"ok": False,
                            "message": "no face detected in photo"}), 200
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify({"ok": False, "message": f"validation error: {e}"}), 200

    os.replace(tmp_path, save_path)
    return jsonify({"ok": True,
                    "message": f"{name} ({len(locs)} face) -> {os.path.basename(save_path)}"})


# ---------- Reload scanner (pick up new faces) ----------
@app.route("/api/reload", methods=["POST"])
def reload_scanner():
    # The scanner auto-starts from labwc autostart, so killing it makes the
    # session relaunch it -> it reloads all faces. We kill by process name.
    try:
        subprocess.run(["pkill", "-9", "-f", "main.py"], capture_output=True)
        return jsonify({"ok": True,
                        "message": "SCANNER RELOADING — new faces will load on restart."})
    except Exception as e:
        return jsonify({"ok": False, "message": f"reload error: {e}"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

