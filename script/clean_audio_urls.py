#!/usr/bin/env python3

import json

INPUT_FILE = "data/data.json"


def clean_audio_url(url):
    if not url:
        return url

    url = str(url).strip()

    # Remove tracking parameters
    url = url.split("?")[0]

    # Unwrap Podtrac/Vpixl redirect
    if "/s/" in url:
        url = url.split("/s/", 1)[1]

    # Ensure scheme
    if not url.startswith("http"):
        url = "https://" + url

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
                episode[key] = new
                changed += 1

    if changed:
        with open(INPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(
                episodes,
                f,
                indent=2,
                ensure_ascii=False
            )

    print(f"Updated {changed} URLs")


if __name__ == "__main__":
    main()
