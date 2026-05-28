"""
State for the AIDAN + MAYA intelligence agent.
seen.json - dedupe; trend_memory.json - accumulated topic signals.
"""

import json
import hashlib
import time
import os
from datetime import date, datetime, timedelta

STATE_FILE = "seen.json"
TREND_FILE = "trend_memory.json"

STATE_RETENTION_DAYS = 45
TREND_WINDOW_DAYS = 30
TREND_RETENTION_DAYS = 60
MAX_NOTES_PER_TOPIC = 8
MAX_PRIORITY_HISTORY = 12


def _key(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print("WARN: seen.json unreadable, starting with empty state.")
        return {}


def is_new(url: str, state: dict) -> bool:
    return _key(url) not in state


def mark_seen(url: str, state: dict) -> None:
    state[_key(url)] = int(time.time())


def prune(state: dict) -> dict:
    cutoff = int(time.time()) - STATE_RETENTION_DAYS * 86400
    return {k: v for k, v in state.items() if v >= cutoff}


def save_state(state: dict) -> None:
    state = prune(state)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=0)


def load_trend_memory() -> dict:
    if not os.path.exists(TREND_FILE):
        return {}
    try:
        with open(TREND_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print("WARN: trend_memory.json unreadable, starting empty.")
        return {}


def _recount_window(seen_dates: list) -> int:
    cutoff = date.today() - timedelta(days=TREND_WINDOW_DAYS)
    n = 0
    for d in seen_dates:
        try:
            if datetime.strptime(d, "%Y-%m-%d").date() >= cutoff:
                n += 1
        except ValueError:
            continue
    return n


def update_trend_memory(memory: dict, trend_signals: list) -> dict:
    today = date.today().isoformat()
    for sig in trend_signals:
        topic = (sig.get("topic") or "").strip()
        if not topic:
            continue
        stream = sig.get("stream", "both")
        priority = (sig.get("priority") or "").strip().upper()
        note = (sig.get("note") or "").strip()

        entry = memory.get(topic) or {
            "stream": stream, "last_seen": today, "seen_dates": [],
            "count_30d": 0, "priority_history": [], "notes": [],
        }
        if today not in entry["seen_dates"]:
            entry["seen_dates"].append(today)
        entry["last_seen"] = today
        entry["stream"] = stream or entry.get("stream", "both")
        if priority:
            entry["priority_history"].append(priority)
            entry["priority_history"] = entry["priority_history"][-MAX_PRIORITY_HISTORY:]
        if note and note not in entry["notes"]:
            entry["notes"].append(note)
            entry["notes"] = entry["notes"][-MAX_NOTES_PER_TOPIC:]
        entry["count_30d"] = _recount_window(entry["seen_dates"])
        memory[topic] = entry
    return _prune_trends(memory)


def _within(d: str, days: int) -> bool:
    cutoff = date.today() - timedelta(days=days)
    try:
        return datetime.strptime(d, "%Y-%m-%d").date() >= cutoff
    except ValueError:
        return False


def _prune_trends(memory: dict) -> dict:
    cutoff = date.today() - timedelta(days=TREND_RETENTION_DAYS)
    cleaned = {}
    for topic, entry in memory.items():
        try:
            last = datetime.strptime(entry["last_seen"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if last < cutoff:
            continue
        entry["seen_dates"] = [d for d in entry.get("seen_dates", [])
                               if _within(d, TREND_RETENTION_DAYS)]
        entry["count_30d"] = _recount_window(entry["seen_dates"])
        cleaned[topic] = entry
    return cleaned


def save_trend_memory(memory: dict) -> None:
    with open(TREND_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=1, ensure_ascii=False)
