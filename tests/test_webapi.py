"""webapi response-shaping against realistic Spotify JSON payloads."""

from spotwave import webapi


class FakeSpotify:
    def __init__(self):
        self.calls = []

    def search(self, q, limit, type):
        return {
            "tracks": {"items": [
                {"name": "MOTTO", "uri": "spotify:track:t1",
                 "artists": [{"name": "NF"}, {"name": "Cordae"}]},
                None,
            ]},
            "albums": {"items": [
                {"name": "HOPE", "uri": "spotify:album:a1",
                 "artists": [{"name": "NF"}]},
            ]},
            "playlists": {"items": [
                {"name": "Rap Mix", "uri": "spotify:playlist:p1",
                 "owner": {"display_name": "Spotify"}},
                None,
            ]},
            "artists": {"items": [{"name": "NF", "uri": "spotify:artist:ar1"}]},
        }

    def queue(self):
        return {"queue": [
            {"name": "Next Up", "uri": "spotify:track:t2",
             "artists": [{"name": "NF"}]},
            {"name": "No URI Track", "artists": []},
            None,
        ]}

    def current_user_playing_track(self):
        return {"item": {
            "id": "t1", "uri": "spotify:track:t1", "name": "MOTTO",
            "artists": [{"name": "NF", "id": "ar1"}],
            "album": {"images": [{"url": "https://img/cover.jpg"}]},
        }}

    def artist(self, artist_id):
        return {"name": "NF", "genres": ["hip hop", "rap"],
                "followers": {"total": 5000000}, "popularity": 88,
                "images": [{"url": "https://img/artist.jpg"}]}

    def artist_top_tracks(self, artist_id):
        return {"tracks": [{"name": f"Track {i}"} for i in range(8)]}

    def current_user_playlists(self, limit):
        return {"items": [{"name": "One", "uri": "spotify:playlist:1"}],
                "next": "page2"}

    def next(self, page):
        return {"items": [{"name": "Two", "uri": "spotify:playlist:2"},
                          {"name": None, "uri": "spotify:playlist:skip"}],
                "next": None}

    def devices(self):
        return {"devices": [
            {"id": "d1", "name": "Mac", "type": "Computer", "is_active": True},
            {"name": "Ghost", "type": "Speaker"},  # no id -> filtered
        ]}

    def current_user_saved_tracks_contains(self, ids):
        return [True]

    def current_user_saved_tracks_delete(self, ids):
        self.calls.append(("delete", ids))

    def current_user_saved_tracks_add(self, ids):
        self.calls.append(("add", ids))


def _fake(monkeypatch):
    sp = FakeSpotify()
    monkeypatch.setattr(webapi, "get_client", lambda: sp)
    return sp


def test_search_orders_and_labels(monkeypatch):
    _fake(monkeypatch)
    results = webapi.search("motto")
    labels = [r["label"] for r in results]
    assert labels[0].startswith("🎵 MOTTO — NF, Cordae")
    assert any(label.startswith("💿 HOPE") for label in labels)
    assert any("Rap Mix (Spotify)" in label for label in labels)
    assert labels[-1] == "🎤 NF"
    assert all(r["uri"] for r in results)


def test_queue_filters_bad_items(monkeypatch):
    _fake(monkeypatch)
    items = webapi.queue()
    assert len(items) == 1
    assert items[0]["uri"] == "spotify:track:t2"


def test_current_track_extracts_art(monkeypatch):
    _fake(monkeypatch)
    track = webapi.current_track()
    assert track is not None
    assert track["art_url"] == "https://img/cover.jpg"
    assert track["artists"] == "NF"


def test_artist_info_caps_top_tracks(monkeypatch):
    _fake(monkeypatch)
    info = webapi.current_artist_info()
    assert info is not None
    assert info["followers"] == 5000000
    assert len(info["top_tracks"]) == 5


def test_all_playlists_paginates(monkeypatch):
    _fake(monkeypatch)
    playlists = webapi.all_playlists()
    assert playlists == {"One": "spotify:playlist:1", "Two": "spotify:playlist:2"}


def test_devices_filters_missing_ids(monkeypatch):
    _fake(monkeypatch)
    devices = webapi.devices()
    assert len(devices) == 1 and devices[0]["id"] == "d1"


def test_toggle_saved_removes_when_saved(monkeypatch):
    sp = _fake(monkeypatch)
    assert webapi.toggle_saved("t1") is False
    assert ("delete", ["t1"]) in sp.calls
