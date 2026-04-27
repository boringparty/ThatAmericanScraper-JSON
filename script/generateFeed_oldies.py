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
    content = re.sub(
        r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)',
        '&amp;',
        content
    )
    return content

# -------------------------
# DATE HANDLING
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
# EPISODE ID
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
# USED EPISODES
# -------------------------
def load_used_episodes():
    if not os.path.exists(USED_FILE):
        return []
    try:
        with open(USED_FILE, "r") as f:
            return json.load(f).get("used_episodes", [])
    except:
        return []

def save_used_episodes(data):
    with open(USED_FILE, "w") as f:
        json.dump({"used_episodes": data}, f, indent=2)

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
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = fix_xml(f.read())

    tree = ET.ElementTree(ET.fromstring(content))
    root = tree.getroot()
    items = root.findall(".//item")

    used = load_used_episodes()

    candidates = []
    for item in items:
        pub = item.find("pubDate")
        title = item.find("title")
        if not pub or not title:
            continue

        dt = parse_date(pub.text)
        if not is_old(dt):
            continue

        ep = extract_episode_number(item)
        if ep and ep in used:
            continue

        candidates.append((item, ep))

    if not candidates:
        print("Resetting used list...")
        used = []
        for item in items:
            pub = item.find("pubDate")
            title = item.find("title")
            if not pub or not title:
                continue

            dt = parse_date(pub.text)
            if not is_old(dt):
                continue

            ep = extract_episode_number(item)
            candidates.append((item, ep))

    if not candidates:
        raise Exception("No valid episodes found")

    chosen_item, episode_num = random.choice(candidates)

    if episode_num:
        used.append(episode_num)
        save_used_episodes(used)
        print(f"Selected episode: {episode_num}")

    # -------------------------
    # Extract raw item XML
    # -------------------------
    guid_text = chosen_item.find("guid").text
    item_start = content.find(guid_text)
    if item_start == -1:
        raise Exception("Could not locate item")

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
    new_pubdate = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S %z"
    )

    original_item_xml = re.sub(
        r"<pubDate>.*?</pubDate>",
        f"<pubDate>{new_pubdate}</pubDate>",
        original_item_xml
    )

    # -------------------------
    # GUID
    # -------------------------
    guid_elem = chosen_item.find("guid")
    if guid_elem is not None and guid_elem.text:
        original_guid = guid_elem.text.strip()
        new_guid = f"{original_guid}-oldies"

        original_item_xml = re.sub(
            r'<guid(?:\s+isPermaLink="[^"]*")?>(.*?)</guid>',
            f'<guid isPermaLink="false">{new_guid}</guid>',
            original_item_xml
        )

    # -------------------------
    # DESCRIPTION LINKS (Reddit Markdown)
    # -------------------------
    enclosure_elem = chosen_item.find("enclosure")

    download_link = None
    episode_link = None

    if enclosure_elem is not None:
        enclosure_url = enclosure_elem.attrib.get("url")
        if enclosure_url:
            download_link = f"* [download link]({enclosure_url})"

    link_elem = chosen_item.find("link")
    if link_elem is not None and link_elem.text:
        episode_url = link_elem.text.strip()
        episode_link = f"* [episode link]({episode_url})"

    if download_link or episode_link:
        link_block = "\n".join(
            [x for x in [download_link, episode_link] if x]
        )

        if re.search(
            r"(<description>)(.*?)(</description>)",
            original_item_xml,
            re.DOTALL
        ):
            original_item_xml = re.sub(
                r"(<description>)(.*?)(</description>)",
                rf"\1\n{link_block}\n\n\2\3",
                original_item_xml,
                flags=re.DOTALL
            )
        else:
            original_item_xml = re.sub(
                r"</item>",
                f"<description>\n{link_block}\n</description>\n</item>",
                original_item_xml
            )

    # -------------------------
    # OUTPUT
    # -------------------------
    output_xml = f"""<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
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

    print(f"Generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
