"""macOS default-output switching via CoreAudio (ctypes, no dependencies).

Enables the "Spotify TUI Multi-Out" aggregate device while the app runs —
so cava hears audio — and restores the previous output on exit. The
aggregate itself is created once by scripts/setup-audio.swift; this module
only switches between existing devices.

Set {"auto_multiout": false} in config.json to opt out.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import sys

from discoterminal import webapi

MULTIOUT_UID = "com.spotify-tui.multi-out"

_core: ctypes.CDLL | None
_cf: ctypes.CDLL | None
if sys.platform == "darwin":
    try:
        _core = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
        _cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
    except (OSError, TypeError):
        _core = _cf = None
else:  # Linux/Windows need no output switching for the visualizer
    _core = _cf = None

_SYSTEM_OBJECT = 1
_ELEMENT_MAIN = 0
_UTF8 = 0x08000100


def _fourcc(code: str) -> int:
    return int.from_bytes(code.encode("ascii"), "big")


class _PropertyAddress(ctypes.Structure):
    _fields_ = [
        ("selector", ctypes.c_uint32),
        ("scope", ctypes.c_uint32),
        ("element", ctypes.c_uint32),
    ]


def _address(selector: str) -> _PropertyAddress:
    return _PropertyAddress(_fourcc(selector), _fourcc("glob"), _ELEMENT_MAIN)


def _get_data(object_id, selector, buffer):
    assert _core is not None
    address = _address(selector)
    size = ctypes.c_uint32(ctypes.sizeof(buffer))
    status = _core.AudioObjectGetPropertyData(
        object_id, ctypes.byref(address), 0, None,
        ctypes.byref(size), ctypes.byref(buffer),
    )
    if status != 0:
        raise OSError(f"CoreAudio error {status} reading {selector!r}")


def default_output() -> int:
    """AudioDeviceID of the current default output device."""
    device = ctypes.c_uint32(0)
    _get_data(_SYSTEM_OBJECT, "dOut", device)
    return device.value


def set_default_output(device_id: int) -> None:
    assert _core is not None
    address = _address("dOut")
    device = ctypes.c_uint32(device_id)
    status = _core.AudioObjectSetPropertyData(
        _SYSTEM_OBJECT, ctypes.byref(address), 0, None,
        ctypes.sizeof(device), ctypes.byref(device),
    )
    if status != 0:
        raise OSError(f"CoreAudio error {status} setting default output")


def _all_devices() -> list[int]:
    assert _core is not None
    address = _address("dev#")
    size = ctypes.c_uint32(0)
    if _core.AudioObjectGetPropertyDataSize(
        _SYSTEM_OBJECT, ctypes.byref(address), 0, None, ctypes.byref(size)
    ) != 0:
        return []
    devices = (ctypes.c_uint32 * (size.value // 4))()
    if _core.AudioObjectGetPropertyData(
        _SYSTEM_OBJECT, ctypes.byref(address), 0, None,
        ctypes.byref(size), ctypes.byref(devices),
    ) != 0:
        return []
    return list(devices)


def device_uid(device_id: int) -> str:
    assert _cf is not None
    ref = ctypes.c_void_p(0)
    try:
        _get_data(device_id, "uid ", ref)
    except OSError:
        return ""
    if not ref.value:
        return ""
    buffer = ctypes.create_string_buffer(256)
    _cf.CFStringGetCString(ref, buffer, 256, _UTF8)
    _cf.CFRelease(ref)
    return buffer.value.decode("utf-8", "replace")


def find_device(uid: str) -> int | None:
    for device in _all_devices():
        if device_uid(device) == uid:
            return device
    return None


def _auto_enabled() -> bool:
    try:
        return json.loads(webapi.CONFIG_FILE.read_text()).get("auto_multiout", True)
    except (OSError, ValueError):
        return True


def enable_multiout() -> int | None:
    """Make the discoterminal Multi-Out the default output.

    Returns the previous default device id (for restore_output), or None
    when nothing changed: not macOS, opted out, device not set up, or
    Multi-Out already active.
    """
    if _core is None or not _auto_enabled():
        return None
    multiout = find_device(MULTIOUT_UID)
    if multiout is None:
        return None
    previous = default_output()
    if previous == multiout:
        return None
    set_default_output(multiout)
    return previous


def restore_output(device_id: int) -> None:
    """Best-effort restore of a previously saved default output."""
    if _core is None:
        return
    try:
        set_default_output(device_id)
    except OSError:
        pass
