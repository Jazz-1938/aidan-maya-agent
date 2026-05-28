"""
Fetch items from configured RSS/Atom feeds, keep only recent + unseen ones.

Returns a list of item dicts:
  {"title", "url", "summary", "source", "stream", "tier", "published"}
"""

import re
import time
import calendar
from datetime import datetime, timezone

import feedparser

import config
import state


def _entry_epoch(entry) -> float | None:
    """Best-effort published time as an epoch. None if unknown."""
    for attr in ("published_parsed", "updated_parsed"):
        tm = getattr(entry, attr, None)
        if tm:
            return calendar.timegm(tm)
    return None


def _strip_html(text: str) -> str:
    """Small HTML tag remover - good enough for feed summaries."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_all(seen_state: dict) -> list[dict]:
    """Fetch every feed, return recent unseen items, newest first."""
    cutoff = time.time() - config.LOOKBACK_HOURS * 3600
    items: list[dict] = []
    failed: list[str] = []

    for name, url, stream, tier in config.FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:  # noqa: BLE001
            print(f"WARN: failed to fetch '{name}': {e}")
            failed.append(name)
            continue

        if parsed.bozo and not parsed.entries:
            print(f"WARN: feed '{name}' returned no usable entries.")
            failed.append(name)
            continue

        for entry in parsed.entries:
            link = getattr(entry, "link", "").strip()
            if not link:
                continue

            epoch = _entry_epoch(entry)
            if epoch is not None and epoch < cutoff:
                continue
            if not state.is_new(link, seen_state):
                continue

            summary = _strip_html(getattr(entry, "summary", "") or "")[:600]

            items.append({
                "title": getattr(entry, "title", "(no title)").strip(),
                "url": link,
                "summary": summary,
                "source": name,
                "stream": stream,
                "tier": tier,
                "published": (
                    datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
                    if epoch else "unknown"
                ),
            })

    if failed:
        print(f"INFO: {len(failed)} feed(s) failed this run: {', '.join(failed)}")

    items.sort(key=lambda i: i["published"], reverse=True)
    if len(items) > config.MAX_ITEMS_PER_RUN:
        print(f"INFO: {len(items)} items, capping to {config.MAX_ITEMS_PER_RUN}.")
        items = items[: config.MAX_ITEMS_PER_RUN]

    return items
