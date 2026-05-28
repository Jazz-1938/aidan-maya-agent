"""
Orchestrator for the AIDAN + MAYA daily/weekly intelligence agent.
"""

import sys
import os
import argparse
import traceback

import config
import state
import analyze
import deliver


def run_daily() -> int:
    import sources

    seen = state.load_state()
    trends = state.load_trend_memory()
    print(f"INFO: {len(seen)} seen entries, {len(trends)} tracked topics.")

    try:
        items = sources.fetch_all(seen)
    except Exception:
        print("FATAL: fetching failed:")
        traceback.print_exc()
        return 1
    print(f"INFO: {len(items)} new items to analyze.")

    try:
        digest, trend_signals = analyze.analyze_daily(items)
    except Exception:
        print("FATAL: analysis failed:")
        traceback.print_exc()
        return 1

    try:
        deliver.send(digest)
    except Exception:
        print("FATAL: delivery failed; state untouched so next run retries.")
        traceback.print_exc()
        return 1

    for it in items:
        state.mark_seen(it["url"], seen)
    state.save_state(seen)

    updated = state.update_trend_memory(trends, trend_signals)
    state.save_trend_memory(updated)
    print(f"INFO: daily run complete. {len(trend_signals)} trend signals "
          f"merged; {len(updated)} topics tracked.")
    return 0


def run_weekly() -> int:
    trends = state.load_trend_memory()
    print(f"INFO: weekly run over {len(trends)} tracked topics.")

    try:
        report = analyze.analyze_weekly(trends)
    except Exception:
        print("FATAL: weekly analysis failed:")
        traceback.print_exc()
        return 1

    try:
        deliver.send(report)
    except Exception:
        print("FATAL: weekly delivery failed.")
        traceback.print_exc()
        return 1

    state.save_trend_memory(state.update_trend_memory(trends, []))
    print("INFO: weekly run complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AIDAN+MAYA intelligence agent")
    parser.add_argument(
        "--mode", choices=["daily", "weekly"],
        default=os.environ.get("RUN_MODE", "daily"),
        help="run mode (default: daily, or RUN_MODE env var)",
    )
    args = parser.parse_args()
    print(f"INFO: starting in '{args.mode}' mode.")
    return run_weekly() if args.mode == "weekly" else run_daily()


if __name__ == "__main__":
    sys.exit(main())
