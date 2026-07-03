from textual.widgets import Input, ListView

from discoterminal.app import SpotifyTUI
from discoterminal.screens import PickerScreen
from discoterminal.visualizer import PALETTES


async def test_now_playing_renders(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        text = str(app.query_one("#now-playing").render())
        assert "NF" in text and "MOTTO" in text and "65%" in text
        assert app.saved is True and app.track_id == "t1"
        assert app.elapsed and app.total == 180


async def test_keybinds_fire_shpotify_commands(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        for key in ("n", "p", "space", "plus", "minus", "s", "t"):
            await pilot.press(key)
        await pilot.pause(0.5)
    commands = [c[1:] for c in calls if c[0] == "shpotify"]
    for expected in (
        ("next",), ("prev",), ("pause",), ("vol", "up"), ("vol", "down"),
        ("toggle", "shuffle"), ("toggle", "repeat"),
    ):
        assert expected in commands


async def test_playlist_selection_uses_web_api(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.8)
        app.query_one("#playlist-list", ListView).focus()
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause(0.5)
    assert ("api-play", "spotify:playlist:x") in calls


async def test_search_opens_picker_and_plays_choice(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("slash")
        assert isinstance(app.focused, Input)
        for ch in "motto":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause(0.5)
        assert isinstance(app.screen, PickerScreen)
        await pilot.press("enter")
        await pilot.pause(0.5)
    assert ("api-play", "spotify:track:found") in calls


async def test_queue_picker(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("u")
        await pilot.pause(0.5)
        assert isinstance(app.screen, PickerScreen)
        await pilot.press("escape")


async def test_card_flip_shows_artist_and_back(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        await pilot.press("i")
        await pilot.pause(0.5)
        text = str(app.query_one("#now-playing").render())
        assert "Followers" in text and "1,000" in text
        # status poll must not overwrite the artist face
        app.render_now_playing(
            {"state": "playing", "artist": "NF", "track": "MOTTO",
             "position": "1:00 / 3:00"}, 65,
        )
        assert "Followers" in str(app.query_one("#now-playing").render())
        await pilot.press("i")
        await pilot.pause(0.5)
        assert "Track" in str(app.query_one("#now-playing").render())


async def test_palette_switch_rethemes_app(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        assert app.theme == "viz-aurora"
        await pilot.press("c")
        await pilot.pause(0.3)
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause(0.5)
        assert app.theme == "viz-synthwave"
        assert app.get_css_variables()["primary"].lower() == PALETTES["synthwave"][2]


async def test_seek_worker_uses_web_api(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        app.seek_to(90.0)
        await pilot.pause(0.5)
    assert ("api-seek", 90.0) in calls


async def test_like_toggles(calls, monkeypatch):
    from discoterminal import webapi

    monkeypatch.setattr(webapi, "toggle_saved", lambda tid: False)
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.6)
        await pilot.press("l")
        await pilot.pause(0.5)
        assert app.saved is False


async def test_narrow_terminal_hides_sidebar(calls):
    app = SpotifyTUI(startup_args=["chill"])
    async with app.run_test(size=(70, 40)) as pilot:
        await pilot.pause(0.8)
        assert app.has_class("narrow")
    # case-insensitive playlist startup arg resolved after sidebar load
    assert ("api-play", "spotify:playlist:x") in calls
