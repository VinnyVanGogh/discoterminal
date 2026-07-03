"""CavaVisualizer frame reader against a fake cava process."""

import asyncio

from spotwave.app import SpotifyTUI
from spotwave.visualizer import CavaVisualizer


class FakeProcess:
    def __init__(self, lines):
        self.stdout = iter(lines)

    def poll(self):
        return None  # still "running" until stdout runs dry

    def terminate(self):
        pass


async def test_read_loop_parses_frames_and_tracks_silence(calls):
    app = SpotifyTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)
        viz = app.query_one(CavaVisualizer)
        viz._process = FakeProcess([
            "1;3;5;7;\n",     # audible frame
            "0;0;0;0;\n",     # silence
            "0;0;0;0;\n",     # silence
            "not;numbers\n",  # garbage — skipped
        ])
        # _read_loop normally runs in a worker thread; emulate that.
        await asyncio.to_thread(viz._read_loop)
        await pilot.pause(0.2)
        assert viz._silent_frames == 2
