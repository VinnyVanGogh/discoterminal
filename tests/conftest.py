import pytest

from discoterminal import player, spotify, visualizer, webapi


@pytest.fixture
def calls(monkeypatch):
    """Mock every external backend; returns the recorded call list."""
    recorded = []

    def fake_run(command, *args):
        recorded.append(("shpotify", command, *args))
        return spotify.SpotifyResult(True, "")

    monkeypatch.setattr(spotify, "run", fake_run)
    monkeypatch.setattr(
        spotify,
        "get_status",
        lambda: {
            "state": "playing",
            "artist": "NF",
            "album": "HOPE",
            "track": "MOTTO",
            "position": "1:00 / 3:00",
        },
    )
    monkeypatch.setattr(spotify, "get_volume", lambda: 65)

    monkeypatch.setattr(webapi, "all_playlists", lambda: {"Chill": "spotify:playlist:x"})
    monkeypatch.setattr(
        webapi,
        "current_track",
        lambda: {"id": "t1", "uri": "spotify:track:t1", "name": "MOTTO",
                 "artists": "NF", "art_url": None},
    )
    monkeypatch.setattr(webapi, "is_saved", lambda tid: True)
    monkeypatch.setattr(webapi, "play", lambda uri: recorded.append(("api-play", uri)))
    monkeypatch.setattr(webapi, "seek", lambda s: recorded.append(("api-seek", s)))
    monkeypatch.setattr(
        webapi, "queue",
        lambda: [{"label": "🎵 Next One — NF", "uri": "spotify:track:t2"}],
    )
    monkeypatch.setattr(
        webapi, "search",
        lambda q, limit=8: [{"label": f"🎵 {q}", "uri": "spotify:track:found"}],
    )
    monkeypatch.setattr(
        webapi, "devices",
        lambda: [{"id": "d1", "name": "Mac", "type": "Computer", "is_active": True}],
    )
    monkeypatch.setattr(webapi, "transfer", lambda d: recorded.append(("transfer", d)))
    monkeypatch.setattr(
        webapi, "current_artist_info",
        lambda: {"id": "a1", "name": "NF", "genres": ["rap"], "followers": 1000,
                 "popularity": 80, "image_url": None, "top_tracks": ["MOTTO"]},
    )

    # Force the shpotify backend everywhere (its CLI calls are mocked above),
    # so tests behave identically on macOS and CI runners.
    monkeypatch.setattr(player, "_active", player.ShpotifyBackend())
    monkeypatch.setattr(webapi, "configured", lambda: True)

    monkeypatch.setattr(visualizer, "save_style", lambda s: None)
    monkeypatch.setattr(visualizer, "save_palette", lambda s: None)
    monkeypatch.setattr(visualizer, "load_style", lambda: "area")
    monkeypatch.setattr(visualizer, "load_palette", lambda: "aurora")
    monkeypatch.setattr(visualizer, "cava_available", lambda: False)
    return recorded
