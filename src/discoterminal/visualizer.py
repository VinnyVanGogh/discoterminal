"""Embedded cava audio visualizer.

Runs `cava` in raw ascii mode and renders its bars as a multi-row wave/bar
display. Hidden automatically when cava is not installed. Shows a hint when
cava runs but only reports silence (macOS needs a loopback device such as
BlackHole to feed system audio into an input).

Render styles (cycle in-app): bars, mirror, wave. Choice persists in
~/.config/spotify_player/config.json under "visualizer_style".
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from textual.widgets import Static

from discoterminal import webapi

BLOCKS = " ▁▂▃▄▅▆▇█"
STYLES = ("area", "bars", "mirror", "peaks", "outline", "dots", "led", "rain")
BAR_COUNT = 100
MAX_RANGE = 8
SILENT_FRAMES_FOR_HINT = 120  # ~10s at 12fps
PEAK_FALL = 0.35  # cells per frame the peak caps drop
CAP = "\x00"  # placeholder swapped for a white cap during colorize

# palettes run bottom -> top
PALETTES = {
    "aurora": ("#22c55e", "#10b981", "#06b6d4", "#6366f1", "#a855f7", "#ec4899"),
    "synthwave": ("#2d00f7", "#8900f2", "#bc00dd", "#e500a4", "#f20089", "#ff5fd2"),
    "matrix": ("#003b00", "#008f11", "#00ff41", "#7dff9b", "#c8ffd4", "#eaffef"),
    "fire": ("#7f1d1d", "#dc2626", "#f97316", "#fbbf24", "#fde68a", "#fffbeb"),
    "ocean": ("#0c4a6e", "#0369a1", "#0284c7", "#38bdf8", "#7dd3fc", "#e0f2fe"),
    "mono": ("#3f3f46", "#71717a", "#a1a1aa", "#d4d4d8", "#e4e4e7", "#fafafa"),
    "sunset": ("#4c1d95", "#7c3aed", "#db2777", "#f97316", "#fbbf24", "#fef08a"),
    "vaporwave": ("#01cdfe", "#05ffa1", "#b967ff", "#ff71ce", "#ff9de6", "#fffb96"),
    "rainbow": ("#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6", "#a855f7"),
    "ice": ("#1e3a8a", "#1d4ed8", "#3b82f6", "#93c5fd", "#dbeafe", "#ffffff"),
    "lava": ("#18181b", "#450a0a", "#991b1b", "#ea580c", "#facc15", "#fef9c3"),
    "candy": ("#be185d", "#ec4899", "#f472b6", "#f9a8d4", "#fbcfe8", "#fdf2f8"),
    "gold": ("#451a03", "#92400e", "#d97706", "#f59e0b", "#fbbf24", "#fef3c7"),
    "cyberpunk": ("#0ff0fc", "#00b8d4", "#7b2ff7", "#d600ff", "#ff2079", "#fdf500"),
}
DEFAULT_PALETTE = "aurora"

CAVA_CONFIG = f"""
[general]
bars = {BAR_COUNT}
framerate = 12

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = {MAX_RANGE}

[smoothing]
monstercat = 1
noise_reduction = 77
"""

CAVA_INPUT_BLACKHOLE = """
[input]
method = portaudio
source = "BlackHole 2ch"
"""


def blackhole_present() -> bool:
    """True when the BlackHole loopback device is registered with CoreAudio.

    macOS only — Linux (PulseAudio monitor) and Windows (WASAPI loopback)
    give cava system audio natively, no loopback driver needed.
    """
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["system_profiler", "SPAudioDataType"],
            capture_output=True, text=True, timeout=10,
        )
        return "BlackHole" in result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def cava_available() -> bool:
    return shutil.which("cava") is not None


def _load_config_value(key, valid, default):
    try:
        value = json.loads(webapi.CONFIG_FILE.read_text()).get(key)
        return value if value in valid else default
    except (OSError, json.JSONDecodeError, AttributeError):
        return default


def _save_config_value(key, value):
    try:
        config = json.loads(webapi.CONFIG_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        config = {}
    config[key] = value
    webapi.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    webapi.CONFIG_FILE.write_text(json.dumps(config, indent=2))


def load_style() -> str:
    return _load_config_value("visualizer_style", STYLES, STYLES[0])


def save_style(style: str) -> None:
    _save_config_value("visualizer_style", style)


def load_palette() -> str:
    return _load_config_value("visualizer_colors", PALETTES, DEFAULT_PALETTE)


def save_palette(name: str) -> None:
    _save_config_value("visualizer_colors", name)


def _sample(values: list[int], width: int) -> list[int]:
    """Resample values to exactly `width` columns."""
    if width <= 0 or not values:
        return []
    step = len(values) / width
    return [values[min(int(i * step), len(values) - 1)] for i in range(width)]


def _cell(fill: float) -> str:
    """Block character for a cell that is `fill` (0..1+) covered from below."""
    if fill >= 1:
        return "█"
    if fill <= 0:
        return " "
    return BLOCKS[max(int(fill * 8), 1)]


def _grid(levels: list[float], height: int, gap_every: int = 0) -> list[list[str]]:
    """Bottom-up grid of block chars. levels are column heights in cells.

    Returns mutable rows (lists of chars), top row first. gap_every=3 leaves
    every third column blank for a classic equalizer look.
    """
    rows = []
    for row in range(height):
        below = height - 1 - row
        chars = []
        for x, level in enumerate(levels):
            if gap_every and x % gap_every == gap_every - 1:
                chars.append(" ")
            else:
                chars.append(_cell(level - below))
        rows.append(chars)
    return rows


def _colorize(rows: list[list[str]], height: int, gradient: tuple[str, ...]) -> str:
    """Wrap each row in its gradient color; CAP markers become white caps."""
    top_index = len(gradient) - 1
    out = []
    for row, chars in enumerate(rows):
        frac = 1 - row / max(height - 1, 1)  # 0 at bottom, 1 at top
        color = gradient[round(frac * top_index)]
        text = "".join(chars)
        if CAP in text:
            text = text.replace(CAP, f"[/][bold white]─[/][{color}]")
        out.append(f"[{color}]{text}[/]")
    return "\n".join(out)


RAVE_GAIN = 1.9  # bar-height multiplier on a beat
RAVE_DECAY = 0.88  # gain decay per frame back toward 1.0
RAVE_PHASE_STEP = 0.35  # sideways color-flow speed (bands per frame)


def _colorize_columns(rows, gradient, phase: float) -> str:
    """Color by column bands (not row) with a scrolling phase offset —
    the gradient flows sideways across the frame."""
    n = len(gradient)
    width = len(rows[0]) if rows else 0
    band_width = max(width // (n * 2), 1)
    out = []
    for chars in rows:
        parts = []
        for start in range(0, width, band_width):
            color = gradient[int(start / band_width + phase) % n]
            segment = "".join(chars[start:start + band_width])
            parts.append(f"[{color}]{segment}[/]")
        out.append("".join(parts))
    return "\n".join(out)


class SpectrumRenderer:
    """Stateful frame renderer (peak caps and rain drops persist between frames)."""

    def __init__(self):
        self._peaks = []
        self._drops = []  # [x, y, speed] falling droplets for the rain style
        self._rave_gain = 1.0  # beat slam, decays back to 1.0
        self._rave_phase = 0.0  # sideways color flow
        self._rave_flash = 0  # full-frame strobe frames remaining

    def trigger_beat(self) -> None:
        """A beat landed: slam the bars and strobe one full frame."""
        self._rave_gain = RAVE_GAIN
        self._rave_flash = 1

    def render_rave(self, cols, height, palette=DEFAULT_PALETTE) -> str:
        """Takeover renderer: 4-way kaleido blob + beat slam + strobe +
        flowing column colors. Independent of the user's chosen style."""
        gradient = PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])

        if self._rave_flash > 0:
            self._rave_flash -= 1
            row = "█" * len(cols)
            return "\n".join(
                f"[{gradient[-1]}]{row}[/]" for _ in range(height)
            )

        self._rave_gain = max(1.0, self._rave_gain * RAVE_DECAY)
        self._rave_phase += RAVE_PHASE_STEP

        # left half mirrored onto the right = horizontal symmetry
        half = cols[: max(len(cols) // 2, 1)]
        sym = half + half[::-1]
        sym = sym[: len(cols)] + [0] * (len(cols) - len(sym))

        # vertical symmetry: blob grows out from the center line
        half_height = max(height // 2, 1)
        levels = [
            min(v * self._rave_gain, MAX_RANGE) / MAX_RANGE * half_height
            for v in sym
        ]
        bottom = _grid(levels, half_height)
        rows = bottom[::-1] + ([[" "] * len(sym)] if height % 2 else []) + bottom
        return _colorize_columns(rows[:height], gradient, self._rave_phase)

    def render(self, cols, height, style, palette=DEFAULT_PALETTE):
        gradient = PALETTES.get(palette, PALETTES[DEFAULT_PALETTE])
        method = getattr(self, f"_style_{style}", self._style_area)
        rows = method(cols, height)
        return _colorize(rows, height, gradient)

    @staticmethod
    def _levels(cols, height):
        return [v / MAX_RANGE * height for v in cols]

    def _style_area(self, cols, height):
        return _grid(self._levels(cols, height), height)

    def _style_bars(self, cols, height):
        return _grid(self._levels(cols, height), height, gap_every=3)

    def _style_mirror(self, cols, height):
        half = max(height // 2, 1)
        levels = [v / MAX_RANGE * half for v in cols]
        bottom = _grid(levels, half)
        rows = bottom[::-1] + ([[" "] * len(cols)] if height % 2 else []) + bottom
        return rows[:height]

    def _style_peaks(self, cols, height):
        levels = self._levels(cols, height)
        gap = 3
        rows = _grid(levels, height, gap_every=gap)
        if len(self._peaks) != len(levels):
            self._peaks = [0.0] * len(levels)
        for x, level in enumerate(levels):
            self._peaks[x] = max(self._peaks[x] - PEAK_FALL, level)
            peak = self._peaks[x]
            if peak > 0.3 and x % gap != gap - 1:
                row = height - 1 - min(int(peak), height - 1)
                rows[row][x] = CAP
        return rows

    def _style_outline(self, cols, height):
        """Just the ridge line of the spectrum."""
        rows = [[" "] * len(cols) for _ in range(height)]
        for x, level in enumerate(self._levels(cols, height)):
            if level < 0.1:
                continue
            cell = min(int(level), height - 1)
            frac = level - cell
            rows[height - 1 - cell][x] = BLOCKS[max(int(frac * 8), 1)] if frac < 1 else "█"
        return rows

    def _style_dots(self, cols, height):
        """A dot per column tracing the curve."""
        rows = [[" "] * len(cols) for _ in range(height)]
        for x, v in enumerate(cols):
            y = height - 1 - min(int(v / MAX_RANGE * (height - 1) + 0.5), height - 1)
            rows[y][x] = "●" if v else "·"
        return rows

    def _style_led(self, cols, height):
        """Segmented LED meter: discrete half-block cells with gaps."""
        rows = []
        levels = self._levels(cols, height)
        for row in range(height):
            below = height - 1 - row
            chars = []
            for x, level in enumerate(levels):
                if x % 3 == 2:
                    chars.append(" ")
                else:
                    chars.append("▄" if level - below >= 0.4 else " ")
            rows.append(chars)
        return rows

    def _style_rain(self, cols, height):
        """Droplets fall onto a spectrum floor (~1/3 of the height)."""
        import random

        floor_rows = min(max(2, height // 3), height)
        sky = height - floor_rows
        levels = self._levels(cols, height)

        # advance + cull (also discard drops left stranded by a resize —
        # their x can exceed the new, narrower width)
        self._drops = [
            [x, y + speed, speed]
            for x, y, speed in self._drops
            if y + speed < sky and x < len(cols)
        ]
        # spawn from loud columns
        if len(self._drops) < len(cols):
            for x, level in enumerate(levels):
                loudness = level / max(height, 1)
                if loudness > 0.35 and random.random() < loudness * 0.15:
                    self._drops.append([x, 0.0, 0.4 + loudness * 0.6])

        rows = [[" "] * len(cols) for _ in range(height)]
        for x, y, _speed in self._drops:
            row = min(int(y), max(sky - 1, 0))
            rows[row][x] = "●"
            if row > 0:
                rows[row - 1][x] = "·"
        # floor: compressed spectrum
        floor_levels = [v / MAX_RANGE * floor_rows for v in cols]
        for i, chars in enumerate(_grid(floor_levels, floor_rows)):
            rows[sky + i] = chars
        return rows


BEAT_THRESHOLD = 1.4  # frame energy vs rolling average
BEAT_MIN_INTERVAL = 0.25  # seconds — caps flashes at 4/sec (photosensitivity)
BEAT_WINDOW = 24  # frames of rolling energy (~2s at 12fps)


class CavaVisualizer(Static):
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self._process = None
        self._silent_frames = 0
        self._renderer = SpectrumRenderer()
        self.style_name = load_style()
        self.palette_name = load_palette()
        self.on_beat = None  # set by the app; called on the UI thread
        self.overlay_title = None  # rave takeover: track name over the viz
        self.rave_takeover = False  # use the dedicated kaleido renderer
        self._energy_window: list[int] = []
        self._last_beat = 0.0

    def _check_beat(self, values, now: float) -> bool:
        """True when this frame's energy spikes above the rolling average.

        Rate-limited to one beat per BEAT_MIN_INTERVAL so strobing stays
        below photosensitivity-risk flash rates.
        """
        energy = sum(values)
        window = self._energy_window
        window.append(energy)
        if len(window) > BEAT_WINDOW:
            window.pop(0)
        if len(window) < 6:
            return False
        average = sum(window[:-1]) / (len(window) - 1)
        if average <= 0:
            return False
        if energy < average * BEAT_THRESHOLD:
            return False
        if now - self._last_beat < BEAT_MIN_INTERVAL:
            return False
        self._last_beat = now
        return True

    def on_mount(self) -> None:
        if not cava_available():
            self.display = False
            self.app.add_class("no-viz")
            return
        # start in a worker: the BlackHole probe (system_profiler) is slow
        self.run_worker(self.start_cava, thread=True, exclusive=True, group="cava")

    def cycle_style(self) -> str:
        """Switch to the next render style, persist it, return its name."""
        index = STYLES.index(self.style_name) if self.style_name in STYLES else 0
        self.style_name = STYLES[(index + 1) % len(STYLES)]
        save_style(self.style_name)
        return self.style_name

    def set_style(self, style) -> None:
        if style in STYLES:
            self.style_name = style
            save_style(style)

    def set_palette(self, name) -> None:
        if name in PALETTES:
            self.palette_name = name
            save_palette(name)

    def trigger_beat(self) -> None:
        self._renderer.trigger_beat()

    def start_cava(self) -> None:
        text = CAVA_CONFIG
        if blackhole_present():
            text += CAVA_INPUT_BLACKHOLE
        config = Path(tempfile.gettempdir()) / "spotify_player_cava.conf"
        config.write_text(text)
        try:
            self._process = subprocess.Popen(
                ["cava", "-p", str(config)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            self.app.call_from_thread(self._disable)
            return
        self._read_loop()

    def _disable(self) -> None:
        self.display = False
        self.app.add_class("no-viz")

    def _read_loop(self) -> None:
        process = self._process
        if not process or not process.stdout:
            return
        for line in process.stdout:
            if process.poll() is not None:
                break
            values = [int(v) for v in line.strip().split(";") if v.isdigit()]
            if not values:
                continue
            if any(values):
                self._silent_frames = 0
            else:
                self._silent_frames += 1
            if self.on_beat is not None and self._check_beat(values, time.monotonic()):
                self.app.call_from_thread(self.on_beat)
            self.app.call_from_thread(self.render_frame, values)

    def render_frame(self, values) -> None:
        if self._silent_frames > SILENT_FRAMES_FOR_HINT:
            self.update(
                "[dim]cava hears silence — route audio through a loopback "
                "device (e.g. BlackHole) to visualize Spotify[/dim]"
            )
            return
        width = self.content_size.width
        height = self.content_size.height
        if width < 2 or height < 1:
            return
        title_row = ""
        if self.overlay_title and height > 4:
            title = self.overlay_title[: max(width - 2, 0)]
            pad = max((width - len(title)) // 2, 0)
            title_row = " " * pad + title
            height -= 1
        cols = _sample(values, width)
        try:
            if self.rave_takeover:
                markup = self._renderer.render_rave(cols, height, self.palette_name)
            else:
                markup = self._renderer.render(
                    cols, height, self.style_name, self.palette_name
                )
        except Exception:
            return  # a bad frame must never take down the app
        if title_row:
            markup = f"[bold]{title_row}[/bold]\n{markup}"
        self.update(markup)

    def on_unmount(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
