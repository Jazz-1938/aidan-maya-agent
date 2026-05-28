"""
Orchestrator for the AIDAN + MAYA daily intelligence agent.

Flow:
  1. Load dedupe state.
  2. Fetch recent, unseen items from all feeds.
  3. Send them to Claude for the strategic digest.
  4. Post the digest to Telegram.
  5. Mark items seen and save state (committed back to the repo by CI).

Designed to run once a day via GitHub Actions cron. A failure in delivery
should NOT mark items as seen, so the next run can retry them.
"""

import sys
import traceback

import config
import state
import sources
import analyze
import deliver


def main() -> int:
    seen = state.load_state()
    print(f"INFO: loaded {len(seen)} seen entries.")

    try:
        items = sources.fetch_all(seen)
    except Exception:  # noqa: BLE001
        print("FATAL: fetching failed:")
        traceback.print_exc()
        return 1

    print(f"INFO: {len(items)} new items to analyze.")

    try:
        digest = analyze.analyze(items)
    except Exception:  # noqa: BLE001
        print("FATAL: analysis failed:")
        traceback.print_exc()
        return 1

    try:
        deliver.send(digest)
    except Exception:  # noqa: BLE001
        # Do NOT mark items seen - we want the next run to retry them.
        print("FATAL: delivery failed; not updating state so items retry.")
        traceback.print_exc()
        return 1

    # Only now, after successful delivery, record items as seen.
    for it in items:
        state.mark_seen(it["url"], seen)
    state.save_state(seen)
    print(f"INFO: run complete. State now has {len(state.prune(seen))} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
