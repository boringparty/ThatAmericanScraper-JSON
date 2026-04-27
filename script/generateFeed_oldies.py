#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import random
import json
import re
from datetime import datetime, timezone, timedelta
import os

INPUT_FILE = "feed/feed.xml"
OUTPUT_FILE = "feed/oldies.xml"
USED_FILE = "data/used_oldies.json"
TEN_YEARS = timedelta(days=365 * 10)

# -------------------------
# XML CLEANUP
# -------------------------
def fix_xml(content):
    return re.sub(
        r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)',
        '&amp;',
        content
    )

# -------------------------
# DATE PARSER
# -------------------------
def parse_date(text):
    if not text:
        return None

    text = text.strip()

    # RFC822 / RSS
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ]:
        try:
            return datetime.strptime(text, fmt).astimezone(timezone.utc)
        except:
            pass

    # ISO fallback
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except:
        pass

    return None

def is_old(dt):
    if not dt:
        return False
    return datetime.now(timezone.utc) - dt >= TEN_YEARS

# -------------------------
# EPISODE ID
# -------------------------
def extract_episode_number(item):
    title = item.find("title")
    if title is not None and title.text:
        t = title.text.strip()
        if ":" in t:
            maybe = t.split(":")[0].strip().replace("#", "")
            if maybe.isdigit():
                return maybe

    link = item.find("link")
    if link is not None and link.text:
        parts = link.text.strip().split("/")
        for p in reversed(parts):
            if p.isdigit():
                return p

    pub = item.find("pubDate")
    if pub is not None and pub.text:
        return pub.text.strip()

    return None

# -------------------------
# USED STORAGE
# -------------------------
def load_used():
    if not os.path.exists(USED_FILE):
        return []
    try:
        with open(USED_FILE, "r") as f:
            return json.load(f).get("used_episodes", [])
    except:
        return []

def save_used(data):
    with open(USED_FILE, "w") as f:
        json.dump({"used_episodes": data}, f, indent=2)

# -------------------------
# TITLE CLEANUP
# -------------------------
def clean_title(title):
    return f"[Oldies] {title.replace(' - Repeat', '')}"

# -------------------------
# MAIN
# -------------------------
def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = fix_xml(f.read())

    root = ET.fromstring(content)
    items = root.findall(".//item")

    used = load_used()
    candidates = []

    # -------------------------
    # BUILD CANDIDATES
    # -------------------------
    for item in items:
        pub = item.find("pubDate")
        if pub is None or not pub.text:
            continue

        dt = parse_date(pub.text)
        if dt is None:
            continue

        if not is_old(dt):
            continue

        ep = extract_episode_number(item)
        if ep and ep in used:
            continue

        candidates.append((item, ep))

    # -------------------------
    # RESET FALLBACK
    # -------------------------
    if not candidates:
        print("Resetting used list...")
        used = []

        for item in items:
            pub = item.find("pubDate")
            if pub is None or not pub.text:
                continue

            dt = parse_date(pub.text)
            if dt is None:
                continue

            if not is_old(dt):
                continue

            ep = extract_episode_number(item)
            candidates.append((item, ep))

    if not candidates:
        raise Exception("No valid episodes found")

    chosen_item, episode_num = random.choice(candidates)

    if episode_num:
        used.append(episode_num)
        save_used(used)
        print(f"Selected episode: {episode_num}")

    # -------------------------
    # EXTRACT ITEM XML
    # -------------------------
    guid_elem = chosen_item.find("guid")
    guid_text = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None

    if not guid_text:
        raise Exception("Missing GUID")

    item_start = content.find(guid_text)
    if item_start == -1:
        raise Exception("Could not locate item in feed")

    item_start = content.rfind("<item", 0, item_start)
    item_end = content.find("</item>", item_start) + len("</item>")

    original_item_xml = content[item_start:item_end]

    # -------------------------
    # TITLE
    # -------------------------
    title_elem = chosen_item.find("title")
    if title_elem is not None and title_elem.text:
        new_title = clean_title(title_elem.text)

        original_item_xml = re.sub(
            r"<title><!\[CDATA\[.*?\]\]></title>",
            f"<title><![CDATA[{new_title}]]></title>",
            original_item_xml
        )

    # -------------------------
    # PUBDATE
    # -------------------------
    new_pubdate = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

    original_item_xml = re.sub(
        r"<pubDate>.*?</pubDate>",
        f"<pubDate>{new_pubdate}</pubDate>",
        original_item_xml
    )

    # -------------------------
    # GUID
    # -------------------------
    new_guid = f"{guid_text}-oldies"

    original_item_xml = re.sub(
        r'<guid(?:\s+isPermaLink="[^"]*")?>(.*?)</guid>',
        f'<guid isPermaLink="false">{new_guid}</guid>',
        original_item_xml
    )

    print(f"GUID: {guid_text} -> {new_guid}")

    # -------------------------
    # ENCLOSURE → REDDIT MARKDOWN (INSIDE ITEM, CORRECT SCOPE)
    # -------------------------
    enclosure = chosen_item.find("enclosure")

    if enclosure is not None:
        url = enclosure.attrib.get("url")

        if url:
            download_line = f"[download]({url})"

            match = re.search(
                r"(<description><!\[CDATA\[)(.*?)(\]\]></description>)",
                original_item_xml,
                re.DOTALL
            )

            if match:
                original_item_xml = original_item_xml.replace(
                    match.group(0),
                    f"{match.group(1)}{match.group(2)}{download_line}{match.group(3)}"
                )
            else:
                original_item_xml = re.sub(
                    r"</description>",
                    f"{download_line}</description>",
                    original_item_xml
                )

            print(f"Added download link: {url}")

    # -------------------------
    # OUTPUT
    # -------------------------
    output_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Oldies TAL Feed</title>
    <link>https://www.thisamericanlife.org</link>
    <description>Random episode 10+ years old, updated weekly</description>
    {original_item_xml}
  </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_xml)

    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
