#!/usr/bin/env python3
"""Shared audio-URL cleaning logic.

Used by both scrape.py (cleans URLs as episodes are scraped) and
clean_audio_urls.py (retroactively cleans anything already stored in
data.json). Previously these lived as two separate, disagreeing
implementations -- this is the single source of truth going forward.
"""
import re
from urllib.parse import urlsplit

# Known tracking/redirect wrapper path segments to peel off, e.g.
#   https://dts.podtrac.com/redirect.mp3/pdst.fm/e/<real-url>
# Order doesn't matter -- clean_audio_url() loops until none apply.
REDIRECT_WRAPPERS = ("/s/", "/redirect.mp3/", "/e/")

# If a Simplecast URL is embedded anywhere in what's left, canonicalize
# down to it. This also acts as a fallback for wrapper formats not listed
# in REDIRECT_WRAPPERS above.
SIMPLECAST_RE = re.compile(
    r"(https?://)?([a-z0-9.-]+\.simplecastaudio\.com/.*)",
    re.IGNORECASE,
)


def clean_audio_url(url):
    """Strip tracking/redirect wrappers and query params from a podcast
    audio URL, returning the canonical underlying file URL (or None if
    no URL was given).
    """
    if not url:
        return None

    url = str(url).strip()

    # Drop query string + fragment
    parts = urlsplit(url)
    url = f"{parts.scheme}://{parts.netloc}{parts.path}"

    # Peel off known redirect-wrapper path segments
    changed = True
    while changed:
        changed = False
        for wrapper in REDIRECT_WRAPPERS:
            if wrapper in url:
                url = url.split(wrapper, 1)[1]
                if not url.startswith("http"):
                    url = "https://" + url
                changed = True
                break

    # Canonicalize to the Simplecast URL if one is present
    match = SIMPLECAST_RE.search(url)
    if match:
        url = "https://" + match.group(2)

    # Clean up any duplicated scheme left over from the splitting above
    url = url.replace("https://https://", "https://")
    url = url.replace("http://http://", "http://")

    return url
