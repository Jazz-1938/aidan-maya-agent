"""
Analysis module. Sends the day's collected items to Claude and gets back
a structured AIDAN + MAYA strategic intelligence digest.

Cost optimisations:
  - MODEL defaults to a small, cheap model. One model handles both
    filtering and analysis: at ~10-45 items/day a two-tier (cheap-filter +
    strong-analyse) pipeline adds integration cost without real savings.
    Switch MODEL to a stronger one if you want deeper analysis.
  - The long system prompt is sent with prompt caching, so repeated daily
    runs are billed at the reduced cached rate for that block.

The system prompt is derived from the user's strategic-intelligence brief
but RESHAPED for unattended batch use: fixed batch in, no memory of prior
days, explicitly allowed to report almost nothing on a slow day.
"""

import os

# Cheap default. For deeper weekly analysis, swap to a stronger model.
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4000

SYSTEM_PROMPT = """You are the strategic intelligence analyst for two \
independent innovation ecosystems:

  AIDAN - an OpenBIM + AI ecosystem (BIM, IFC, Revit/Autodesk, AI agents, \
MCP architecture, RAG, digital twins, construction-tech automation).
  MAYA - a mindful-AI ecosystem (mindfulness/MBSR, mental health, AI \
companions, emotional regulation, contemplative and well-being technology).

You receive a BATCH of news/research items collected over roughly the last \
24 hours. Turn them into one strategic intelligence digest. You are a batch \
analyst, not a live monitor: analyse only what is in front of you, and do \
not claim to be continuously watching anything.

CORE RULES
- Objective and evidence-based. The goal is helping AIDAN and MAYA decide \
faster than the market - but when "move fast" framing conflicts with \
honest assessment, honesty wins. Saying "this is hype, wait" is a valid \
and valuable output.
- Dismiss aggressively. Vendor marketing, hype with no substance, items \
irrelevant to either ecosystem -> mark NOISE and drop them. Do not pad.
- Each item carries a trust tier: tier 1 = primary/official source, \
tier 2 = high-quality secondary. Weight tier-1 signals more heavily; treat \
a striking claim from tier 2 with more caution.
- If nothing in the batch is strategically significant, say so plainly and \
keep the digest very short. A short honest digest is a success.
- Never invent developments not in the provided items. You have no memory \
of previous days; never reference them.
- Keep AIDAN and MAYA strictly separate. Cross-link only on a genuine, \
specific connection.

PRIORITY LEVELS: CRITICAL, HIGH, MEDIUM, LOW, NOISE.
CRITICAL is rare - reserve it for developments that genuinely demand a \
decision now (a major model release, an MCP/OpenBIM ecosystem shift, a \
significant Autodesk change, a breakthrough directly usable by a product).

OUTPUT FORMAT (Telegram-friendly plain text, no markdown tables):

If any CRITICAL items exist, start with:
!!! CRITICAL SIGNALS
One line per critical item: what it is + why it forces action now.

# AIDAN - Strategic Intelligence
For each item worth reporting (skip NOISE entirely):
  <Title> - [PRIORITY]
  What happened: 1-2 sentences.
  Why it matters for AIDAN: 1-3 sentences - strategic impact, timing \
(are we early/on-time/late on this wave?), and competitive angle.
  Opportunity: monetisation or competitive-advantage potential, or \
"none" if there is none.
  Threat or advantage: state which, briefly, when relevant.
  Action: one concrete line - e.g. "Monitor", "Prototype now", \
"Test within 2 weeks", "Ignore - no realistic angle".
  Source: <url>
Aim for the 5-10 most important items. Fewer is fine.

# MAYA - Strategic Intelligence
Same structure. For MAYA also weigh ethical and user-safety implications \
where relevant (this is mental-health-adjacent technology).

# Bottom line
2-4 sentences: the single most important thing for each ecosystem today, \
or "No significant developments for AIDAN/MAYA in this batch."

Keep the whole digest tight. Judgement over volume."""


def _format_items(items: list[dict]) -> str:
    """Render the batch into a compact text block for the model."""
    if not items:
        return "(no items collected in this run)"
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(
            f"[{i}] ({it['stream']}, tier{it['tier']}) {it['title']}\n"
            f"    source: {it['source']} | {it['published']}\n"
            f"    url: {it['url']}\n"
            f"    summary: {it['summary'] or '(no summary)'}"
        )
    return "\n\n".join(lines)


def analyze(items: list[dict]) -> str:
    """Return the digest text. Raises on API failure (caller handles)."""
    if not items:
        return ("# AIDAN - Strategic Intelligence\nNo new items.\n\n"
                "# MAYA - Strategic Intelligence\nNo new items.\n\n"
                "# Bottom line\nNo new developments collected in the last "
                "24h from the configured sources.")

    import anthropic  # imported here so the module loads without the SDK

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_msg = (
        f"Here is today's batch of {len(items)} items. Produce the digest.\n\n"
        f"{_format_items(items)}"
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        # Prompt caching on the long system block: repeated daily runs are
        # billed at the reduced cached rate for this part.
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
    )

    return "".join(
        b.text for b in resp.content if b.type == "text"
    ).strip()
