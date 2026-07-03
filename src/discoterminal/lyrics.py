"""Lyrics lookup via lrclib.net — free, no API key.

https://lrclib.net/docs
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

API = "https://lrclib.net/api/get"
USER_AGENT = "discoterminal/0.1.0 (https://github.com/VinnyVanGogh/discoterminal)"

TIMESTAMP_RE = re.compile(r"\[(\d+):(\d{2})(?:\.(\d{1,2}))?\]\s?(.*)")


def fetch(artist: str, track: str, duration: float | None = None) -> dict | None:
    """The raw lrclib record ({plainLyrics, syncedLyrics, ...}) or None on 404."""
    params = {"artist_name": artist, "track_name": track}
    if duration:
        params["duration"] = str(int(duration))
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def get_lyrics(artist: str, track: str, duration: float | None = None) -> str | None:
    """Plain lyrics text, or None when lrclib has no match."""
    data = fetch(artist, track, duration)
    if not data:
        return None
    return data.get("plainLyrics") or data.get("syncedLyrics")


def parse_synced(text: str) -> list[tuple[float, str]]:
    """'[01:23.45] line' lyrics -> [(seconds, line)], sorted by time."""
    lines: list[tuple[float, str]] = []
    for raw in text.splitlines():
        match = TIMESTAMP_RE.match(raw.strip())
        if not match:
            continue
        minutes, seconds, frac, words = match.groups()
        fraction = int(frac) / (10 ** len(frac)) if frac else 0.0
        stamp = int(minutes) * 60 + int(seconds) + fraction
        lines.append((stamp, words.strip()))
    lines.sort(key=lambda pair: pair[0])
    return lines


def get_synced(
    artist: str, track: str, duration: float | None = None
) -> tuple[list[tuple[float, str]] | None, str | None]:
    """(synced_lines, plain_text) — either may be None."""
    data = fetch(artist, track, duration)
    if not data:
        return None, None
    synced = data.get("syncedLyrics")
    lines = parse_synced(synced) if synced else None
    return (lines or None), data.get("plainLyrics")
