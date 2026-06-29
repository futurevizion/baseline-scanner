# Baseline Scanner

A facial-recognition entry display for the Raspberry Pi, inspired by the
"baseline test" interrogation scenes in *Blade Runner 2049*. Mount a camera
by your door, register the faces you want it to know, and it plays a
personalized video sequence when it recognizes someone — and a "denied"
sequence when it doesn't.

It runs as a kiosk on a Pi-connected screen, speaks through a Bluetooth
speaker, drives an addressable LED ring, and serves a retro CRT-styled web
dashboard you can open from your phone.

> This is a hobby art project, not a security product. See **Security &
> privacy** below before you point a camera at anything.

## Features

- **Face recognition** on a live camera using `face_recognition` (dlib).
- **Per-person video sequences** — each known face triggers its own clip
  set; unknown faces get a denial clip.
- **Kiosk playback** — full-screen video on the Pi's own display via `mpv`.
- **Bluetooth audio** — routes sound to a paired speaker through PipeWire.
- **Addressable LEDs** — scan / granted / denied animations over SPI.
- **Optional OLED** — small status display over I2C (degrades gracefully if
  absent).
- **Push notifications** — optional phone alert with a photo on each entry
  via [Pushover](https://pushover.net).
- **Web dashboard** — CRT-styled control terminal: live camera feed with
  face boxes, start/stop controls, a searchable entry log with photos, and
  browser-based face registration.
- **Automatic cleanup** — entry photos older than a configurable age are
  pruned nightly.

## Hardware

| Part | Notes |
| --- | --- |
| Raspberry Pi 5 | Developed and tested on Pi 5 (64-bit Raspberry Pi OS, Debian 13 "trixie"). |
| Pi Camera Module 3 | Any `libcamera`-supported camera should work. |
| Display | Any HDMI screen for the kiosk video. |
| Bluetooth speaker | Optional, for audio. |
| WS2812 / NeoPixel LEDs | Optional, driven over SPI (GPIO 10). |
| SSD1306 OLED | Optional, over I2C. |

Everything except the Pi and camera is optional — the code degrades
gracefully when hardware isn't present.

## Quick start

```bash
cd baseline-scanner
cp config.example.json config.json
cp pushover_config.example.json pushover_config.json
pip install -r requirements.txt --break-system-packages
```

Then follow **[INSTALL.md](INSTALL.md)** for the full setup: system
packages, enabling SPI/I2C, registering faces, adding your videos, audio
pairing, and kiosk auto-start.

## You supply your own videos

The repository ships **no video files**. Movie clips are copyrighted and
can't be redistributed. Create or source your own clips, drop them in
`videos/`, and list them in `VIDEO_SEQUENCES` at the top of `src/main.py`.
The defaults expect filenames like `welcome_1.mp4` and `denied.mp4` — rename
to taste.

## Security & privacy

This project is built for a **trusted home LAN**, not the open internet.

- The dashboard has **no authentication** and binds to all interfaces on
  port 5000. Anyone who can reach that port can view the feed and control
  the scanner. Keep it behind your router; do not port-forward it.
- It stores **photos of real people** and a timestamped **entry log**. These
  are git-ignored by default and never leave your device. Treat them as
  sensitive.
- `pushover_config.json` holds your private API keys. It is git-ignored.
  Never commit it.

See [INSTALL.md](INSTALL.md#hardening) for hardening suggestions.

## License

**Proprietary — all rights reserved.** See [LICENSE](LICENSE).

This software may not be used, copied, modified, distributed, or sold
without the prior written permission of the copyright holder. It is shared
privately and is not open source.

All video and audio assets are supplied by the end user; none ship with this
software.
