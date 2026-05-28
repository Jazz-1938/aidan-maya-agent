"""
Delivery module. Posts the digest to a Telegram chat via the Bot API.

Telegram caps messages at 4096 characters, so long digests are split on
paragraph boundaries.

Requires two environment variables:
  TELEGRAM_BOT_TOKEN  - from @BotFather
  TELEGRAM_CHAT_ID    - the channel/chat to post to
"""

import os
import time
import urllib.request
import urllib.parse
import urllib.error

TELEGRAM_LIMIT = 4000  # a little under 4096 for safety


def _split(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Split text into <=limit chunks, preferring paragraph breaks."""
    if len(text) <= limit:
        return [text]

    chunks, current = [], ""
    for para in text.split("\n\n"):
        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # A single paragraph longer than the limit: hard-split it.
            while len(para) > limit:
                chunks.append(para[:limit])
                para = para[limit:]
            current = para
    if current:
        chunks.append(current)
    return chunks


def send(text: str) -> None:
    """Post the digest to Telegram. Raises on hard failure."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    chunks = _split(text)
    for idx, chunk in enumerate(chunks, 1):
        prefix = f"({idx}/{len(chunks)})\n\n" if len(chunks) > 1 else ""
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": prefix + chunk,
            "disable_web_page_preview": "true",
        }).encode()

        try:
            with urllib.request.urlopen(api_url, data=payload, timeout=30) as r:
                if r.status != 200:
                    print(f"WARN: Telegram returned status {r.status}")
        except urllib.error.HTTPError as e:
            # Surface the Telegram error body - it explains most failures.
            print(f"ERROR: Telegram HTTPError {e.code}: {e.read().decode()}")
            raise

        # Be gentle with the Bot API rate limit between chunks.
        if idx < len(chunks):
            time.sleep(1)
