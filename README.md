# AIDAN + MAYA Strategic Intelligence System

An unattended agent that once a day collects developments from trusted
sources, has Claude turn them into a strategic digest for two ecosystems
(AIDAN and MAYA), and posts it to Telegram.

Runs free on GitHub Actions. No server, no database - the repo itself
stores dedupe state.

## What it is - and is not

It is a **daily batch job**, not a live monitor. Each run is independent.
On a slow news day the digest is short - that is correct behaviour.
CRITICAL items are surfaced at the top of the daily digest; there is no
separate real-time alerting in the MVP (that needs a different, costlier
architecture and rarely matters for BIM / mindfulness timelines).

## Files

| File              | Role                                          |
|-------------------|-----------------------------------------------|
| `config.py`       | Feed list with trust tiers, tuning constants  |
| `sources.py`      | Fetch + filter feeds                          |
| `state.py`        | Dedupe store (`seen.json`)                    |
| `analyze.py`      | Claude call + batch-mode system prompt        |
| `deliver.py`      | Post to Telegram (splits long messages)       |
| `main.py`         | Orchestrator                                  |
| `.github/workflows/daily.yml` | Daily cron + state commit-back    |

## Setup

1. **Telegram bot** - `@BotFather` -> `/newbot` -> copy the bot token.
2. **Chat id** - create a channel/group, add the bot as admin, post a
   message, open `https://api.telegram.org/bot<TOKEN>/getUpdates`, read
   `chat.id` (channels look like `-100xxxxxxxxxx`).
3. **Anthropic key** - from console.anthropic.com. API billing is separate
   from any Claude.ai subscription.
4. **GitHub repo** - push all files, keeping `.github/workflows/daily.yml`.
5. **Secrets** - repo Settings -> Secrets and variables -> Actions:
   `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
6. **First run** - Actions tab -> `daily-intelligence-digest` ->
   Run workflow. Check logs and Telegram.

## Cost

- `analyze.py` defaults to a small, cheap model (`MODEL`). One model does
  both filtering and analysis - at 10-45 items/day a two-tier pipeline
  adds complexity without real savings.
- The long system prompt uses prompt caching, cutting the per-run cost of
  that block on repeated daily runs.
- `MAX_ITEMS_PER_RUN` in `config.py` caps tokens per run.
- For deeper analysis (e.g. a weekly run), switch `MODEL` to a stronger
  model - one line.

## Tuning

- **Feeds** - `FEEDS` in `config.py`: `(name, url, stream, tier)`.
  stream = `aidan` / `maya` / `both`; tier 1 = primary, tier 2 = secondary.
- **Schedule** - `cron` line in `daily.yml`.
- **Analyst behaviour** - `SYSTEM_PROMPT` in `analyze.py`. Highest-leverage
  thing to tune. If digests get padded or hype-y, fix it here, not in code.

## Known limitations

- **No regional sources.** Kazakhstan / China / CIS / Central Asia sources
  (Astana Hub, buildingSMART Kazakhstan, local programs) have no reliable
  feeds. They are deliberately out of the MVP - automating them needs
  brittle scrapers. Track them manually; add targeted scrapers in v2.
- **Feeds only, no full articles.** The agent sees titles + summaries. It
  is a triage layer - follow source links for depth.
- **Delivery failure retries the batch.** If Telegram fails, state is not
  updated, so the next run re-processes the same items (one possible
  duplicate digest after an outage, but no lost reports).

## Roadmap

- **MVP (this repo):** ~15 trusted feeds, daily Telegram digest, AIDAN/MAYA
  split, priority tiering, CRITICAL surfaced in the digest.
- **v2:** targeted regional scrapers (one source at a time); optional
  OpenRouter multi-model routing once source volume is large enough to
  justify it; optional separate weekly deep-analysis run on a stronger
  model.
- **Later:** searchable archive (Notion), trend tracking across weeks.
