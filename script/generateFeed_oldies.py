#!/usr/bin/env python3
import os
import re
from datetime import datetime, timezone

INPUT_FILE = os.path.join("feed", "feed.xml")
OUTPUT_FILE = os.path.join("feed", "oldies.xml")

# -------------------------
# CONFIG
# -------------------------
YEARS_OLD = 10


# -------------------------
# HELPERS
# -------------------------
def get_episode_number(item: str):
    m = re.search(r"<itunes:episode>(\d+)</itunes:episode>", item)
    return int(m.group(1)) if m else None


def get_pub_year(item: str):
    m = re.search(r"<itunes:season>(\d+)</itunes:season>", item)
    return int(m.group(1)) if m else None


def is_older_than_10_years(item: str):
    year = get_pub_year(item)
    if not year:
        return False
    current_year = datetime.now(timezone.utc).year
    return (current_year - year) >= YEARS_OLD


def update_title(title: str):
    title = title.replace(" - Repeat", "")
    if "[Oldies]" in title:
        return title
    return "[Oldies] " + title


def process_item(item: str):
    return re.sub(
        r"(<title><!\[CDATA\[)(.*?)(\]\]></title>)",
        lambda m: m.group(1) + update_title(m.group(2)) + m.group(3),
        item,
        flags=re.DOTALL
    )


# -------------------------
# MAIN
# -------------------------
def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rss = f.read()

    # extract items
    items = re.findall(r"<item>.*?</item>", rss, flags=re.DOTALL)

    # filter old episodes
    old_items = [i for i in items if is_older_than_10_years(i)]

    if not old_items:
        print("No old episodes found.")
        return

    # pick ONE episode (latest among old ones by episode number)
    def ep_num(x):
        n = get_episode_number(x)
        return n if n is not None else -1

    target = max(old_items, key=ep_num)

    # modify only that one
    target = process_item(target)

    # build minimal RSS
    output = """<?xml version="1.0" ?>
<rss version="2.0">
<channel>
<title>Oldies Feed</title>
<link>https://www.thisamericanlife.org</link>
<description>Single weekly old episode</description>
"""

    output += target

    output += """
</channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)


if __name__ == "__main__":
    main()
