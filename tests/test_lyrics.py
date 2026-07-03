"""lyrics module against mocked lrclib responses."""

import io
import json
import urllib.error
import urllib.request

import pytest

from discoterminal import lyrics


def _respond(monkeypatch, payload):
    def fake_urlopen(request, timeout=10):
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def test_plain_lyrics_preferred(monkeypatch):
    _respond(monkeypatch, {"plainLyrics": "hello", "syncedLyrics": "[00:01] hello"})
    assert lyrics.get_lyrics("NF", "MOTTO") == "hello"


def test_synced_fallback(monkeypatch):
    _respond(monkeypatch, {"plainLyrics": None, "syncedLyrics": "[00:01] hi"})
    assert lyrics.get_lyrics("NF", "MOTTO") == "[00:01] hi"


def test_404_returns_none(monkeypatch):
    def raise_404(request, timeout=10):
        raise urllib.error.HTTPError("url", 404, "not found", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", raise_404)
    assert lyrics.get_lyrics("Nobody", "Nothing") is None


def test_server_error_raises(monkeypatch):
    def raise_500(request, timeout=10):
        raise urllib.error.HTTPError("url", 500, "boom", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", raise_500)
    with pytest.raises(urllib.error.HTTPError):
        lyrics.get_lyrics("NF", "MOTTO")


def test_duration_param_stringified(monkeypatch):
    seen = {}

    def capture(request, timeout=10):
        seen["url"] = request.full_url
        body = io.BytesIO(b'{"plainLyrics": "x"}')
        return body

    monkeypatch.setattr(urllib.request, "urlopen", capture)
    lyrics.get_lyrics("NF", "MOTTO", duration=163.7)
    assert "duration=163" in seen["url"]
