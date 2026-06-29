#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER -- video_player.py
# HAL standby loop + recognition cinematic sequences.
# One process owns the screen: HAL loops while idle; on recognition
# we stop HAL, play the sequence, then restart HAL.
# ================================================================

import os
import subprocess

VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
STANDBY_FILE = "HAL_standby_small.mp4"

_ENV = dict(os.environ)
_ENV["WAYLAND_DISPLAY"] = "wayland-0"
_ENV["XDG_RUNTIME_DIR"] = "/run/user/1000"

# Flags shared by every mpv launch.
# --no-border / --force-window / --background keep a solid black-backed,
# borderless window covering the screen so the desktop never peeks through
# during the brief handoff between HAL and a sequence.
_MPV_BASE = [
    "mpv",
    "--fullscreen",
    "--vo=gpu",
    "--gpu-context=wayland",
    "--gpu-api=opengl",
    "--no-terminal",
    "--no-input-default-bindings",
    "--no-border",
    "--force-window=yes",
    "--idle=no",
]

# Holds the running HAL standby process (or None).
_standby_proc = None


def start_standby():
    """Start HAL looping fullscreen as the idle screen."""
    global _standby_proc
    if _standby_proc is not None and _standby_proc.poll() is None:
        return  # already running
    path = os.path.join(VIDEO_DIR, STANDBY_FILE)
    if not os.path.exists(path):
        print(f"  [STANDBY] MISSING: {STANDBY_FILE}")
        return
    print("  [STANDBY] HAL idle loop started.")
    _standby_proc = subprocess.Popen(
        _MPV_BASE + ["--loop", path], env=_ENV
    )


def stop_standby():
    """Stop the HAL idle loop (before playing a sequence)."""
    global _standby_proc
    if _standby_proc is not None:
        _standby_proc.terminate()
        try:
            _standby_proc.wait(timeout=3)
        except Exception:
            _standby_proc.kill()
        _standby_proc = None
        print("  [STANDBY] HAL idle loop stopped.")


def play_sequence(filenames):
    """Stop HAL, play the clips fullscreen back-to-back, then restart HAL."""
    paths = []
    for name in filenames:
        p = os.path.join(VIDEO_DIR, name)
        if os.path.exists(p):
            paths.append(p)
        else:
            print(f"  [VIDEO] MISSING: {name}")

    if not paths:
        return

    # Build the sequence mpv but DON'T stop HAL until the new player is
    # actually up, so a video always owns the screen (no desktop flash).
    print(f"  [VIDEO] Playing sequence: {', '.join(filenames)}")
    seq = subprocess.Popen(_MPV_BASE + paths, env=_ENV)

    # Give the sequence window a moment to map on screen, then drop HAL.
    import time
    time.sleep(0.6)
    stop_standby()

    # Wait for the sequence to finish.
    seq.wait()
    print("  [VIDEO] Sequence complete.")

    # Relaunch HAL immediately so the desktop never shows through.
    start_standby()

