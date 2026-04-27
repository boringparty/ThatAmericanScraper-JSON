#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import random
import json
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
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
# DATE PARSER (FIXED)
# -------------------------
def parse_date(text):
    if not text:
        return None

    # RFC822 (standard RSS)
    try:
        dt = parsedate_to_datetime(text)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    except:
        pass

    # ISO 8601 fallback
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
# EPISODE EXTRACTION
# -------------------------
def extract_episode_number(item):
    title_elem = item.find("title")
    if title_elem is not None and title_elem.text:
        title = title_elem.text.strip()
        if ':' in title:
            maybe = title.split(':')[0].strip().replace('#', '')
            if maybe.isdigit():
                return maybe

    link_elem = item.find("link")
    if link_elem is not None and link_elem.text:
        parts = link_elem.text.split('/')
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
        if not pub or not pub.text:
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

    # fallback reset
    if not candidates:
        print("Resetting used list...")
        used = []

        for item in items:
            pub = item.find("pubDate")
            if not pub or not pub.text:
                continue

            dt = parse_date(pub.text)
            if dt is None:
                continue

            if not is_old(dt):
                continue

            ep = extract_episode_number(item)
            candidates.append((item, ep))

    if not candidates:
        raise Exception("No valid episodes found (check pubDate format)")

    chosen_item, episode_num = random.choice(candidates)

    if episode_num:
        used.append(episode_num)
        save_used(used)
        print(f"Selected episode: {episode_num}")

    # -------------------------
    # SAFE GUID EXTRACTION
    # -------------------------
    guid_elem = chosen_item.find("guid")
    guid_text = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None

    if not guid_text:
        raise Exception("Missing GUID")

    item_start = content.find(guid_text)
    if item_start == -1:
        raise Exception("Could not locate item in raw XML")

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
    # GUID UPDATE
    # -------------------------
    original_guid = guid_text
    new_guid = f"{original_guid}-oldies"

    original_item_xml = re.sub(
        r'<guid(?:\s+isPermaLink="[^"]*")?>(.*?)</guid>',
        f'<guid isPermaLink="false">{new_guid}</guid>',
        original_item_xml
    )

    # -------------------------
    # REDDIT LINKS (MARKDOWN)
    # -------------------------
    enclosure = chosen_item.find("enclosure")

    download = None
    episode = None

    if enclosure is not None:
        url = enclosure.attrib.get("url")
        if url:
            download = f"* [download link]({url})"

    link = chosen_item.find("link")
    if link is not None and link.text:
        episode = f"* [episode link]({link.text.strip()})"

    if download or episode:
        block = "\n".join([x for x in [download, episode] if x])

        if re.search(r"(<description>)(.*?)(</description>)", original_item_xml, re.DOTALL):
            original_item_xml = re.sub(
                r"(<description>)(.*?)(</description>)",
                rf"\1\n{block}\n\n\2\3",
                original_item_xml,
                flags=re.DOTALL
            )
        else:
            original_item_xml = re.sub(
                r"</item>",
                f"<description>\n{block}\n</description>\n</item>",
                original_item_xml
            )

    # -------------------------
    # OUTPUT
    # -------------------------
    output = f"""<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>Oldies TAL Feed</title>
  <link>https://www.thisamericanlife.org</link>
  <description>Random episode 10+ years old, updated weekly</description>
  {original_item_xml}
</channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
