# Baseline Scanner

A facial-recognition entry display for the Raspberry Pi. Mount a camera at
your door, register the faces it should know, and it plays a personalized
video sequence the moment it recognizes someone — and a "denied" sequence
for anyone it doesn't. It runs full-screen on a connected display, speaks
through a Bluetooth speaker, drives an addressable LED ring, and serves a
retro CRT-styled web dashboard you can open from your phone.

The look and feel are inspired by the replicant-interrogation scenes of
dystopian sci-fi cinema — green phosphor, scanlines, and a cold terminal
readout. All video and audio are supplied by you; none ship with the code.

---

## Features

- **Face recognition** on a live camera feed using `face_recognition` (dlib)
- **Per-person video sequences** — each known face triggers its own clip set;
  unknown faces get a denial clip
- **Full-screen playback** on the Pi's own display via `mpv`
- **Bluetooth audio** routed through PipeWire to a paired speaker
- **Addressable LEDs** — scan, granted, and denied animations over SPI
- **Optional OLED** status readout over I2C (skipped automatically if absent)
- **Phone notifications** with a photo on each entry, via Pushover (optional)
- **CRT web dashboard** — live camera feed with face boxes, start/stop
  controls, a searchable entry log with photos, and browser-based face
  registration
- **Password-protected** dashboard with a styled login
- **Remote access** from anywhere over a private Tailscale network
- **Encoding cache** for near-instant startup after the first boot
- **Automatic cleanup** of entry photos older than a set age
- **Runs on boot** — both the scanner and dashboard start automatically

---

## Hardware

| Component | Details |
| --- | --- |
| **Raspberry Pi** | Pi 5 recommended, running 64-bit Raspberry Pi OS (Debian 13 "trixie") |
| **Camera** | Pi Camera Module 3, or any `libcamera`-supported camera |
| **Display** | Any HDMI screen for the full-screen video |
| **Bluetooth speaker** *(optional)* | For recognition audio |
| **WS2812 / NeoPixel ring** *(optional)* | Driven over SPI (GPIO 10) |
| **SSD1306 OLED** *(optional)* | Small status display over I2C |

Only the Pi and camera are required. Everything else is optional — the code
detects missing hardware and carries on without it.

---

## Quick Start

### 1. Enable SPI and I2C (only if using LEDs or the OLED)

```
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo reboot
```

### 2. Install system packages

```
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y python3-opencv mpv ffmpeg espeak rpicam-apps \
    build-essential cmake python3-dev libopenblas-dev
```

The build tools are needed because dlib compiles from source on this
platform — there is no prebuilt wheel for ARM64 on Python 3.13.

### 3. Install Python dependencies

```
pip install -r requirements.txt --break-system-packages
```

The dlib build takes around 20 minutes and looks frozen while it works. It
isn't — let it finish.

### 4. Configure

```
cp config.example.json config.json
cp pushover_config.example.json pushover_config.json
```

`config.json` holds the spoken and on-screen lines for each person.
`pushover_config.json` stays disabled unless you want phone alerts.

### 5. Register faces

Each person gets a folder under `faces/` with one or more clear,
front-facing photos:

```
faces/
  alice/
    1.jpg
    2.jpg
```

Add them from the Pi with `python3 src/register_subject.py alice`, from the
dashboard's Register Subject panel, or by copying image files in directly. A
few photos per person from slightly different angles improves accuracy.

### 6. Add your videos

Drop your clips in `videos/` and list them in `VIDEO_SEQUENCES` at the top
of `src/main.py`. Each known person maps to an ordered list of clips;
`unknown` is the fallback.

### 7. Run

The scanner and the dashboard are two separate programs. Run each in its own
terminal:

```
python3 src/main.py        # the scanner (needs the desktop session)
python3 src/dashboard.py   # the web dashboard
```

Open the dashboard at `http://<pi-address>:5000`.

Video only renders from inside the Pi's graphical session, not over plain
SSH. For a permanent install, launch both from your compositor's autostart
so they start on boot.

---

## Videos and Audio

No media ships with this code. You supply your own:

- **Entry clips** — your own footage, listed per person in `VIDEO_SEQUENCES`
- **Standby loop** — an idle clip that plays between scans
- **HAL-style hum** — if you want the ambient standby tone heard in the demo,
  it comes from a Creative Commons clip on YouTube; download it yourself from
  the source and drop it in `videos/`

Keeping media user-supplied is deliberate — it keeps the project free of
third-party copyrighted material.

---

## The Dashboard

A CRT-styled control terminal, reachable from any browser on your network.

- **Live feed** — the door camera with green boxes around detected faces
- **Pause / Resume** — stop and start recognition without killing the scanner
- **Entry log** — every event, newest first, with the captured photo and a
  click-through subject dossier
- **Register subject** — upload a face and reload the scanner, all from the
  browser
- **Login** — username and password, set in `auth_config.json`

The scanner (`main.py`) and the dashboard (`dashboard.py`) must both be
running for the live feed and controls to do anything.

---

## Remote Access (optional)

To reach the dashboard from outside your home, use
[Tailscale](https://tailscale.com) — a free private network that connects
only your own devices, with nothing exposed to the public internet.

```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

Install Tailscale on your phone too, sign in with the same account, and
reach the dashboard at `http://<tailscale-ip>:5000` from anywhere. Combined
with the dashboard login, that's two layers between the outside world and
your scanner.

> Do **not** port-forward the dashboard to the open internet. Tailscale is
> the safe way to get remote access.

---

## Run on Boot

For a permanent install, launch the scanner and dashboard from your
compositor's autostart. A `start_scanner.sh` launcher is included that sets
the display environment, starts the dashboard in the background, waits, then
starts the scanner in the foreground. Point your autostart at it:

```
/home/pi/start_scanner.sh &
```

Both services then come up automatically after a reboot or power loss.

---

## Project Structure

```
baseline-scanner/
├── README.md
├── INSTALL.md                 # detailed setup notes
├── LICENSE
├── requirements.txt
├── config.example.json        # voice / display lines per person
├── pushover_config.example.json
├── src/
│   ├── main.py                # scanner: camera, recognition, playback, live feed
│   ├── camera.py              # camera capture + orientation
│   ├── video_player.py        # mpv full-screen playback
│   ├── led_controller.py      # WS2812 LED animations
│   ├── oled_controller.py     # optional OLED status
│   ├── voice.py               # spoken lines (espeak)
│   ├── notifier.py            # Pushover phone alerts
│   ├── logger.py              # entry-log writer
│   ├── cleanup_photos.py      # prunes old entry photos
│   ├── dashboard.py           # Flask web dashboard + login
│   └── register_subject.py    # add a face from the Pi
├── templates/
│   ├── dashboard.html         # CRT control terminal
│   └── login.html             # CRT login page
├── faces/                     # registered people (one folder each)
└── videos/                    # your clips (none included)
```

---

## Configuration

### `config.json`

Top-level keys are the person folder names under `faces/`, plus an `unknown`
entry for the denial case. Each holds the display name and the lines used at
different times of day.

### Recognition tuning (`src/main.py`)

| Setting | Default | Description |
| --- | --- | --- |
| `SCAN_COOLDOWN` | `8` | Seconds before the same person triggers again |
| `MATCH_TOLERANCE` | `0.55` | Lower is stricter (fewer false matches) |
| `DETECT_SCALE` | `0.5` | Frame shrink for faster detection |
| `CAPTURE` | `1280×720` | Camera capture resolution |

---

## Troubleshooting

**Faces are never detected.** Check camera orientation first — an upside-down
or sideways image won't detect. `src/camera.py` rotates frames in software
after capture; adjust that to match how your camera is mounted. Also make
sure faces are roughly front-facing and well lit.

**Video plays audio but no picture.** The scanner was launched over SSH
instead of the Pi's display session. Start it from the Pi's desktop.

**Bluetooth connects but there's no sound.** The audio profile is stuck.
Restart the audio stack: `systemctl --user restart wireplumber pipewire pipewire-pulse`.

**The dlib install looks frozen.** It's compiling from source — give it
about 20 minutes.

**Dashboard buttons do nothing.** The scanner (`main.py`) isn't running
alongside the dashboard. Both need to be up.

**Startup is slow every time.** The first boot encodes all faces and writes
a cache; later boots load it instantly. If it re-encodes every time, make
sure the project folder is writable.

---

## License

Free for personal and noncommercial use, under the
[PolyForm Noncommercial License](LICENSE).

In plain terms:

- **You can** download it, run it at home, study it, and modify it for your
  own personal projects — free.
- **You cannot** sell it, sell hardware units based on it, or use it for any
  commercial purpose without written permission from the author.

Want to use it commercially or sell a product built on it? Get in touch for
a commercial license.
