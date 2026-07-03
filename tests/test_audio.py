from discoterminal import audio


def test_enable_returns_none_when_multiout_missing(monkeypatch):
    monkeypatch.setattr(audio, "_auto_enabled", lambda: True)
    monkeypatch.setattr(audio, "find_device", lambda uid: None)
    if audio._core is not None:
        assert audio.enable_multiout() is None


def test_enable_respects_opt_out(monkeypatch):
    monkeypatch.setattr(audio, "_auto_enabled", lambda: False)
    assert audio.enable_multiout() is None


def test_enable_switches_and_reports_previous(monkeypatch):
    if audio._core is None:  # non-macOS CI
        assert audio.enable_multiout() is None
        return
    switched = []
    monkeypatch.setattr(audio, "_auto_enabled", lambda: True)
    monkeypatch.setattr(audio, "find_device", lambda uid: 42)
    monkeypatch.setattr(audio, "default_output", lambda: 7)
    monkeypatch.setattr(audio, "set_default_output", switched.append)
    assert audio.enable_multiout() == 7
    assert switched == [42]


def test_enable_noop_when_already_active(monkeypatch):
    if audio._core is None:
        return
    monkeypatch.setattr(audio, "_auto_enabled", lambda: True)
    monkeypatch.setattr(audio, "find_device", lambda uid: 42)
    monkeypatch.setattr(audio, "default_output", lambda: 42)
    assert audio.enable_multiout() is None
