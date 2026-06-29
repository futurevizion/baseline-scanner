# Installation & Setup

A complete walkthrough for getting Baseline Scanner running on a Raspberry
Pi 5 with 64-bit Raspberry Pi OS (Debian 13 "trixie").

Estimated time: about an hour, most of it spent compiling dlib.

---

## 1. System packages

Update first, then install the build tools and media stack:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y \
    python3-opencv mpv ffmpeg espeak rpicam-apps \
    build-essential cmake python3-dev libopenblas-dev
```

`build-essential`, `cmake`, `python3-dev`, and `libopenblas-dev` are needed
because dlib compiles from source on this platform (no prebuilt wheel exists
for ARM64 / Python 3.13).

## 2. Python dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

The dlib build (pulled in by `face_recognition`) takes roughly 20 minutes
and looks like it has stalled — it hasn't. Let it finish.

## 3. Enable SPI and I2C (only if using LEDs / OLED)

```bash
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo reboot
```

After reboot you should have `/dev/spidev0.0` (LEDs) and `/dev/i2c-1` (OLED).
Skip this step entirely if you aren't using that hardware — the code detects
their absence and continues without them.

## 4. Configuration files

```bash
cp config.example.json config.json
cp pushover_config.example.json pushover_config.json
```

- **`config.json`** — the spoken/displayed lines per person. The top-level
  keys (e.g. `person1`) must match the face folder names you create in
  step 5, plus an `unknown` entry for the denial case.
- **`pushover_config.json`** — leave `enabled` as `false` unless you want
  phone alerts (see step 8).

## 5. Register faces

Each person gets a folder under `faces/` containing one or more clear,
front-facing photos:

```
faces/
  person1/
    1.jpg
    2.jpg
```

You can add photos two ways:

- **Camera capture on the Pi:**
  ```bash
  python3 src/register_subject.py alice
  ```
- **From the dashboard** once it's running (Register Subject panel), or by
  copying image files into the folder directly.

A few photos per person from slightly different angles improves accuracy.
The detector needs roughly front-facing faces — pure profile shots won't
register.

## 6. Add your videos

Put your clips in `videos/` and reference them in `VIDEO_SEQUENCES` at the
top of `src/main.py`. Each known person maps to an ordered list of clips;
`unknown` is the fallback. The repo ships no video — supply your own.

## 7. Camera orientation

If faces aren't detected, check orientation first — an upside-down or
sideways image will not detect. `src/camera.py` rotates frames in software
(`cv2.rotate`) after capture; adjust or remove that call to match how your
camera is physically mounted.

## 8. Phone notifications (optional)

1. Install the Pushover app and create an account at https://pushover.net.
2. Create an Application there to get an API token.
3. Put your **user key** and **API token** into `pushover_config.json` and
   set `"enabled": true`.

Your keys stay local — `pushover_config.json` is git-ignored.

## 9. Bluetooth audio (optional)

Pair your speaker once with `bluetoothctl` (`scan on`, `pair <MAC>`,
`trust <MAC>`, `connect <MAC>`). If it connects but produces no sound,
restart the audio stack so it switches to the A2DP profile:

```bash
systemctl --user restart wireplumber pipewire pipewire-pulse
```

## 10. Run it

The scanner and the dashboard are **two separate programs**; run each in its
own terminal:

```bash
# Terminal 1 — the scanner (needs the desktop session for video)
python3 src/main.py

# Terminal 2 — the dashboard web server
python3 src/dashboard.py
```

Open the dashboard at `http://<pi-address>:5000`.

Video only renders from inside the Pi's graphical (Wayland) session, not
over plain SSH. For a permanent install, launch both from your compositor's
autostart so they start on boot.

## Hardening

For anything beyond a trusted home network:

- Put the dashboard behind a reverse proxy with authentication, or bind it
  to `127.0.0.1` and reach it over SSH tunneling instead of `0.0.0.0`.
- Restrict access to port 5000 at your router/firewall.
- Remember the entry photos and log are personal data — keep backups
  encrypted and never commit them.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Faces never detected | Camera orientation (see step 7), or poor lighting / not front-facing. |
| Video plays audio but no picture | Launched over SSH instead of the Pi's display session. |
| Bluetooth connects but silent | Audio profile stuck — restart the audio stack (step 9). |
| dlib install seems frozen | It's compiling; give it ~20 minutes. |
| Dashboard buttons do nothing | The scanner (`main.py`) isn't running alongside the dashboard. |
