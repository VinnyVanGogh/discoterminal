"""Playlist sources for the sidebar.

Primary: Spotify Web API (see webapi.py).
Fallback: local playlists.json next to this file, seeded with PRESETS.
"""

import json
from pathlib import Path

from spotui import webapi

LOCAL_FILE = Path(__file__).parent / "playlists.json"

PRESETS = {
    "emo": "spotify:playlist:2qGqm36EKzi0JTv7zgcdYY",
    "swolemates": "spotify:playlist:3M8nJT5Y34Ouo8egaTduiy",
    "nf": "spotify:playlist:37i9dQZF1E4wIccOCmPFGt",
}


def load_local():
    """Playlists from playlists.json, else the built-in presets."""
    try:
        data = json.loads(LOCAL_FILE.read_text())
        if isinstance(data, dict) and data:
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return dict(PRESETS)


def get_playlists():
    """Returns (playlists, source, error) where source is 'spotify' or 'local'."""
    try:
        playlists = webapi.all_playlists()
        if not playlists:
            raise RuntimeError("Spotify returned no playlists")
        return playlists, "spotify", None
    except Exception as e:
        return load_local(), "local", str(e)
