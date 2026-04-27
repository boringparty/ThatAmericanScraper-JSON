import feedparser
import random
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os

INPUT_FILE = "feed/feed.xml"
OUTPUT_FILE = "feed/oldies.xml"

TEN_YEARS = timedelta(days=365 * 10)


def is_old(pub_date):
    try:
        dt = parsedate_to_datetime(pub_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return datetime.now(timezone.utc) - dt >= TEN_YEARS
    except Exception:
        return False


def clean_title(title):
    title = title.replace(" - Repeat", "")
    return "[Oldies] " + title


def main():
    feed = feedparser.parse(INPUT_FILE)

    candidates = []

    for entry in feed.entries:
        pub = entry.get("published") or entry.get("pubDate")
        if not pub:
            continue

        if not is_old(pub):
            continue

        candidates.append(entry)

    if not candidates:
        raise Exception("No eligible episodes found")

    chosen = random.choice(candidates)

    title = clean_title(chosen.title)

    item = f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Oldies TAL Feed</title>
    <link>https://www.thisamericanlife.org</link>
    <description>Random 10+ year old episode</description>

    <item>
      <title><![CDATA[{title}]]></title>
      <link>{chosen.link}</link>
      <description><![CDATA[{chosen.get("summary", "")}]]></description>
      <pubDate>{pub}</pubDate>
    </item>

  </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(item)


if __name__ == "__main__":
    main()
