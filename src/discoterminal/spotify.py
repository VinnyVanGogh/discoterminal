"""Thin wrapper around the shpotify CLI (`spotify` on PATH)."""

from __future__ import annotations

import re
import subprocess

ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-9;]*[A-Za-z]|\(B)")


class SpotifyResult:
    def __init__(self, ok: bool, output: str) -> None:
        self.ok = ok
        self.output = output


def run(command: str, *args: str) -> SpotifyResult:
    """Run `spotify <command> [args...]`. Never raises."""
    cmd = ["spotify", command, *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        return SpotifyResult(False, str(e))
    if result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip()
        return SpotifyResult(False, ANSI_ESCAPE.sub("", output))
    return SpotifyResult(True, ANSI_ESCAPE.sub("", result.stdout.strip()))


STATUS_FIELDS = ("Artist", "Album", "Track", "Position", "Shuffle", "Repeat")


def get_status() -> dict[str, str] | None:
    """Parse `spotify status` output into a dict, or None on failure.

    shpotify emits lines like `Artist: NF` plus a first line such as
    `Spotify is currently playing/paused`.
    """
    result = run("status")
    if not result.ok or not result.output:
        return None

    return parse_status(result.output)


def parse_status(output: str) -> dict[str, str] | None:

    status = {}
    for line in output.splitlines():
        for field in STATUS_FIELDS:
            marker = f"{field}:"
            if marker in line:
                status[field.lower()] = line.split(marker, 1)[1].strip()
                break
        else:
            lowered = line.lower()
            if "playing" in lowered:
                status["state"] = "playing"
            elif "paused" in lowered:
                status["state"] = "paused"
    return status or None


def get_volume() -> int | None:
    """Current volume 0-100 as int, or None. shpotify prints e.g.
    `Current Spotify volume level is 66.`"""
    result = run("vol")
    if not result.ok:
        return None
    digits = "".join(c for c in result.output if c.isdigit())
    return int(digits) if digits else None
