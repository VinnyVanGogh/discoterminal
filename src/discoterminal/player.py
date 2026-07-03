"""Playback backends.

Local CLIs are the fast path — shpotify on macOS, playerctl on Linux —
with the Spotify Web API as the universal fallback (the only option on
Windows). Selection is automatic; override with {"backend": "shpotify" |
"playerctl" | "webapi"} in config.json.

Every backend exposes the same surface: `status()` returning a normalized
dict (state/artist/album/track/position/volume), `command(action)` for the
fixed action set, and `seek(seconds)`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

from discoterminal import spotify, webapi

StatusDict = dict[str, object]

ACTIONS = (
    "play", "pause", "next", "prev", "replay",
    "vol_up", "vol_down", "shuffle", "repeat",
)


class BackendError(Exception):
    """A playback command failed; message is user-displayable."""


class Backend:
    name = "base"

    def status(self) -> StatusDict | None:
        raise NotImplementedError

    def command(self, action: str) -> None:
        raise NotImplementedError

    def seek(self, seconds: float) -> None:
        raise NotImplementedError


def _clock(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


class ShpotifyBackend(Backend):
    """macOS: the `spotify` CLI (shpotify) via AppleScript. No Premium needed."""

    name = "shpotify"

    _ACTIONS: dict[str, tuple[str, ...]] = {
        "play": ("play",),
        "pause": ("pause",),
        "next": ("next",),
        "prev": ("prev",),
        "replay": ("replay",),
        "vol_up": ("vol", "up"),
        "vol_down": ("vol", "down"),
        "shuffle": ("toggle", "shuffle"),
        "repeat": ("toggle", "repeat"),
    }

    @staticmethod
    def available() -> bool:
        return sys.platform == "darwin" and shutil.which("spotify") is not None

    def status(self) -> StatusDict | None:
        status = spotify.get_status()
        if status is None:
            return None
        result: StatusDict = dict(status)
        result["volume"] = spotify.get_volume()
        return result

    def command(self, action: str) -> None:
        result = spotify.run(*self._ACTIONS[action])
        if not result.ok:
            raise BackendError(result.output or f"{action} failed")

    def seek(self, seconds: float) -> None:
        result = spotify.run("pos", str(int(seconds)))
        if not result.ok:
            raise BackendError(result.output or "seek failed")


class PlayerctlBackend(Backend):
    """Linux: playerctl over MPRIS. No Premium needed."""

    name = "playerctl"

    _BASE = ("playerctl", "-p", "spotify")
    _SEP = "\x1f"
    _ACTIONS: dict[str, tuple[str, ...]] = {
        "play": ("play",),
        "pause": ("pause",),
        "next": ("next",),
        "prev": ("previous",),
        "replay": ("position", "0"),
        "vol_up": ("volume", "0.05+"),
        "vol_down": ("volume", "0.05-"),
        "shuffle": ("shuffle", "toggle"),
    }

    @staticmethod
    def available() -> bool:
        return sys.platform.startswith("linux") and shutil.which("playerctl") is not None

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            [*self._BASE, *args], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise BackendError(result.stderr.strip() or f"playerctl {args[0]} failed")
        return result.stdout.strip()

    def status(self) -> StatusDict | None:
        template = self._SEP.join(
            ("{{status}}", "{{artist}}", "{{album}}", "{{title}}",
             "{{position}}", "{{mpris:length}}", "{{volume}}")
        )
        try:
            raw = self._run("metadata", "--format", template)
        except BackendError:
            return None
        parts = raw.split(self._SEP)
        if len(parts) < 7:
            return None
        state, artist, album, title, position, length, volume = parts[:7]

        def us_clock(value: str) -> str:
            try:
                return _clock(int(float(value)) // 1_000_000)
            except ValueError:
                return "0:00"

        return {
            "state": "playing" if state.lower() == "playing" else "paused",
            "artist": artist,
            "album": album,
            "track": title,
            "position": f"{us_clock(position)} / {us_clock(length)}",
            "volume": int(float(volume) * 100) if volume else None,
        }

    def command(self, action: str) -> None:
        if action == "repeat":
            current = self._run("loop")
            cycle = {"None": "Playlist", "Playlist": "Track", "Track": "None"}
            self._run("loop", cycle.get(current, "None"))
            return
        self._run(*self._ACTIONS[action])

    def seek(self, seconds: float) -> None:
        self._run("position", str(int(seconds)))


class WebAPIBackend(Backend):
    """Any platform: pure Web API. Needs Premium and an active device."""

    name = "webapi"

    def __init__(self) -> None:
        self._volume: int | None = None
        self._shuffle: bool = False
        self._repeat: str = "off"

    @staticmethod
    def available() -> bool:
        return webapi.configured()

    def status(self) -> StatusDict | None:
        try:
            playback = webapi.current_playback()
        except Exception:
            return None
        item = (playback or {}).get("item") if playback else None
        if not playback or not item:
            return None

        def ms_clock(ms: object) -> str:
            try:
                return _clock(int(ms) // 1000)  # type: ignore[call-overload]
            except (TypeError, ValueError):
                return "0:00"

        device = playback.get("device") or {}
        self._volume = device.get("volume_percent")
        self._shuffle = bool(playback.get("shuffle_state"))
        self._repeat = playback.get("repeat_state") or "off"
        return {
            "state": "playing" if playback.get("is_playing") else "paused",
            "artist": ", ".join(a["name"] for a in item.get("artists") or []),
            "album": (item.get("album") or {}).get("name", ""),
            "track": item.get("name", ""),
            "position": (
                f"{ms_clock(playback.get('progress_ms'))} / "
                f"{ms_clock(item.get('duration_ms'))}"
            ),
            "shuffle": str(self._shuffle).lower(),
            "repeat": self._repeat,
            "volume": self._volume,
        }

    def command(self, action: str) -> None:
        try:
            self._command(action)
        except BackendError:
            raise
        except Exception as e:
            raise BackendError(str(e)) from e

    def _command(self, action: str) -> None:
        sp = webapi.get_client()
        if action == "play":
            sp.start_playback()
        elif action == "pause":
            sp.pause_playback()
        elif action == "next":
            sp.next_track()
        elif action == "prev":
            sp.previous_track()
        elif action == "replay":
            sp.seek_track(0)
        elif action in ("vol_up", "vol_down"):
            if self._volume is None:
                raise BackendError("volume unknown — wait for status")
            step = 10 if action == "vol_up" else -10
            self._volume = max(0, min(100, self._volume + step))
            sp.volume(self._volume)
        elif action == "shuffle":
            self._shuffle = not self._shuffle
            sp.shuffle(self._shuffle)
        elif action == "repeat":
            cycle = {"off": "context", "context": "track", "track": "off"}
            self._repeat = cycle.get(self._repeat, "off")
            sp.repeat(self._repeat)

    def seek(self, seconds: float) -> None:
        webapi.seek(seconds)


_BACKENDS: dict[str, type[Backend]] = {
    "shpotify": ShpotifyBackend,
    "playerctl": PlayerctlBackend,
    "webapi": WebAPIBackend,
}

_active: Backend | None = None


def _configured_choice() -> str | None:
    try:
        return json.loads(webapi.CONFIG_FILE.read_text()).get("backend")
    except (OSError, ValueError):
        return None


def get_backend() -> Backend:
    """The active backend, selected once per process."""
    global _active
    if _active is None:
        choice = _configured_choice()
        if choice in _BACKENDS:
            _active = _BACKENDS[choice]()
        elif ShpotifyBackend.available():
            _active = ShpotifyBackend()
        elif PlayerctlBackend.available():
            _active = PlayerctlBackend()
        else:
            _active = WebAPIBackend()
    return _active
