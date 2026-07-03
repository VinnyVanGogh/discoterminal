"""Lyrics lookup via lrclib.net — free, no API key.

https://lrclib.net/docs
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://lrclib.net/api/get"
USER_AGENT = "spotwave/0.1.0 (https://github.com/VinnyVanGogh/spotwave)"


def get_lyrics(artist: str, track: str, duration: float | None = None) -> str | None:
    """Plain lyrics text, or None when lrclib has no match."""
    params = {"artist_name": artist, "track_name": track}
    if duration:
        params["duration"] = str(int(duration))
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return data.get("plainLyrics") or data.get("syncedLyrics")
