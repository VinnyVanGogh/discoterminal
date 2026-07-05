"""Rave mode: beat detection, R-cycle, palette restore, takeover."""

from discoterminal.app import DiscoTerminal
from discoterminal.visualizer import BEAT_MIN_INTERVAL, CavaVisualizer


def test_beat_detector_fires_on_energy_spike():
    viz = CavaVisualizer.__new__(CavaVisualizer)
    viz._energy_window = []
    viz._last_beat = 0.0
    now = 100.0
    # steady quiet frames build the rolling average
    for _ in range(10):
        assert not viz._check_beat([1] * 50, now)
        now += 1 / 12
    # a loud frame is a beat
    assert viz._check_beat([8] * 50, now)


def test_beat_detector_rate_limited():
    viz = CavaVisualizer.__new__(CavaVisualizer)
    viz._energy_window = []
    viz._last_beat = 0.0
    now = 100.0
    for _ in range(10):
        viz._check_beat([1] * 50, now)
        now += 1 / 12
    assert viz._check_beat([8] * 50, now)
    # an equally loud frame right after is suppressed by the flash cap
    assert not viz._check_beat([8] * 50, now + 0.05)
    # ...but allowed once the interval has passed
    assert viz._check_beat([9] * 50, now + BEAT_MIN_INTERVAL + 0.01)


async def test_rave_cycle_and_palette_restore(calls):
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        original = app.palette_name
        await pilot.press("R")
        assert app.rave_mode == "pulse"
        # beats strobe the theme without persisting anything
        app.on_rave_beat()
        assert app.palette_name != original
        strobed = app.palette_name
        app.on_rave_beat()
        assert app.palette_name != strobed  # never repeats back-to-back
        await pilot.press("R")
        assert app.rave_mode == "takeover"
        assert app.has_class("rave-takeover")
        await pilot.press("R")
        await pilot.pause(0.3)
        assert app.rave_mode == "off"
        assert not app.has_class("rave-takeover")
        assert app.palette_name == original  # saved palette restored


async def test_escape_exits_takeover(calls):
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("R")
        await pilot.press("R")
        assert app.rave_mode == "takeover"
        await pilot.press("escape")
        await pilot.pause(0.3)
        assert app.rave_mode == "off"


async def test_beats_ignored_when_rave_off(calls):
    app = DiscoTerminal()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)
        before = app.palette_name
        app.on_rave_beat()
        assert app.palette_name == before
