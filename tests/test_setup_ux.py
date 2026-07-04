from discoterminal import player, webapi
from discoterminal.app import DiscoTerminal


async def test_first_run_shows_setup_checklist(monkeypatch):
    monkeypatch.setattr(player, "_active", player.WebAPIBackend())
    monkeypatch.setattr(webapi, "configured", lambda: False)
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        assert app.needs_setup is True
        text = str(app.query_one("#now-playing").render())
        assert "developer.spotify.com" in text
        assert "client_id" in text
