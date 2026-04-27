#!/usr/bin/env python3
import re
import json
import random
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

INPUT_FILE = "feed/feed.xml"
OUTPUT_FILE = "feed/oldies.xml"
USED_FILE = "used_oldies.json"

NOW = datetime.now(timezone.utc)


# -------------------------
# LOAD USED
# -------------------------
def load_used():
    try:
        with open(USED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_used(used):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)


# -------------------------
# PARSE DATE
# -------------------------
def parse_rss_date(text):
    # Example: "Wed, 17 Nov 2010 00:00:00 +0000"
    return datetime.strptime(text, "%a, %d %b %Y %H:%M:%S %z")


def older_than_10_years(dt):
    return (NOW - dt).days >= 3650


# -------------------------
# CLEAN TITLE
# -------------------------
def clean_title(title):
    title = re.sub(r"\s-\sRepeat$", "", title)
    return "[Oldies] " + title


# -------------------------
# MAIN
# -------------------------
def main():
    used = load_used()

    tree = ET.parse(INPUT_FILE)
    root = tree.getroot()

    items = root.findall(".//item")

    eligible = []

    for item in items:
        title = item.findtext("title", "")
        pub = item.findtext("pubDate", "")
        guid = item.findtext("guid", "")

        try:
            dt = parse_rss_date(pub)
        except Exception:
            continue

        if not older_than_10_years(dt):
            continue

        if guid in used:
            continue

        eligible.append((item, dt, guid))

    if not eligible:
        print("No eligible episodes found.")
        return

    item, dt, guid = random.choice(eligible)

    used.add(guid)
    save_used(used)

    # extract fields
    title = clean_title(item.findtext("title", ""))
    link = item.findtext("link", "")
    pubDate = NOW.strftime("%a, %d %b %Y %H:%M:%S +0000")

    enclosure = item.find("enclosure")
    audio_url = enclosure.attrib["url"] if enclosure is not None else ""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Oldies Feed</title>
    <link>{link}</link>
    <description>Random old This American Life episodes (10+ years old)</description>

    <item>
      <title><![CDATA[{title}]]></title>
      <link>{link}</link>
      <guid>{guid}</guid>
      <pubDate>{pubDate}</pubDate>
      <enclosure url="{audio_url}" type="audio/mpeg"/>
      <description><![CDATA[
        Archived episode from This American Life.
      ]]></description>
    </item>

  </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss)

    print(f"Selected: {title}")


if __name__ == "__main__":
    main()
