#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — notifier.py
# Sends push notifications to your phone via Pushover.
#
# SETUP (one time):
#   1. Install Pushover app on your phone (free)
#      iOS: https://apps.apple.com/app/pushover/id506088175
#      Android: https://play.google.com/store/apps/details?id=net.superblock.pushover
#   2. Create a free account at https://pushover.net
#   3. Create a new Application at https://pushover.net/apps/build
#      Name it "Baseline Scanner"
#   4. Copy your User Key and App API Token into pushover_config.json
#
# pushover_config.json format:
#   {
#       "user_key": "your_user_key_here",
#       "api_token": "your_app_token_here",
#       "enabled": true
#   }
# ================================================================

import requests
import os
import json

CONFIG_FILE = "pushover_config.json"

def _load_config():
    if not os.path.exists(CONFIG_FILE):
        print("  [NOTIFY] pushover_config.json not found — notifications disabled.")
        print("  [NOTIFY] See notifier.py for setup instructions.")
        return None
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    if not cfg.get("enabled", False):
        return None
    return cfg

def send_notification(title: str, message: str, photo_path: str = None):
    """
    Sends a push notification to your phone.
    Attaches the entry photo if provided.
    """
    cfg = _load_config()
    if not cfg:
        print(f"  [NOTIFY] (disabled) {message}")
        return

    data = {
        "token":   cfg["api_token"],
        "user":    cfg["user_key"],
        "title":   title,
        "message": message,
        "sound":   "alien",   # sci-fi appropriate sound
        "priority": 0
    }

    files = {}
    if photo_path and os.path.exists(photo_path):
        files["attachment"] = (
            os.path.basename(photo_path),
            open(photo_path, "rb"),
            "image/jpeg"
        )

    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data=data,
            files=files if files else None,
            timeout=10
        )
        if response.status_code == 200:
            print(f"  [NOTIFY] Alert sent to phone.")
        else:
            print(f"  [NOTIFY] Alert failed: {response.text}")
    except Exception as e:
        print(f"  [NOTIFY] Error: {e}")
    finally:
        if files and "attachment" in files:
            files["attachment"][1].close()

