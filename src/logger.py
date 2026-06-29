#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER — logger.py
# Saves every entry event to a JSON log file.
# The web dashboard reads this file to display the entry history.
# ================================================================

import json
import os

LOG_FILE = "entry_log.json"

def log_entry(name: str, status: str, photo: str, timestamp: str):
    """Appends an entry event to the log file."""

    # Load existing log
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                log = json.load(f)
            except json.JSONDecodeError:
                log = []
    else:
        log = []

    # Add new entry at the top (newest first)
    log.insert(0, {
        "name":      name,
        "status":    status,
        "photo":     photo,
        "timestamp": timestamp
    })

    # Keep only the last 200 entries
    log = log[:200]

    # Save back
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

