"""discoterminal entry point.

Usage:
    discoterminal                    # open the TUI
    discoterminal next               # open the TUI and skip track
    discoterminal <playlist name>    # open the TUI and play that playlist
    discoterminal play artist NF     # any shpotify command as startup action
"""

import sys

from discoterminal import audio
from discoterminal.app import SpotifyTUI


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
