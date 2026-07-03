from spotwave.app import format_seconds, parse_position
from spotwave.spotify import ANSI_ESCAPE, parse_status


def test_parse_position():
    assert parse_position("1:26 / 2:43") == (86, 163)
    assert parse_position("0:00 / 10:05") == (0, 605)
    assert parse_position("garbage") == (None, None)
    assert parse_position(None) == (None, None)


def test_format_seconds():
    assert format_seconds(0) == "0:00"
    assert format_seconds(605) == "10:05"
    assert format_seconds(None) == "-:--"


def test_parse_status_with_ansi_noise():
    raw = (
        "\x1b[1m\x1b[32mSpotify is currently paused.\x1b(B\x1b[m\n"
        "Artist: Debbie Check\nAlbum: The March\nTrack: The March \n"
        "Position: 1:26 / 2:43"
    )
    clean = ANSI_ESCAPE.sub("", raw)
    status = parse_status(clean)
    assert status == {
        "state": "paused",
        "artist": "Debbie Check",
        "album": "The March",
        "track": "The March",
        "position": "1:26 / 2:43",
    }


def test_ansi_strip_protects_volume_digits():
    raw = "\x1b[1m\x1b[32mCurrent Spotify volume level is 100.\x1b(B\x1b[m"
    digits = "".join(c for c in ANSI_ESCAPE.sub("", raw) if c.isdigit())
    assert digits == "100"
