"""Spotify Web API access via spotipy (PKCE — client ID only).

Credentials: SPOTIPY_CLIENT_ID / SPOTIFY_CLIENT_ID env var, or
~/.config/spotify_player/config.json  {"client_id": "..."}

First call opens a browser for login; token cached afterwards. Scope
changes invalidate the cache and trigger one more login.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "discoterminal"
_LEGACY_CONFIG_DIR = Path.home() / ".config" / "spotify_player"
if not CONFIG_DIR.exists() and _LEGACY_CONFIG_DIR.exists():
    CONFIG_DIR = _LEGACY_CONFIG_DIR  # keep pre-rename setups working
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_CACHE = CONFIG_DIR / ".token-cache"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = " ".join(
    (
        "playlist-read-private",
        "playlist-read-collaborative",
        "user-library-read",
        "user-library-modify",
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
    )
)

_client = None


def _client_id() -> str | None:
    client_id = os.environ.get("SPOTIPY_CLIENT_ID") or os.environ.get(
        "SPOTIFY_CLIENT_ID"
    )
    if client_id:
        return client_id
    try:
        return json.loads(CONFIG_FILE.read_text()).get("client_id")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def configured() -> bool:
    """True when a client ID is available (env var or config file)."""
    return _client_id() is not None


def current_playback():
    """Full playback state (track, progress, device, shuffle/repeat) — one call."""
    return get_client().current_playback()


def get_client():
    """Cached spotipy client. Raises RuntimeError when unconfigured."""
    global _client
    if _client is not None:
        return _client

    import spotipy
    from spotipy.cache_handler import CacheFileHandler
    from spotipy.oauth2 import SpotifyPKCE

    client_id = _client_id()
    if not client_id:
        raise RuntimeError(
            "No Spotify client ID. Set SPOTIPY_CLIENT_ID or add it to "
            f"{CONFIG_FILE}"
        )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    auth = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=CacheFileHandler(cache_path=str(TOKEN_CACHE)),
        open_browser=True,
    )
    _client = spotipy.Spotify(auth_manager=auth)
    try:
        TOKEN_CACHE.chmod(0o600)  # cached OAuth token is a credential
    except OSError:
        pass
    return _client


def all_playlists() -> dict[str, str]:
    """dict of name -> uri for every playlist of the user."""
    sp = get_client()
    playlists = {}
    page = sp.current_user_playlists(limit=50)
    while page:
        for item in page.get("items") or []:
            if item and item.get("name") and item.get("uri"):
                playlists[item["name"]] = item["uri"]
        page = sp.next(page) if page.get("next") else None
    return playlists


def search(query: str, limit: int = 8) -> list[dict[str, str]]:
    """Mixed search. Returns [{'label': str, 'uri': str}], tracks first."""
    sp = get_client()
    response = sp.search(q=query, limit=limit, type="track,album,playlist,artist")
    results = []

    for item in (response.get("tracks") or {}).get("items") or []:
        if not item:
            continue
        artists = ", ".join(a["name"] for a in item.get("artists") or [])
        results.append({"label": f"🎵 {item['name']} — {artists}", "uri": item["uri"]})
    for item in (response.get("albums") or {}).get("items") or []:
        if not item:
            continue
        artists = ", ".join(a["name"] for a in item.get("artists") or [])
        results.append({"label": f"💿 {item['name']} — {artists}", "uri": item["uri"]})
    for item in (response.get("playlists") or {}).get("items") or []:
        if not item:
            continue
        owner = (item.get("owner") or {}).get("display_name", "")
        results.append({"label": f"📻 {item['name']} ({owner})", "uri": item["uri"]})
    for item in (response.get("artists") or {}).get("items") or []:
        if not item:
            continue
        results.append({"label": f"🎤 {item['name']}", "uri": item["uri"]})
    return results


def current_track() -> dict[str, str | None] | None:
    """Currently playing track or None."""
    sp = get_client()
    playing = sp.current_user_playing_track()
    item = (playing or {}).get("item")
    if not item:
        return None
    images = (item.get("album") or {}).get("images") or []
    return {
        "id": item.get("id"),
        "uri": item.get("uri"),
        "name": item.get("name"),
        "artists": ", ".join(a["name"] for a in item.get("artists") or []),
        "art_url": images[0]["url"] if images else None,
    }


def now_playing() -> dict[str, object] | None:
    """Track + playback context + shuffle/repeat state — one call."""
    playback = get_client().current_playback()
    item = (playback or {}).get("item") if playback else None
    if not playback or not item:
        return None
    images = (item.get("album") or {}).get("images") or []
    context = playback.get("context") or {}
    return {
        "id": item.get("id"),
        "uri": item.get("uri"),
        "name": item.get("name"),
        "artists": ", ".join(a["name"] for a in item.get("artists") or []),
        "art_url": images[0]["url"] if images else None,
        "context_uri": context.get("uri"),
        "context_type": context.get("type"),
        "shuffle": bool(playback.get("shuffle_state")),
        "repeat": playback.get("repeat_state") or "off",
    }


def playlist_name(uri: str) -> str | None:
    """Display name of a playlist URI."""
    playlist_id = uri.rsplit(":", 1)[-1]
    data = get_client().playlist(playlist_id, fields="name")
    return (data or {}).get("name")


def playlist_tracks(uri: str, limit: int = 100) -> list[dict[str, str]]:
    """First `limit` tracks of a playlist: [{'label', 'uri'}]."""
    playlist_id = uri.rsplit(":", 1)[-1]
    page = get_client().playlist_items(
        playlist_id, limit=min(limit, 100),
        fields="items(track(name,uri,artists(name)))",
    )
    tracks = []
    for entry in (page or {}).get("items") or []:
        track = (entry or {}).get("track") or {}
        if not track.get("uri"):
            continue
        artists = ", ".join(a["name"] for a in track.get("artists") or [])
        tracks.append(
            {"label": f"🎵 {track.get('name')} — {artists}", "uri": track["uri"]}
        )
    return tracks


LIKED_URI = "discoterminal:liked"  # sentinel — Liked Songs has no real URI


def saved_tracks(limit: int = 100) -> list[dict[str, str]]:
    """The user's Liked Songs (newest first): [{'label', 'uri'}]."""
    sp = get_client()
    tracks: list[dict[str, str]] = []
    offset = 0
    while len(tracks) < limit:
        page = sp.current_user_saved_tracks(limit=50, offset=offset)
        items = (page or {}).get("items") or []
        if not items:
            break
        for entry in items:
            track = (entry or {}).get("track") or {}
            if not track.get("uri"):
                continue
            artists = ", ".join(a["name"] for a in track.get("artists") or [])
            tracks.append(
                {"label": f"🎵 {track.get('name')} — {artists}", "uri": track["uri"]}
            )
        offset += 50
    return tracks[:limit]


def play_liked(track_uri: str | None = None, limit: int = 100) -> None:
    """Play Liked Songs — the API has no context URI for the collection,
    so we queue the track list directly (first `limit` tracks)."""
    uris = [t["uri"] for t in saved_tracks(limit)]
    if not uris:
        raise RuntimeError("No liked songs found")
    if track_uri and track_uri in uris:
        get_client().start_playback(uris=uris, offset={"uri": track_uri})
    else:
        get_client().start_playback(uris=uris)


def play_in_context(context_uri: str, track_uri: str) -> None:
    """Play a specific track inside its playlist/album context."""
    get_client().start_playback(context_uri=context_uri, offset={"uri": track_uri})


def current_artist_info() -> dict[str, object] | None:
    """Profile of the primary artist of the current track, or None."""
    sp = get_client()
    playing = sp.current_user_playing_track()
    artists = ((playing or {}).get("item") or {}).get("artists") or []
    if not artists:
        return None
    artist_id = artists[0].get("id")
    if not artist_id:
        return None
    artist = sp.artist(artist_id)
    top = sp.artist_top_tracks(artist_id)
    images = artist.get("images") or []
    return {
        "id": artist_id,
        "name": artist.get("name"),
        "genres": artist.get("genres") or [],
        "followers": (artist.get("followers") or {}).get("total"),
        "popularity": artist.get("popularity"),
        "image_url": images[0]["url"] if images else None,
        "top_tracks": [
            t["name"] for t in (top.get("tracks") or [])[:5] if t.get("name")
        ],
    }


def is_saved(track_id: str) -> bool:
    sp = get_client()
    result = sp.current_user_saved_tracks_contains([track_id])
    return bool(result and result[0])


def toggle_saved(track_id: str) -> bool:
    """Flip Liked Songs membership. Returns the new saved state."""
    sp = get_client()
    if is_saved(track_id):
        sp.current_user_saved_tracks_delete([track_id])
        return False
    sp.current_user_saved_tracks_add([track_id])
    return True


def devices() -> list[dict[str, object]]:
    """[{'id', 'name', 'type', 'is_active'}] of available playback devices."""
    sp = get_client()
    return [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "type": d.get("type"),
            "is_active": d.get("is_active", False),
        }
        for d in (sp.devices() or {}).get("devices") or []
        if d.get("id")
    ]


def transfer(device_id: str) -> None:
    get_client().transfer_playback(device_id, force_play=True)


def queue() -> list[dict[str, str]]:
    """Upcoming tracks in the play queue: [{'label', 'uri'}]."""
    sp = get_client()
    items = []
    for item in (sp.queue() or {}).get("queue") or []:
        if not item or not item.get("uri"):
            continue
        artists = ", ".join(a["name"] for a in item.get("artists") or [])
        items.append(
            {"label": f"🎵 {item.get('name')} — {artists}", "uri": item["uri"]}
        )
    return items


def seek(seconds: float) -> None:
    """Jump to a position (seconds) in the current track."""
    get_client().seek_track(int(seconds * 1000))


def play(uri: str) -> None:
    """Start playback of a URI via the Web API — no app focus stealing.

    Tracks play directly; albums/playlists/artists play as context.
    Raises when there is no active device (caller falls back to shpotify).
    """
    sp = get_client()
    parts = uri.split(":")
    kind = parts[1] if len(parts) >= 3 else "track"
    if kind == "track":
        sp.start_playback(uris=[uri])
    else:
        sp.start_playback(context_uri=uri)
