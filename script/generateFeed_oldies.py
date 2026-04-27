#!/usr/bin/env python3
import os
import re

INPUT_FILE = os.path.join("feed", "feed.xml")
OUTPUT_FILE = os.path.join("feed", "feed.xml")  # overwrite same file


# -------------------------
# CONFIG
# -------------------------
OLD_EPISODE_CUTOFF = 10_000  # optional safety default (not used unless you want it)


# -------------------------
# HELPERS
# -------------------------
def get_episode_number(item: str):
    m = re.search(r"<itunes:episode>(\d+)</itunes:episode>", item)
    return int(m.group(1)) if m else None


def update_title(title: str):
    # remove repeat marker
    title = title.replace(" - Repeat", "")

    # avoid double prefixing
    if "[Oldies]" in title:
        return title

    return "[Oldies] " + title


def process_item(item: str):
    ep_num = get_episode_number(item)

    if ep_num is None:
        return item

    # OPTIONAL RULE (customize this)
    # only mark older episodes
    # if ep_num > 600: return item

    # update title only
    item = re.sub(
        r"(<title><!\[CDATA\[)(.*?)(\]\]></title>)",
        lambda m: m.group(1) + update_title(m.group(2)) + m.group(3),
        item,
        flags=re.DOTALL
    )

    return item


# -------------------------
# MAIN
# -------------------------
def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        rss = f.read()

    # split items (no XML parsing)
    parts = re.split(r"(<item>.*?</item>)", rss, flags=re.DOTALL)

    new_parts = []
    for part in parts:
        if part.startswith("<item>"):
            new_parts.append(process_item(part))
        else:
            new_parts.append(part)

    output = "".join(new_parts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)


if __name__ == "__main__":
    main()
