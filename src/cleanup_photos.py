#!/usr/bin/env python3
# ================================================================
# BASELINE SCANNER -- cleanup_photos.py
# Deletes entry photos older than RETENTION_DAYS from
# static/photos/, and prunes matching entries from entry_log.json.
# Run daily by the baseline-cleanup systemd timer (04:00).
# ================================================================
import os
import json
import time

# Resolve paths relative to this file so the project runs from anywhere.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(PROJECT_DIR, "static", "photos")
LOG_FILE = os.path.join(PROJECT_DIR, "entry_log.json")
RETENTION_DAYS = 30
CUTOFF = time.time() - (RETENTION_DAYS * 86400)


def cleanup_photos():
    if not os.path.isdir(PHOTOS_DIR):
        print(f"[CLEANUP] no photos dir at {PHOTOS_DIR}")
        return 0
    removed = 0
    for fn in os.listdir(PHOTOS_DIR):
        path = os.path.join(PHOTOS_DIR, fn)
        if not os.path.isfile(path):
            continue
        if os.path.getmtime(path) < CUTOFF:
            try:
                os.remove(path)
                removed += 1
            except OSError as e:
                print(f"[CLEANUP] could not remove {fn}: {e}")
    return removed


def prune_log():
    """Drop log entries whose photo file no longer exists."""
    if not os.path.exists(LOG_FILE):
        return 0
    try:
        with open(LOG_FILE, "r") as f:
            log = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0
    kept = []
    for entry in log:
        photo = entry.get("photo", "")
        if photo and not os.path.exists(os.path.join(PHOTOS_DIR, photo)):
            continue  # photo was deleted -> drop the entry
        kept.append(entry)
    dropped = len(log) - len(kept)
    if dropped:
        with open(LOG_FILE, "w") as f:
            json.dump(kept, f, indent=2)
    return dropped


if __name__ == "__main__":
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    n_photos = cleanup_photos()
    n_log = prune_log()
    print(f"[CLEANUP {ts}] removed {n_photos} photo(s) older than "
          f"{RETENTION_DAYS} days, pruned {n_log} log entr(ies).")

