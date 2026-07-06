#!/usr/bin/env python3

import json
from urllib.parse import urlsplit

INPUT_FILE = "data/data.json"


def clean_audio_url(url):
    if not url:
        return url

    url = str(url).strip()

    # Remove query string and fragment
    parts = urlsplit(url)
    url = f"{parts.scheme}://{parts.netloc}{parts.path}"

    # Remove common redirect wrappers
    wrappers = (
        "/s/",           # prefix.up.audio/s/
        "/redirect.mp/", # dts.podtrac.com/redirect.mp/
        "/e/",           # pdst.fm/e/
    )

    changed = True
    while changed:
        changed = False
        for wrapper in wrappers:
            if wrapper in url:
                url = url.split(wrapper, 1)[1]
                if not url.startswith("http"):
                    url = "https://" + url
                changed = True
                break

    # Remove any duplicated scheme
    url = url.replace("https://https://", "https://")
    url = url.replace("http://http://", "http://")

    return url


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    changed = 0

    for episode in episodes:
        for key in ("download", "download_clean"):
            if not episode.get(key):
                continue

            old = episode[key]
            new = clean_audio_url(old)

            if old != new:
                print(f"{key}:")
                print(f"  OLD: {old}")
                print(f"  NEW: {new}\n")
                episode[key] = new
                changed += 1

    if changed:
        with open(INPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(
                episodes,
                f,
                indent=2,
                ensure_ascii=False,
            )

    print(f"Updated {changed} URLs")


if __name__ == "__main__":
    main()
