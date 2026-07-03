from discoterminal import player, spotify, webapi


def test_shpotify_status_merges_volume(monkeypatch):
    monkeypatch.setattr(
        spotify, "get_status", lambda: {"state": "playing", "track": "X"}
    )
    monkeypatch.setattr(spotify, "get_volume", lambda: 40)
    status = player.ShpotifyBackend().status()
    assert status == {"state": "playing", "track": "X", "volume": 40}


def test_shpotify_command_raises_on_failure(monkeypatch):
    monkeypatch.setattr(
        spotify, "run", lambda *a: spotify.SpotifyResult(False, "boom")
    )
    backend = player.ShpotifyBackend()
    try:
        backend.command("next")
        raise AssertionError("expected BackendError")
    except player.BackendError as e:
        assert "boom" in str(e)


def test_playerctl_status_parses_metadata(monkeypatch):
    sep = "\x1f"
    raw = sep.join(
        ("Playing", "NF", "HOPE", "MOTTO", "86000000", "163000000", "0.65")
    )
    monkeypatch.setattr(player.PlayerctlBackend, "_run", lambda self, *a: raw)
    status = player.PlayerctlBackend().status()
    assert status == {
        "state": "playing",
        "artist": "NF",
        "album": "HOPE",
        "track": "MOTTO",
        "position": "1:26 / 2:43",
        "volume": 65,
    }


def test_playerctl_repeat_cycles_loop(monkeypatch):
    seen = []

    def fake_run(self, *args):
        seen.append(args)
        return "Playlist" if args == ("loop",) else ""

    monkeypatch.setattr(player.PlayerctlBackend, "_run", fake_run)
    player.PlayerctlBackend().command("repeat")
    assert ("loop", "Track") in seen


def test_webapi_status_normalizes_playback(monkeypatch):
    playback = {
        "is_playing": True,
        "progress_ms": 86000,
        "shuffle_state": True,
        "repeat_state": "context",
        "device": {"volume_percent": 65},
        "item": {
            "name": "MOTTO",
            "duration_ms": 163000,
            "artists": [{"name": "NF"}],
            "album": {"name": "HOPE"},
        },
    }
    monkeypatch.setattr(webapi, "current_playback", lambda: playback)
    status = player.WebAPIBackend().status()
    assert status is not None
    assert status["position"] == "1:26 / 2:43"
    assert status["state"] == "playing"
    assert status["volume"] == 65


def test_backend_selection_prefers_local(monkeypatch):
    monkeypatch.setattr(player, "_active", None)
    monkeypatch.setattr(player, "_configured_choice", lambda: None)
    monkeypatch.setattr(player.ShpotifyBackend, "available", staticmethod(lambda: True))
    assert player.get_backend().name == "shpotify"


def test_backend_selection_falls_back_to_webapi(monkeypatch):
    monkeypatch.setattr(player, "_active", None)
    monkeypatch.setattr(player, "_configured_choice", lambda: None)
    monkeypatch.setattr(player.ShpotifyBackend, "available", staticmethod(lambda: False))
    monkeypatch.setattr(player.PlayerctlBackend, "available", staticmethod(lambda: False))
    assert player.get_backend().name == "webapi"


def test_backend_config_override(monkeypatch):
    monkeypatch.setattr(player, "_active", None)
    monkeypatch.setattr(player, "_configured_choice", lambda: "webapi")
    assert player.get_backend().name == "webapi"
