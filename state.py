"""
Dedupe state. A JSON file of URL hashes we have already reported on,
so a daily run never re-analyzes yesterday's items.

The file is committed back to the repo by the GitHub Actions workflow,
so the repo itself is the persistence layer. No database needed.

Old entries are pruned after STATE_RETENTION_DAYS to keep the file small.
"""

import json
import hashlib
import time
import os

STATE_FILE = "seen.json"
STATE_RETENTION_DAYS = 45


def _key(url: str) -> str:
    """Stable short hash of a URL, used as the dedupe key."""
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def load_state() -> dict:
    """Return {url_hash: first_seen_epoch}. Empty dict if no file yet."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt state should not crash the run; start fresh.
        print("WARN: seen.json unreadable, starting with empty state.")
        return {}


def is_new(url: str, state: dict) -> bool:
    return _key(url) not in state


def mark_seen(url: str, state: dict) -> None:
    state[_key(url)] = int(time.time())


def prune(state: dict) -> dict:
    """Drop entries older than the retention window."""
    cutoff = int(time.time()) - STATE_RETENTION_DAYS * 86400
    return {k: v for k, v in state.items() if v >= cutoff}


def save_state(state: dict) -> None:
    state = prune(state)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=0)
