#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import random
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import os

INPUT_FILE = "feed/feed.xml"
OUTPUT_FILE = "feed/oldies.xml"

TEN_YEARS = timedelta(days=365 * 10)


# -------------------------
# PARSE DATE
# -------------------------
def parse_date(text):
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def is_old(dt):
    if not dt:
        return False
    return datetime.now(timezone.utc) - dt >= TEN_YEARS


# -------------------------
# TITLE CLEANUP
# -------------------------
def clean_title(title):
    title = title.replace(" - Repeat", "")
    return f"[Oldies] {title}"


# -------------------------
# MAIN
# -------------------------
def main():
    tree = ET.parse(INPUT_FILE)
    root = tree.getroot()

    items = root.findall(".//item")

    candidates = []

    for item in items:
        pub = item.find("pubDate")
        title = item.find("title")

        if pub is None or title is None:
            continue

        dt = parse_date(pub.text)
        if not is_old(dt):
            continue

        candidates.append(item)

    if not candidates:
        raise Exception("No 10+ year old episodes found")

    chosen = random.choice(candidates)

    # clone item safely
    item_xml = ET.tostring(chosen, encoding="unicode")

    # fix title
    item_xml = item_xml.replace("<title><![CDATA[", "<title><![CDATA[")

    # safer title patching
    title_elem = chosen.find("title")
    if title_elem is not None and title_elem.text:
        title_elem.text = clean_title(title_elem.text)

    output_xml = f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Oldies TAL Feed</title>
    <link>https://www.thisamericanlife.org</link>
    <description>Random episode 10+ years old</description>

{ET.tostring(chosen, encoding="unicode")}

  </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_xml)


if __name__ == "__main__":
    main()
