"""
Source configuration for the AIDAN + MAYA intelligence agent.

Only sources with REAL machine-readable feeds (RSS/Atom) are listed.
Each source carries a trust tier so the analyst can weight signals:

  tier 1  - primary / official (company blogs, standards bodies, journals)
  tier 2  - high-quality secondary (specialist trade press, curated research)

Regional sources (Astana Hub, local BIM forums) have no clean feeds and
are intentionally NOT here. See REGIONAL_NOTE below.

Each feed: (name, url, stream, tier)
  stream: "aidan" | "maya" | "both"
"""

# ---- run tuning ----
LOOKBACK_HOURS = 26          # daily cron + small overlap buffer
MAX_ITEMS_PER_RUN = 45       # hard cap on items sent to the model (cost control)

# ---- feeds ----
FEEDS = [
    # ===== AI: primary / official (both streams) =====
    # Anthropic removed their RSS feed (returns 404). Check manually: anthropic.com/news
    ("OpenAI News",            "https://openai.com/news/rss.xml",                    "both",  1),
    ("Google DeepMind Blog",   "https://deepmind.google/blog/rss.xml",               "both",  1),
    ("Hugging Face Blog",      "https://huggingface.co/blog/feed.xml",               "both",  1),
    ("NVIDIA Tech Blog",       "https://developer.nvidia.com/blog/feed",             "both",  1),

    # ===== AI: research =====
    ("arXiv cs.AI",            "http://export.arxiv.org/rss/cs.AI",                  "both",  1),
    ("arXiv cs.SE",            "http://export.arxiv.org/rss/cs.SE",                  "aidan", 1),
    ("arXiv cs.HC",            "http://export.arxiv.org/rss/cs.HC",                  "maya",  1),

    # ===== AI: high-quality secondary =====
    ("MIT Tech Review AI",     "https://www.technologyreview.com/feed/",             "both",  2),
    ("Stanford HAI News",      "https://hai.stanford.edu/news/rss.xml",              "both",  2),

    # ===== AIDAN: BIM / AEC =====
    ("buildingSMART News",     "https://www.buildingsmart.org/feed/",                "aidan", 1),
    ("Autodesk APS Blog",      "https://aps.autodesk.com/blog/feed",                 "aidan", 1),
    ("AEC Magazine",           "https://aecmag.com/feed/",                           "aidan", 2),

    # ===== MAYA: psychology / wellbeing / cognitive science =====
    ("APA Press Releases",     "https://www.apa.org/news/press/releases/rss.xml",    "maya",  1),
    ("Greater Good (Berkeley)","https://greatergood.berkeley.edu/site/rss/articles", "maya",  2),
]

# REGIONAL_NOTE:
# Kazakhstan / China / CIS / Central Asia sources (Astana Hub, buildingSMART
# Kazakhstan, local construction-digitalization programs) have no reliable
# machine-readable feeds. Automating them means brittle scrapers that break
# on every site redesign. They are deliberately out of the MVP. Track them
# manually (a weekly review) until v2, when targeted scrapers can be added
# here one at a time, only for sources that prove worth the maintenance.
REGIONAL_SCRAPERS = []
