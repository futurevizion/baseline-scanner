#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — voice.py
# AI text-to-speech voice output.
# Uses Coqui TTS for natural voice, espeak as fallback.
#
# AUDIO ROUTING FIX: espeak does NOT follow the PipeWire default
# sink, so on its own it plays out the wrong device (or silent).
# We make espeak WRITE A WAV, then play that wav through pw-play,
# which DOES use the PipeWire default (the Echo Dot). That routes
# the spoken greeting to the Dot, same path the videos use.
# ================================================================

import subprocess
import os
import tempfile
import shutil

try:
    from TTS.api import TTS as CoquiTTS
    COQUI_AVAILABLE = True
    print("  [VOICE] Coqui TTS ready — AI voice active.")
except ImportError:
    COQUI_AVAILABLE = False
    print("  [VOICE] Coqui TTS not found — using espeak fallback.")

# Model downloads automatically on first run (~100MB, one time only)
if COQUI_AVAILABLE:
    tts_engine = CoquiTTS("tts_models/en/ljspeech/vits")

# Prefer pw-play (PipeWire) so audio follows the default sink (Echo Dot).
# Fall back to paplay, then aplay, if pw-play isn't present.
def _player_cmd(wav_path):
    if shutil.which("pw-play"):
        return ["pw-play", wav_path]
    if shutil.which("paplay"):
        return ["paplay", wav_path]
    return ["aplay", wav_path]


def speak(text: str):
    """Speaks the given text through the PipeWire default sink (Echo Dot)."""
    print(f"  [VOICE] >> {text}")
    if COQUI_AVAILABLE:
        _speak_coqui(text)
    else:
        _speak_espeak(text)


def _speak_coqui(text: str):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    try:
        tts_engine.tts_to_file(text=text, file_path=wav_path)
        subprocess.run(_player_cmd(wav_path), check=True)
    except Exception as e:
        print(f"  [VOICE] Coqui error: {e} — falling back to espeak")
        _speak_espeak(text)
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def _speak_espeak(text: str):
    """
    Fallback robotic voice, routed through PipeWire so it reaches the Dot.
    Pitch 30 = deep and cold, fitting for a scanner.
    espeak writes a WAV (-w), then pw-play sends it to the default sink.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    try:
        subprocess.run([
            "espeak",
            "-v", "en",
            "-p", "30",
            "-s", "135",
            "-w", wav_path,     # write to WAV instead of playing directly
            text
        ], check=True)
        # Play the WAV through PipeWire's default sink (the Echo Dot).
        subprocess.run(_player_cmd(wav_path), check=True)
    except Exception as e:
        print(f"  [VOICE] espeak error: {e}")
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

