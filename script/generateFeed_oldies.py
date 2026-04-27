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
    """Fix common XML issues in RSS feeds"""
    content = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', content)
    return content

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
# EPISODE NUMBER EXTRACTION
# -------------------------
def extract_episode_number(item):
    title_elem = item.find("title")
    if title_elem is not None and title_elem.text:
        title = title_elem.text.strip()
        if ':' in title:
            potential_num = title.split(':')[0].strip().replace('#', '')
            if potential_num.isdigit():
                return potential_num

    link_elem = item.find("link")
    if link_elem is not None and link_elem.text:
        parts = link_elem.text.strip().split('/')
        for part in reversed(parts):
            if part.isdigit():
                return part

    pub_elem = item.find("pubDate")
    if pub_elem is not None and pub_elem.text:
        return pub_elem.text.strip()

    return None

# -------------------------
# USED EPISODES TRACKING
# -------------------------
def load_used_episodes():
    if not os.path.exists(USED_FILE):
        return []
    try:
        with open(USED_FILE, 'r') as f:
            data = json.load(f)
            return data.get('used_episodes', [])
    except Exception as e:
        print(f"Warning: Could not load {USED_FILE}: {e}")
        return []

def save_used_episodes(used_list):
    with open(USED_FILE, 'w') as f:
        json.dump({'used_episodes': used_list}, f, indent=2)

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
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    content = fix_xml(content)

    tree = ET.ElementTree(ET.fromstring(content))
    root = tree.getroot()
    items = root.findall(".//item")

    used_episodes = load_used_episodes()

    candidates = []
    for item in items:
        pub = item.find("pubDate")
        title = item.find("title")
        if pub is None or title is None:
            continue

        dt = parse_date(pub.text)
        if not is_old(dt):
            continue

        episode_num = extract_episode_number(item)
        if episode_num and episode_num in used_episodes:
            continue

        candidates.append((item, episode_num))

    if not candidates:
        print("No unused 10+ year old episodes found. Resetting used list.")
        used_episodes = []
        for item in items:
            pub = item.find("pubDate")
            title = item.find("title")
            if pub is None or title is None:
                continue

            dt = parse_date(pub.text)
            if not is_old(dt):
                continue

            episode_num = extract_episode_number(item)
            candidates.append((item, episode_num))

    if not candidates:
        raise Exception("No 10+ year old episodes found at all")

    chosen_item, episode_num = random.choice(candidates)

    if episode_num:
        used_episodes.append(episode_num)
        save_used_episodes(used_episodes)
        print(f"Selected episode: {episode_num}")

    # --- Extract original XML block ---
    guid_text = chosen_item.find("guid").text
    item_start = content.find(guid_text)
    if item_start == -1:
        raise Exception("Could not find item in original XML")

    item_start = content.rfind('<item', 0, item_start)
    item_end = content.find('</item>', item_start) + len('</item>')

    original_item_xml = content[item_start:item_end]

    # --- Title update ---
    title_elem = chosen_item.find("title")
    if title_elem is not None and title_elem.text:
        original_title = title_elem.text
        new_title = clean_title(original_title)

        original_item_xml = re.sub(
            r'<title><!\[CDATA\[.*?\]\]></title>',
            f'<title><![CDATA[{new_title}]]></title>',
            original_item_xml
        )

        print(f"Title: {original_title} -> {new_title}")

    # --- pubDate update ---
    today = datetime.now(timezone.utc)
    new_pubdate = today.strftime("%a, %d %b %Y %H:%M:%S %z")

    original_item_xml = re.sub(
        r'<pubDate>.*?</pubDate>',
        f'<pubDate>{new_pubdate}</pubDate>',
        original_item_xml
    )

    print(f"Updated pubDate to: {new_pubdate}")

    # --- GUID update ---
    guid_elem = chosen_item.find("guid")
    if guid_elem is not None and guid_elem.text:
        original_guid = guid_elem.text.strip()
        new_guid = f"{original_guid}-oldies"

        original_item_xml = re.sub(
            r'<guid(?:\s+isPermaLink="[^"]*")?>(.*?)</guid>',
            f'<guid isPermaLink="false">{new_guid}</guid>',
            original_item_xml
        )

        print(f"GUID: {original_guid} -> {new_guid}")

    # --- Output ---
    output_xml = f"""<feed xmlns='http://www.w3.org/2005/Atom' xmlns:itunes='http://www.itunes.com/dtds/podcast-1.0.dtd' xml:lang='en-US'>
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
