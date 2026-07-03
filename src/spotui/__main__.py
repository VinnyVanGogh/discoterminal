"""spotui entry point.

Usage:
    spotui                    # open the TUI
    spotui next               # open the TUI and skip track
    spotui <playlist name>    # open the TUI and play that playlist
    spotui play artist NF     # any shpotify command as startup action
"""

import sys

from spotui import audio
from spotui.app import SpotifyTUI


def main():
    try:
        # Route audio through the Multi-Out (visualizer feed) while running.
        restore = audio.enable_multiout()
    except Exception:
        restore = None
    try:
        SpotifyTUI(startup_args=sys.argv[1:]).run()
    finally:
        if restore is not None:
            audio.restore_output(restore)


if __name__ == "__main__":
    main()
