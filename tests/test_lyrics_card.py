"""Synced-lyrics card face: follows playback position like Spotify."""

from discoterminal import lyrics
from discoterminal.app import DiscoTerminal

SYNCED = [(0.0, "Line zero"), (58.0, "Line one"), (62.0, "Line two"), (120.0, "Line three")]


async def test_lyrics_card_highlights_current_line(calls, monkeypatch):
    monkeypatch.setattr(lyrics, "get_synced", lambda a, t, d=None: (SYNCED, "plain"))
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        assert app.elapsed == 60  # from mocked position "1:00 / 3:00"
        await pilot.press("y")
        await pilot.pause(0.5)
        assert app.card_face == "lyrics"
        text = str(app.query_one("#now-playing").render())
        assert "▶ Line one" in text, text  # 58s <= 60 < 62s
        assert "Line two" in text

        # tick past 62s -> highlight advances
        app.elapsed = 62
        app.last_state = "playing"
        app.tick_position()
        await pilot.pause(0.2)
        text = str(app.query_one("#now-playing").render())
        assert "▶ Line two" in text, text

        # y again flips back to the playing face
        await pilot.press("y")
        await pilot.pause(0.5)
        assert app.card_face == "playing"
        assert "Track" in str(app.query_one("#now-playing").render())


async def test_lyrics_card_plain_fallback(calls, monkeypatch):
    monkeypatch.setattr(
        lyrics, "get_synced", lambda a, t, d=None: (None, "just plain text\nmore")
    )
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        await pilot.press("y")
        await pilot.pause(0.5)
        text = str(app.query_one("#now-playing").render())
        assert "no sync available" in text and "just plain text" in text


async def test_lyrics_card_none_found(calls, monkeypatch):
    monkeypatch.setattr(lyrics, "get_synced", lambda a, t, d=None: (None, None))
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        await pilot.press("y")
        await pilot.pause(0.5)
        assert "No lyrics found" in str(app.query_one("#now-playing").render())


async def test_lyrics_offset_nudges_index(calls, monkeypatch):
    from discoterminal import visualizer

    monkeypatch.setattr(lyrics, "get_synced", lambda a, t, d=None: (SYNCED, None))
    monkeypatch.setattr(visualizer, "_save_config_value", lambda k, v: None)
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        app.lyrics_offset = 0.0
        await pilot.press("y")
        await pilot.pause(0.5)
        assert "▶ Line one" in str(app.query_one("#now-playing").render())
        # +2.0s pushes effective position from 60 past the 62s line
        for _ in range(4):
            await pilot.press("right_square_bracket")
        await pilot.pause(0.3)
        assert app.lyrics_offset == 2.0
        assert "▶ Line two" in str(app.query_one("#now-playing").render())


async def test_precise_position_resync(calls, monkeypatch):
    monkeypatch.setattr(lyrics, "get_synced", lambda a, t, d=None: (SYNCED, None))
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        await pilot.press("y")
        await pilot.pause(0.5)
        app.set_precise_position(63.25)  # webapi progress_ms path
        await pilot.pause(0.2)
        assert app.elapsed == 63.25
        assert "▶ Line two" in str(app.query_one("#now-playing").render())
