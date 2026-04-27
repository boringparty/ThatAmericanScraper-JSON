#!/usr/bin/env python3
import feedparser
import random
import json
import os
from datetime import datetime, timezone, timedelta

INPUT_FEED = "feed/feed.xml"
OUTPUT_FILE = "feed/oldies.xml"
STATE_FILE = "feed/oldies_used.json"

TEN_YEARS = timedelta(days=365 * 10)


# -------------------------
# DATE HELPERS
# -------------------------
def parse_date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None


def is_old(pub_date):
    if not pub_date:
        return False
    return datetime.now(timezone.utc) - pub_date >= TEN_YEARS


# -------------------------
# STATE HANDLING
# -------------------------
def load_used():
    if not os.path.exists(STATE_FILE):
        return set()

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_used(used):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(used), f, indent=2)


# -------------------------
# TITLE CLEANUP
# -------------------------
def clean_title(title: str):
    title = title.replace(" - Repeat", "")
    return f"[Oldies] {title}" if "[Oldies]" not in title else title


# -------------------------
# RSS ITEM BUILDER
# -------------------------
def build_item(entry):
    title = clean_title(entry.title)
    link = entry.link
    guid = getattr(entry, "id", link)
    pub_date = entry.published if hasattr(entry, "published") else ""

    return f"""    <item>
      <title><![CDATA[{title}]]></title>
      <link>{link}</link>
      <guid>{guid}</guid>
      <description><![CDATA[{getattr(entry, "summary", "")}]]></description>
      <pubDate>{pub_date}</pubDate>
    </item>"""


# -------------------------
# MAIN
# -------------------------
def main():
    feed = feedparser.parse(INPUT_FEED)

    used = load_used()

    # build candidate pool
    candidates = []

    for entry in feed.entries:
        pub_date = parse_date(entry)
        if not is_old(pub_date):
            continue

        uid = entry.link  # stable identifier
        if uid in used:
            continue

        candidates.append(entry)

    # reset if exhausted
    if not candidates:
        used = set()
        candidates = [
            e for e in feed.entries
            if is_old(parse_date(e))
        ]

    if not candidates:
        raise Exception("No valid old episodes found")

    chosen = random.choice(candidates)

    # update state
    used.add(chosen.link)
    save_used(used)

    # write RSS
    item_xml = build_item(chosen)

    rss = f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Oldies TAL Feed</title>
    <link>https://www.thisamericanlife.org</link>
    <description>Random episode 10+ years old</description>

{item_xml}

  </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss)


if __name__ == "__main__":
    main()
