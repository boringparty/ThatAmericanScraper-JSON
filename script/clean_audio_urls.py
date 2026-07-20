#!/usr/bin/env python3

import json

from audio_url import clean_audio_url

INPUT_FILE = "data/data.json"


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
