"""
Analysis module for the AIDAN + MAYA intelligence agent.

Two modes:
  daily   - short digest of the last ~24h of items, scored, in plain
            Russian, with a clear "what to do" block; plus a machine-
            readable TREND_SIGNALS block parsed into trend_memory.json.
  weekly  - strategic synthesis over accumulated trend_memory.json.

Cost notes:
  - MODEL defaults to a small, cheap model.
  - The long system prompt is sent with prompt caching.
  - Only titles + summaries are sent, never full articles.
"""

import os
import json
import re

MODEL = "claude-haiku-4-5-20251001"   # cheap default; swap for deeper runs
MAX_TOKENS = 4500

TREND_START = "<<<TREND_SIGNALS>>>"
TREND_END = "<<<END_TREND_SIGNALS>>>"


# ----------------------------------------------------------------------
# PROJECT CONTEXT - the real state of both startups. This is what makes
# "why it matters for us" specific instead of generic. Edit this block
# as the projects evolve.
# ----------------------------------------------------------------------

_CONTEXT = """REAL PROJECT CONTEXT (use this to judge relevance precisely - \
do NOT give generic "this could be useful for BIM" takes; tie every \
judgement to where these projects actually are today):

AIDAN - OpenBIM + AI platform, pre-production / active development.
- Team ~12, limited budget. Cost-efficiency, speed, lean infra, and real
  measurable savings matter more than cutting-edge ambition.
- Infra: AWS, cloud-deployed.
- Already built: web 3D IFC viewer; BIM analytics (metadata/model analysis);
  a hybrid Graph-RAG + vector-RAG AI assistant ("AIDAN") using external APIs,
  currently Google Gemini, IFC-aware; early material takeoff; early code/norm
  compliance checking; IFC parsing.
- Roadmap (NOT built yet): clash detection, AI-native BIM automation, an AI
  orchestration layer, digital twins, scan-to-BIM, generative/concept design,
  full project-lifecycle workflows.
- Second connected product: AIDAN Revit AI - AI inside Revit via pyRevit +
  MCP architecture (automation, QA/QC, documentation, parameter management).
  A US competitor already MONETIZES similar AI-Revit workflows, so timing and
  competitive moves here are strategically urgent. First validated internally
  at Dan Partners, then commercialized to architecture firms / developers /
  BIM departments.
- Region of interest: Kazakhstan & Central Asia BIM ecosystem, buildingSMART
  Kazakhstan, gov BIM/digitalization; and China (DeepSeek, Qwen, open-source
  AI acceleration) for cheap capable models.

What is HIGH-VALUE for AIDAN: cheaper/faster capable models (esp. open or
self-hostable), anything that directly accelerates the unbuilt roadmap (clash
detection, orchestration, automation), MCP / pyRevit / Revit-API advances,
moves by the US Revit-AI competitor, IFC/OpenBIM standard shifts, practical
agent infra that cuts engineering cost. LOW-VALUE: generic AI hype, heavy
infra they can't afford, research with no near-term implementation path.

MAYA - mindful-AI companion, early stage. Currently a Telegram AI companion
for mindfulness support; founder is an experienced MBSR teacher/researcher.
Long-term: a mindful AI companion + "mindful OS" + AI-assisted mindfulness
teacher training. Russian-speaking users matter.

What is HIGH-VALUE for MAYA: AI companion / memory / voice / emotional-
adaptation advances, evidence-grounding for wellbeing claims, user-safety and
ethics findings (this is mental-health-adjacent, so safety is not optional),
personalization, retention. Treat anything that could harm vulnerable users
as a safety obligation, not a feature."""


# ----------------------------------------------------------------------
# system prompts
# ----------------------------------------------------------------------

_COMMON = """You are the strategic intelligence analyst for two startup \
ecosystems, AIDAN and MAYA. Write in RUSSIAN. Be concrete and practical.

""" + _CONTEXT + """

PRINCIPLES
- Objective and evidence-based. Helping them move faster than the market is \
the goal, but honesty wins over hype: "это шум, ждать" is a valid output.
- Dismiss aggressively: vendor marketing and substanceless hype are NOISE.
- Trust tiers: tier 1 = primary/official, tier 2 = quality secondary. Weight \
tier-1 more; treat striking tier-2 claims with caution.
- Keep AIDAN and MAYA separate unless there is a genuine link.
- Never invent developments not in the provided material.
- Explain in PLAIN language. Imagine the reader is a smart founder, not an \
academic. No jargon dumps. If a paper is abstract, say what it actually \
means in practice."""

DAILY_PROMPT = _COMMON + """

You are a DAILY analyst. You get a batch of items from the last ~24h. No \
memory of previous days.

SCORING (internal): score each reportable item 1-10 averaging relevance, \
implementation potential, timing, revenue potential, strategic importance, \
source reliability (for MAYA also user-safety). Print only the final score.
Priority: >=9.0 КРИТИЧНО, >=7.5 ВЫСОКИЙ, >=5.5 СРЕДНИЙ, >=3.0 НИЗКИЙ, \
below 3.0 = ШУМ (drop entirely, do not list).

Report the 4-8 most important items per stream. Fewer is fine. If nothing \
matters, say so and keep it short.

OUTPUT - plain text in RUSSIAN, Telegram-friendly, NO markdown tables, NO \
bold stars. Use this exact structure:

AIDAN + MAYA — Стратегический дайджест
Дата: <YYYY-MM-DD>

═══ AIDAN ═══

<for each item:>
N. <короткий заголовок на русском> [<ПРИОРИТЕТ>]
Оценка: <X.X>/10
О чём это (просто): <2-3 простых предложения. Объясни суть новости \
по-человечески, без терминов. Что именно сделали/выяснили и что это значит.>
Чем полезно для AIDAN: <1-2 предложения, привязанные к реальному состоянию \
проекта - что протестировать/исследовать/применить, какую конкретную задачу \
это закрывает (clash detection? удешевление модели? Revit AI? конкурент?).>
Что делать: <одна строка: ТЕСТ / ИЗУЧИТЬ / СЛЕДИТЬ / ВНЕДРИТЬ / ИГНОР + \
срок, напр. "ТЕСТ за 3 недели">
→ <URL>

<if none: "Значимых новостей для AIDAN в этой порции нет.">

═══ MAYA ═══

<same structure; for MAYA always consider ethics / user-safety>

<if none: "Значимых новостей для MAYA в этой порции нет.">

═══ ЧТО ДЕЛАТЬ НА ЭТОЙ НЕДЕЛЕ ═══

AIDAN:
1. <конкретная задача + срок>  (только реально важное; 1-3 пункта)
MAYA:
1. <конкретная задача + срок>

<if there is genuinely nothing to act on: "Срочных действий нет. \
Продолжаем наблюдение.">

After the human digest, output the machine-readable block EXACTLY, wrapped \
in the markers, ONLY valid JSON, 3-8 recurring topics worth tracking, short \
canonical topic names. No commentary inside.

""" + TREND_START + """
[
  {"topic": "MCP", "stream": "aidan", "priority": "ВЫСОКИЙ", "note": "short note"},
  {"topic": "AI companions", "stream": "maya", "priority": "СРЕДНИЙ", "note": "short note"}
]
""" + TREND_END + """

If no trend-worthy topics, output [] inside the markers. Always include them."""

WEEKLY_PROMPT = _COMMON + """

You are a WEEKLY analyst. You do NOT get fresh news - you get accumulated \
TREND MEMORY (topics over recent weeks, with count_30d, last_seen, priority \
history). Synthesize: what is strengthening, what is fading, what it means.

A topic with rising count and rising priorities is a strengthening wave. A \
topic seen once is a weak signal, not a trend. If memory is nearly empty, \
say so honestly.

OUTPUT - plain text in RUSSIAN, Telegram-friendly, no tables:

AIDAN + MAYA — Недельный стратегический обзор
Неделя: <YYYY-MM-DD> — <YYYY-MM-DD>

1. Самые сильные тренды недели
<topics with most momentum + the evidence from counts, in plain language>

2. AIDAN — что это значит
<tie to the real roadmap: clash detection, Revit AI, the US competitor, \
cheap models, MCP. Concrete.>

3. MAYA — что это значит
<companion/voice/memory/safety angle, concrete>

4. Слабые сигналы (следить)
5. Хайп / что игнорировать

6. ═══ ФОКУС НА СЛЕДУЮЩУЮ НЕДЕЛЮ ═══
AIDAN:
1. <конкретный фокус + почему>
2.
3.
MAYA:
1.
2.
3.

Tight and decision-oriented."""


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _format_items(items: list[dict]) -> str:
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(
            f"[{i}] ({it['stream']}, tier{it['tier']}) {it['title']}\n"
            f"    source: {it['source']} | {it['published']}\n"
            f"    url: {it['url']}\n"
            f"    summary: {it['summary'] or '(no summary)'}"
        )
    return "\n\n".join(lines)


def _format_trend_memory(memory: dict) -> str:
    if not memory:
        return "(trend memory is empty - no accumulated history yet)"
    lines = []
    for topic, e in sorted(
        memory.items(), key=lambda kv: kv[1].get("count_30d", 0), reverse=True
    ):
        ph = ",".join(e.get("priority_history", [])) or "-"
        notes = " | ".join(e.get("notes", [])[-3:])
        lines.append(
            f"- {topic} [{e.get('stream','?')}] "
            f"count_30d={e.get('count_30d',0)} "
            f"last_seen={e.get('last_seen','?')} "
            f"priorities={ph}"
            + (f" notes: {notes}" if notes else "")
        )
    return "\n".join(lines)


def split_trend_block(text: str) -> tuple[str, list[dict]]:
    """Split daily output into (human_digest, trend_signals_list)."""
    start = text.find(TREND_START)
    end = text.find(TREND_END)
    if start == -1 or end == -1 or end < start:
        return text.strip(), []

    human = text[:start].strip()
    raw = text[start + len(TREND_START):end].strip()

    signals: list[dict] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            for s in parsed:
                if isinstance(s, dict) and s.get("topic"):
                    signals.append(s)
    except json.JSONDecodeError:
        print("WARN: TREND_SIGNALS block was not valid JSON; skipping it.")

    return human, signals


# ----------------------------------------------------------------------
# main entry points
# ----------------------------------------------------------------------

def _call(system_prompt: str, user_msg: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def analyze_daily(items: list[dict]) -> tuple[str, list[dict]]:
    """Daily mode. Returns (human_digest, trend_signals)."""
    if not items:
        digest = ("AIDAN + MAYA — Стратегический дайджест\n\n"
                  "═══ AIDAN ═══\nЗначимых новостей для AIDAN в этой "
                  "порции нет.\n\n"
                  "═══ MAYA ═══\nЗначимых новостей для MAYA в этой "
                  "порции нет.\n\n"
                  "═══ ЧТО ДЕЛАТЬ НА ЭТОЙ НЕДЕЛЕ ═══\nСрочных действий "
                  "нет. Продолжаем наблюдение.")
        return digest, []

    user_msg = (
        f"Вот сегодняшняя порция из {len(items)} новостей. Сделай дневной "
        f"дайджест строго в заданном формате, включая машинный trend-блок.\n\n"
        f"{_format_items(items)}"
    )
    raw = _call(DAILY_PROMPT, user_msg)
    return split_trend_block(raw)


def analyze_weekly(memory: dict) -> str:
    """Weekly mode. Returns the strategic synthesis text."""
    user_msg = (
        "Вот накопленная trend memory. Сделай недельный стратегический "
        "обзор строго в заданном формате.\n\n"
        + _format_trend_memory(memory)
    )
    return _call(WEEKLY_PROMPT, user_msg)
