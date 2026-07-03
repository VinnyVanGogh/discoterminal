"""spotui entry point.

Usage:
    spotui                    # open the TUI
    spotui next               # open the TUI and skip track
    spotui <playlist name>    # open the TUI and play that playlist
    spotui play artist NF     # any shpotify command as startup action
"""

import sys

from spotui.app import SpotifyTUI


def main():
    SpotifyTUI(startup_args=sys.argv[1:]).run()


if __name__ == "__main__":
    main()
