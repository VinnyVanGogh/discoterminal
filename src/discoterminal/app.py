"""Textual TUI for controlling Spotify via shpotify + the Web API."""

import io
import json
import re
import urllib.request

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.theme import Theme
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    Static,
)

from discoterminal import lyrics, player, playlists, spotify, webapi
from discoterminal.screens import PickerScreen
from discoterminal.visualizer import PALETTES, CavaVisualizer

SETUP_TEXT = """\
[bold]👋 Welcome to discoterminal — one-time setup[/bold]

No Spotify credentials found. To connect your account:

[bold]1.[/bold] Create an app at [u]developer.spotify.com/dashboard[/u]
   (Web API checkbox greyed out? Create the app without it,
    then Edit the app and add Web API there.)
[bold]2.[/bold] Add redirect URI: [u]http://127.0.0.1:8888/callback[/u]
[bold]3.[/bold] Put your Client ID in [u]~/.config/discoterminal/config.json[/u]:
   {"client_id": "your-client-id"}
[bold]4.[/bold] Restart discoterminal — a browser opens once to log in.

[dim]macOS: `brew install shpotify` also enables local control
without any of the above (playlists/search still need the API).[/dim]"""


def _palette_theme(name, colors):
    """A full app Theme derived from a visualizer palette (bottom -> top)."""
    return Theme(
        name=f"viz-{name}",
        primary=colors[2],
        secondary=colors[1],
        accent=colors[4],
        success=colors[0],
        warning=colors[-2],
        error="#f43f5e",
        dark=True,
    )

def _art_widget_class():
    """Album-art widget class, honoring "art_renderer" in config.json.

    Values: auto (default) | sixel | tgp | halfcell | unicode.
    halfcell/unicode are pure text — use them if the terminal's graphics
    protocol misbehaves.
    """
    try:
        from textual_image import widget as tiw
    except ImportError:
        return None
    try:
        import json

        choice = json.loads(webapi.CONFIG_FILE.read_text()).get("art_renderer", "auto")
    except (OSError, ValueError, AttributeError):
        choice = "auto"
    return {
        "auto": tiw.Image,
        "sixel": tiw.SixelImage,
        "tgp": tiw.TGPImage,
        "halfcell": tiw.HalfcellImage,
        "unicode": tiw.UnicodeImage,
    }.get(choice, tiw.Image)


try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore[assignment]

AlbumArt = _art_widget_class()

VOLUME_BAR_LENGTH = 20
STATUS_POLL_SECONDS = 2.0
NARROW_WIDTH = 90
POSITION_RE = re.compile(r"(\d+):(\d{2})\s*/\s*(\d+):(\d{2})")

# Commands handed straight to shpotify when given as startup args;
# anything else is treated as a playlist name.
PASSTHROUGH_COMMANDS = {
    "play", "pause", "next", "prev", "replay", "pos",
    "vol", "status", "share", "toggle", "stop", "quit",
}


def parse_position(text):
    """'1:26 / 2:43' -> (86, 163) seconds, or (None, None)."""
    match = POSITION_RE.search(text or "")
    if not match:
        return None, None
    m1, s1, m2, s2 = (int(g) for g in match.groups())
    return m1 * 60 + s1, m2 * 60 + s2


def format_seconds(seconds):
    if seconds is None:
        return "-:--"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _fetch_image(url):
    """Download an image into a PIL image; None on any failure."""
    if not url or PILImage is None:
        return None
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return PILImage.open(io.BytesIO(response.read()))
    except Exception:
        return None


class DiscoTerminal(App):
    TITLE = "🪩 Disco Terminal"

    CSS = """
    #body {
        height: 1fr;
    }
    #sidebar {
        width: 28;
        border: round $accent;
        padding: 0 1;
    }
    #sidebar-title {
        text-style: bold;
        color: $accent;
    }
    DiscoTerminal.narrow #sidebar {
        display: none;
    }
    #main {
        padding: 0 1;
    }
    #now-playing-row {
        border: round $success;
        padding: 1 2;
        height: 19;
    }
    DiscoTerminal.no-viz #now-playing-row {
        height: 1fr;
    }
    #album-art {
        width: 30;
        height: 15;
        margin-right: 2;
    }
    DiscoTerminal.narrow #album-art {
        display: none;
    }
    #now-playing {
        width: 1fr;
    }
    #btn-flip {
        dock: right;
        min-width: 12;
        margin-left: 1;
    }
    #progress-row {
        height: 1;
        margin: 0 1;
    }
    #time-elapsed, #time-total {
        width: 7;
        color: $text-muted;
    }
    #time-total {
        text-align: right;
    }
    #track-progress {
        width: 1fr;
    }
    #track-progress Bar {
        width: 1fr;
    }
    #controls {
        height: 3;
        align: center middle;
    }
    #controls Button {
        margin: 0 1;
        min-width: 8;
    }
    #search {
        margin: 0 1 1 1;
    }
    #viz {
        height: 1fr;
        min-height: 3;
        margin: 0 1;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("space", "play_pause", "Play/Pause"),
        Binding("n", "next", "Next"),
        Binding("p", "prev", "Prev"),
        Binding("r", "replay", "Replay", show=False),
        Binding("plus,equals_sign", "vol_up", "Vol +"),
        Binding("minus", "vol_down", "Vol -"),
        Binding("s", "shuffle", "Shuffle", show=False),
        Binding("t", "repeat", "Repeat", show=False),
        Binding("l", "like", "♥ Like"),
        Binding("d", "devices", "Devices"),
        Binding("b", "toggle_sidebar", "Sidebar"),
        Binding("v", "toggle_viz", "Visualizer", show=False),
        Binding("V", "viz_style", "Viz style"),
        Binding("c", "viz_colors", "🎨 Colors"),
        Binding("i", "flip_card", "Artist info"),
        Binding("u", "show_queue", "Queue"),
        Binding("y", "show_lyrics_card", "Lyrics"),
        Binding("left_square_bracket", "lyrics_earlier", show=False),
        Binding("right_square_bracket", "lyrics_later", show=False),
        Binding("slash", "focus_search", "Search"),
        Binding("escape", "blur_search", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, startup_args=None):
        super().__init__()
        self.startup_args = list(startup_args or [])
        self.last_state = None  # "playing" / "paused" / None
        self.playlist_entries = []  # [(name, uri)] in sidebar order
        self.pending_playlist = None  # startup arg waiting for playlist load
        self.elapsed = None  # seconds into current track
        self.total = None  # track length in seconds
        self.track_key = None  # (artist, track) for change detection
        self.track_id = None  # Spotify ID of current track
        self.saved = None  # True/False/None(unknown) — Liked Songs state
        self.card_face = "playing"  # "playing" | "artist" | "lyrics"
        self.lyrics_synced = None  # [(seconds, line)] for the current track
        self.lyrics_plain = None  # plain-text fallback
        self.lyrics_for_key = None  # (artist, track) the lyrics belong to
        self._lyrics_index = None  # last rendered synced-line index
        try:
            self.lyrics_offset = float(
                json.loads(webapi.CONFIG_FILE.read_text()).get("lyrics_offset", 0.0)
            )
        except (OSError, ValueError, TypeError):
            self.lyrics_offset = 0.0
        self.needs_setup = False  # true when no credentials and no local CLI
        self.palette_name = "aurora"  # synced with visualizer palette on mount
        self._track_art = None  # PIL image of current track's cover
        self._artist_cache = {}  # artist id -> (info dict, PIL image)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Static("Playlists (loading…)", id="sidebar-title")
                yield ListView(id="playlist-list")
            with Vertical(id="main"):
                with Horizontal(id="now-playing-row"):
                    if AlbumArt is not None:
                        yield AlbumArt(id="album-art")
                    yield Static("Loading status…", id="now-playing")
                    yield Button("ℹ artist", id="btn-flip")
                yield CavaVisualizer(id="viz")
                with Horizontal(id="progress-row"):
                    yield Static("-:--", id="time-elapsed")
                    yield ProgressBar(
                        id="track-progress",
                        show_percentage=False,
                        show_eta=False,
                    )
                    yield Static("-:--", id="time-total")
                with Horizontal(id="controls"):
                    yield Button("⏮ prev", id="btn-prev")
                    yield Button("⏯ play/pause", id="btn-playpause")
                    yield Button("⏭ next", id="btn-next")
                    yield Button("🔀 shuffle", id="btn-shuffle")
                    yield Button("🔁 repeat", id="btn-repeat")
                yield Input(
                    placeholder="Search anything — tracks, albums, playlists, artists…",
                    id="search",
                )
        yield Footer()

    def on_mount(self) -> None:
        for name, colors in PALETTES.items():
            self.register_theme(_palette_theme(name, colors))
        self.apply_palette(self.query_one("#viz", CavaVisualizer).palette_name)

        # First run: Web API backend selected but no credentials — show
        # the setup checklist instead of polling into "unreachable".
        backend = player.get_backend()
        if backend.name == "webapi" and not webapi.configured():
            self.needs_setup = True
            self.query_one("#now-playing", Static).update(SETUP_TEXT)
            return

        self.set_interval(STATUS_POLL_SECONDS, self.refresh_status)
        self.set_interval(1.0, self.tick_position)
        # Sixel/TGP art can get clobbered by other repaints (iTerm2);
        # a periodic refresh re-emits it so it never stays gone.
        if AlbumArt is not None:
            self.set_interval(5.0, self._refresh_art)
        self.refresh_status()
        self.load_playlists()
        if self.startup_args:
            self.dispatch_startup(self.startup_args)

    def on_resize(self, event) -> None:
        self.set_class(event.size.width < NARROW_WIDTH, "narrow")

    def dispatch_startup(self, args: list[str]) -> None:
        head = args[0]
        if head in player.ACTIONS:
            self.run_player(head)
        elif head in PASSTHROUGH_COMMANDS:
            if player.get_backend().name == "shpotify":
                self.run_spotify(*args)
            else:
                self.notify(
                    f"Startup command {head!r} needs shpotify (macOS)",
                    severity="warning",
                )
        else:
            # Playlist name — played once the sidebar has loaded.
            self.pending_playlist = " ".join(args)

    # ---- background work -------------------------------------------------

    @work(thread=True, exclusive=True, group="playlists")
    def load_playlists(self) -> None:
        # May block on first-run OAuth (browser login) — thread keeps UI live.
        loaded, source, error = playlists.get_playlists()
        self.call_from_thread(self.populate_sidebar, loaded, source, error)

    @work(thread=True, exclusive=True, group="status")
    def refresh_status(self) -> None:
        if self.needs_setup:
            return
        status = player.get_backend().status()
        volume = status.pop("volume", None) if status else None
        self.call_from_thread(self.render_now_playing, status, volume)
        if self.card_face == "lyrics":
            # Millisecond-accurate resync — local CLIs round to whole
            # seconds and can lag, which drags the highlighted line behind.
            try:
                progress = (webapi.current_playback() or {}).get("progress_ms")
            except Exception:
                progress = None
            if progress is not None:
                self.call_from_thread(self.set_precise_position, progress / 1000)

    def set_precise_position(self, seconds: float) -> None:
        self.elapsed = seconds
        self.update_progress()
        if self.card_face == "lyrics":
            self.render_lyrics_card()

    @work(thread=True, group="commands")
    def run_player(self, action: str) -> None:
        """Run a standard playback action on the active backend."""
        try:
            player.get_backend().command(action)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")
        self.call_from_thread(self.refresh_status)

    @work(thread=True, group="commands")
    def run_spotify(self, *args) -> None:
        """Raw shpotify passthrough (macOS only) — used by startup args."""
        result = spotify.run(*args)
        if not result.ok:
            self.call_from_thread(
                self.notify,
                result.output or f"spotify {' '.join(args)} failed",
                severity="error",
            )
        self.call_from_thread(self.refresh_status)

    @work(thread=True, exclusive=True, group="track-details")
    def sync_track_details(self) -> None:
        """Web API details for the current track: id, saved state, album art."""
        try:
            track = webapi.current_track()
            saved = webapi.is_saved(track["id"]) if track and track["id"] else None
        except Exception:
            return
        art = _fetch_image(track.get("art_url")) if track else None
        self.call_from_thread(self.apply_track_details, track, saved, art)

    @work(thread=True, exclusive=True, group="artist-info")
    def load_artist_info(self) -> None:
        try:
            info = webapi.current_artist_info()
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        if not info:
            self.call_from_thread(
                self.notify, "No artist info available", severity="warning"
            )
            return
        cached = self._artist_cache.get(info["id"])
        image = cached[1] if cached else _fetch_image(info.get("image_url"))
        self._artist_cache[info["id"]] = (info, image)
        self.call_from_thread(self.render_artist_card, info, image)

    @work(thread=True, exclusive=True, group="search")
    def run_search(self, query) -> None:
        try:
            results = webapi.search(query)
        except Exception as e:
            # No Web API? Fall back to shpotify's own search-and-play.
            self.call_from_thread(
                self.notify, f"Search API unavailable ({e}); playing best match",
                severity="warning",
            )
            self.call_from_thread(self.run_spotify, "play", *query.split())
            return
        if not results:
            self.call_from_thread(
                self.notify, f"No results for {query!r}", severity="warning"
            )
            return
        options = [(r["label"], r["uri"]) for r in results]
        self.call_from_thread(self.show_picker, f"Results for {query!r}", options,
                              self.play_uri)

    @work(thread=True, exclusive=True, group="queue")
    def load_queue(self) -> None:
        try:
            upcoming = webapi.queue()
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        if not upcoming:
            self.call_from_thread(self.notify, "Queue is empty", severity="warning")
            return
        options = [(item["label"], item["uri"]) for item in upcoming]
        self.call_from_thread(
            self.show_picker, "Up next (enter plays directly)", options, self.play_uri
        )

    @work(thread=True, exclusive=True, group="lyrics")
    def load_lyrics(self) -> None:
        artist, track = self.track_key or (None, None)
        if not artist or not track:
            self.call_from_thread(self.notify, "Nothing playing", severity="warning")
            return
        try:
            synced, plain = lyrics.get_synced(artist, track, self.total)
        except Exception as e:
            self.call_from_thread(self.notify, f"Lyrics lookup failed: {e}",
                                  severity="error")
            synced, plain = None, None  # resolve the "Fetching…" state
        self.lyrics_synced = synced
        self.lyrics_plain = plain
        self.lyrics_for_key = (artist, track)
        self._lyrics_index = None
        try:
            progress = (webapi.current_playback() or {}).get("progress_ms")
        except Exception:
            progress = None
        if progress is not None:
            self.call_from_thread(self.set_precise_position, progress / 1000)
        else:
            self.call_from_thread(self.render_lyrics_card)

    @work(thread=True, exclusive=True, group="seek")
    def seek_to(self, seconds) -> None:
        try:
            webapi.seek(seconds)
        except Exception:
            try:
                player.get_backend().seek(seconds)
            except Exception:
                self.call_from_thread(self.notify, "Seek failed", severity="error")
                return
        self.elapsed = int(seconds)
        self.call_from_thread(self.update_progress)

    @work(thread=True, exclusive=True, group="devices")
    def load_devices(self) -> None:
        try:
            found = webapi.devices()
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        if not found:
            self.call_from_thread(
                self.notify, "No Spotify devices found", severity="warning"
            )
            return
        options = [
            (f"{'● ' if d['is_active'] else '  '}{d['name']} ({d['type']})", d["id"])
            for d in found
        ]
        self.call_from_thread(self.show_picker, "Play on device", options,
                              self.transfer_device)

    @work(thread=True, exclusive=True, group="like")
    def toggle_like(self) -> None:
        if not self.track_id:
            self.call_from_thread(
                self.notify, "No current track to like", severity="warning"
            )
            return
        try:
            saved = webapi.toggle_saved(self.track_id)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        self.saved = saved
        message = "♥ Added to Liked Songs" if saved else "♡ Removed from Liked Songs"
        self.call_from_thread(self.notify, message)
        self.call_from_thread(self.refresh_status)

    @work(thread=True, exclusive=True, group="transfer")
    def transfer_playback(self, device_id) -> None:
        try:
            webapi.transfer(device_id)
            self.call_from_thread(self.notify, "Playback transferred")
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    # ---- rendering --------------------------------------------------------

    def populate_sidebar(self, loaded, source, error) -> None:
        self.playlist_entries = list(loaded.items())
        list_view = self.query_one("#playlist-list", ListView)
        list_view.clear()
        for i, (name, _uri) in enumerate(self.playlist_entries):
            list_view.append(ListItem(Label(name, markup=False), id=f"pl-{i}"))

        title = self.query_one("#sidebar-title", Static)
        if source == "spotify":
            title.update(f"Playlists ({len(self.playlist_entries)})")
        else:
            title.update(f"Playlists (local, {len(self.playlist_entries)})")
            self.notify(
                f"Using local playlist fallback: {error}",
                severity="warning",
                timeout=10,
            )

        if self.pending_playlist:
            self.play_playlist_by_name(self.pending_playlist)
            self.pending_playlist = None

    def play_playlist_by_name(self, name) -> None:
        wanted = name.lower()
        for entry_name, uri in self.playlist_entries:
            if entry_name.lower() == wanted:
                self.play_uri(uri)
                self.notify(f"Playing playlist: {entry_name}")
                return
        self.notify(f"No playlist named {name!r}", severity="error")

    def render_now_playing(self, status, volume) -> None:
        try:
            self._render_now_playing(status, volume)
        except NoMatches:
            pass  # widgets already unmounted (app shutting down)

    def _render_now_playing(self, status, volume) -> None:
        # Track state/progress/track-change always update, even while the
        # card shows the artist face — only the panel text is skipped then.
        if status is not None:
            self.last_state = status.get("state", self.last_state)
            elapsed, total = parse_position(status.get("position"))
            if elapsed is not None:
                self.elapsed, self.total = elapsed, total
                self.update_progress()
            key = (status.get("artist"), status.get("track"))
            if key != self.track_key and key != (None, None):
                self.track_key = key
                self.saved = None
                self.sync_track_details()
                if self.card_face == "artist":
                    self.load_artist_info()
                elif self.card_face == "lyrics":
                    self.query_one("#now-playing", Static).update("Loading lyrics…")
                    self.load_lyrics()

        if self.card_face != "playing":
            return

        panel = self.query_one("#now-playing", Static)
        if status is None:
            panel.update(
                "[bold red]Spotify unreachable[/bold red]\n\n"
                "Is the Spotify app running?"
            )
            self.last_state = None
            return

        state_icon = "▶ playing" if self.last_state == "playing" else "⏸ paused"

        if self.saved is True:
            heart = " [red]♥[/red]"
        elif self.saved is False:
            heart = " [dim]♡[/dim]"
        else:
            heart = ""

        colors = PALETTES[self.palette_name]
        lines = [f"[bold]{state_icon}[/bold]{heart}\n"]
        for icon, dict_key, style in (
            ("🎤 Artist", "artist", colors[0]),
            ("💿 Album", "album", colors[2]),
            ("🎵 Track", "track", colors[4]),
            ("🔀 Shuffle", "shuffle", colors[1]),
            ("🔁 Repeat", "repeat", colors[3]),
        ):
            if dict_key in status:
                lines.append(
                    f"[bold {style}]{icon}:[/bold {style}] "
                    f"[{style}]{status[dict_key]}[/{style}]"
                )

        if volume is not None:
            filled = int(volume / 100 * VOLUME_BAR_LENGTH)
            bar = "█" * filled + "░" * (VOLUME_BAR_LENGTH - filled)
            lines.append(f"\n🔊 [{colors[2]}]{bar}[/{colors[2]}] {volume}%")

        panel.update("\n".join(lines))

    def apply_track_details(self, track, saved, art) -> None:
        self.track_id = track["id"] if track else None
        self.saved = saved
        self._track_art = art
        if self.card_face in ("playing", "lyrics"):
            # artist face keeps the artist photo; every other face shows
            # the current track's cover
            self._set_art(art, retries=6)

    def render_artist_card(self, info, image) -> None:
        if self.card_face != "artist":
            return  # user flipped back while we were fetching
        colors = PALETTES[self.palette_name]
        lines = [f"[bold {colors[4]}]🎤 {info['name']}[/bold {colors[4]}]\n"]
        if info.get("genres"):
            lines.append(f"[bold {colors[2]}]🏷 Genres:[/bold {colors[2]}] {', '.join(info['genres'][:4])}")
        if info.get("followers") is not None:
            lines.append(f"[bold {colors[1]}]👥 Followers:[/bold {colors[1]}] {info['followers']:,}")
        if info.get("popularity") is not None:
            lines.append(f"[bold {colors[3]}]🔥 Popularity:[/bold {colors[3]}] {info['popularity']}/100")
        if info.get("top_tracks"):
            lines.append("\n[bold]Top tracks[/bold]")
            for i, name in enumerate(info["top_tracks"], 1):
                lines.append(f"  {i}. {name}")
        self.query_one("#now-playing", Static).update("\n".join(lines))
        self._set_art(image, retries=6)

    def action_flip_card(self) -> None:
        if self.card_face == "artist":
            self._show_playing_face()
        else:
            self.card_face = "artist"
            self.query_one("#btn-flip", Button).label = "🎵 playing"
            self.query_one("#now-playing", Static).update("Loading artist info…")
            self.load_artist_info()

    def action_show_lyrics_card(self) -> None:
        if self.card_face == "lyrics":
            self._show_playing_face()
            return
        self.card_face = "lyrics"
        self.query_one("#btn-flip", Button).label = "🎵 playing"
        self._set_art(self._track_art, retries=6)  # in case artist photo was up
        if self.lyrics_for_key == self.track_key and (
            self.lyrics_synced or self.lyrics_plain
        ):
            self.render_lyrics_card()
        else:
            self.query_one("#now-playing", Static).update("Loading lyrics…")
            self.load_lyrics()

    def _show_playing_face(self) -> None:
        self.card_face = "playing"
        self.query_one("#btn-flip", Button).label = "ℹ artist"
        self._set_art(self._track_art, retries=6)
        self.refresh_status()

    def render_lyrics_card(self) -> None:
        if self.card_face != "lyrics":
            return
        panel = self.query_one("#now-playing", Static)
        if self.lyrics_for_key != self.track_key:
            # fetch for this track hasn't landed yet — never claim "no lyrics"
            panel.update("[dim]Fetching lyrics…[/dim]")
            return
        colors = PALETTES[self.palette_name]
        artist, track = self.track_key or ("", "")

        if self.lyrics_synced:
            index = self._current_lyric_index()
            self._lyrics_index = index
            window = 11  # lines shown
            lines = [f"[bold {colors[4]}]🎤 {track}[/bold {colors[4]}]\n"]
            start = max((index or 0) - 3, 0)
            for i in range(start, min(start + window, len(self.lyrics_synced))):
                _stamp, text = self.lyrics_synced[i]
                text = text or "♪"
                if i == index:
                    lines.append(
                        f"[bold black on {colors[2]}] ▶ {text} [/bold black on {colors[2]}]"
                    )
                else:
                    lines.append(f"[dim]   {text}[/dim]")
            panel.update("\n".join(lines))
        elif self.lyrics_plain:
            body = "\n".join(self.lyrics_plain.splitlines()[:11])
            panel.update(
                f"[bold {colors[4]}]🎤 {track}[/bold {colors[4]}] "
                f"[dim](no sync available)[/dim]\n\n{body}"
            )
        else:
            panel.update(f"[dim]No lyrics found for {track}[/dim]")

    def _current_lyric_index(self) -> int | None:
        """Index of the synced line matching the playback position."""
        if not self.lyrics_synced or self.elapsed is None:
            return None
        position = self.elapsed + self.lyrics_offset
        index = None
        for i, (stamp, _text) in enumerate(self.lyrics_synced):
            if stamp <= position:
                index = i
            else:
                break
        return index

    def _nudge_lyrics(self, delta: float) -> None:
        if self.card_face != "lyrics":
            return
        from discoterminal.visualizer import _save_config_value

        self.lyrics_offset = round(self.lyrics_offset + delta, 2)
        _save_config_value("lyrics_offset", self.lyrics_offset)
        self.notify(f"Lyrics sync offset: {self.lyrics_offset:+.1f}s")
        self.render_lyrics_card()

    def _refresh_art(self) -> None:
        try:
            self.query_one("#album-art").refresh()
        except NoMatches:
            pass

    def _set_art(self, art, retries=0) -> None:
        """Apply album art, retrying while the widget hasn't been laid out yet.

        Setting the image before the first layout completes caches an
        empty render (0x0), which is why the first track's art never
        appeared until a track change re-set it.
        """
        if AlbumArt is None:
            return
        widget = self.query_one("#album-art")
        if widget.size.width == 0 and retries > 0:
            self.set_timer(0.5, lambda: self._set_art(art, retries - 1))
            return
        widget.image = art  # type: ignore[attr-defined]

    def update_progress(self) -> None:
        try:
            bar = self.query_one("#track-progress", ProgressBar)
        except NoMatches:
            return  # app shutting down
        if self.total:
            bar.update(total=self.total, progress=min(self.elapsed or 0, self.total))
        self.query_one("#time-elapsed", Static).update(format_seconds(self.elapsed))
        self.query_one("#time-total", Static).update(format_seconds(self.total))

    def tick_position(self) -> None:
        if self.last_state == "playing" and self.elapsed is not None and self.total:
            self.elapsed = min(self.elapsed + 1, self.total)
            self.update_progress()
            if (
                self.card_face == "lyrics"
                and self.lyrics_synced
                and self._current_lyric_index() != self._lyrics_index
            ):
                self.render_lyrics_card()

    def show_picker(self, title, options, on_pick) -> None:
        def handle(value):
            if value is not None:
                on_pick(value)

        self.push_screen(PickerScreen(title, options), handle)

    def apply_palette(self, name) -> None:
        """Retheme the whole app to match a visualizer palette."""
        if name not in PALETTES:
            name = "aurora"
        self.palette_name = name
        self.theme = f"viz-{name}"
        if self.is_running:
            self.refresh_status()  # repaint panel text in the new colors now

    def play_uri(self, uri) -> None:
        self._play_uri_worker(uri)

    @work(thread=True, group="commands")
    def _play_uri_worker(self, uri) -> None:
        try:
            webapi.play(uri)  # Web API: keeps focus on the terminal
        except Exception as e:
            if player.get_backend().name == "shpotify":
                # No active device / API hiccup — shpotify can wake Spotify
                # up (this path may briefly focus the Spotify app).
                result = spotify.run("play", "uri", uri)
                if not result.ok:
                    self.call_from_thread(
                        self.notify, result.output or "play failed", severity="error"
                    )
            else:
                self.call_from_thread(self.notify, str(e), severity="error")
        self.call_from_thread(self.refresh_status)

    def transfer_device(self, device_id) -> None:
        self.transfer_playback(device_id)

    # ---- actions ----------------------------------------------------------

    def action_play_pause(self) -> None:
        self.run_player("pause" if self.last_state == "playing" else "play")

    def action_next(self) -> None:
        self.run_player("next")

    def action_prev(self) -> None:
        self.run_player("prev")

    def action_replay(self) -> None:
        self.run_player("replay")

    def action_vol_up(self) -> None:
        self.run_player("vol_up")

    def action_vol_down(self) -> None:
        self.run_player("vol_down")

    def action_shuffle(self) -> None:
        self.run_player("shuffle")

    def action_repeat(self) -> None:
        self.run_player("repeat")

    def action_like(self) -> None:
        self.toggle_like()

    def action_devices(self) -> None:
        self.load_devices()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_toggle_viz(self) -> None:
        viz = self.query_one("#viz")
        viz.display = not viz.display

    def action_viz_style(self) -> None:
        from discoterminal.visualizer import STYLES

        viz = self.query_one("#viz", CavaVisualizer)
        options = [
            (("● " if s == viz.style_name else "  ") + s, s) for s in STYLES
        ]

        def apply(style):
            viz.set_style(style)
            self.notify(f"Visualizer style: {style}")

        self.show_picker("Visualizer style", options, apply)

    def action_viz_colors(self) -> None:
        from discoterminal.visualizer import PALETTES

        viz = self.query_one("#viz", CavaVisualizer)
        options = []
        for name, colors in PALETTES.items():
            mark = "●" if name == viz.palette_name else " "
            swatch = "".join(f"[{color}]█[/]" for color in colors)
            options.append((f"{mark} {swatch} {name}", name))

        def apply(name):
            viz.set_palette(name)
            self.apply_palette(name)
            self.notify(f"Theme: {name}")

        self.push_screen(
            PickerScreen("Visualizer colors", options, markup=True),
            lambda v: apply(v) if v is not None else None,
        )

    def action_show_queue(self) -> None:
        self.load_queue()

    def action_lyrics_earlier(self) -> None:
        self._nudge_lyrics(-0.5)

    def action_lyrics_later(self) -> None:
        self._nudge_lyrics(0.5)

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_blur_search(self) -> None:
        self.set_focus(None)

    # ---- events -----------------------------------------------------------

    def on_click(self, event: events.Click) -> None:
        """Click on the progress bar seeks to that position."""
        if not self.total:
            return
        bar = self.query_one("#track-progress", ProgressBar)
        region = bar.region
        if not region.contains(event.screen_x, event.screen_y):
            return
        fraction = (event.screen_x - region.x) / max(region.width, 1)
        self.seek_to(min(max(fraction, 0.0), 1.0) * self.total)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "btn-prev": self.action_prev,
            "btn-playpause": self.action_play_pause,
            "btn-next": self.action_next,
            "btn-shuffle": self.action_shuffle,
            "btn-repeat": self.action_repeat,
            "btn-flip": self.action_flip_card,
        }
        action = actions.get(event.button.id or "")
        if action:
            action()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index_str = (event.item.id or "").removeprefix("pl-")
        if not index_str.isdigit():
            return
        index = int(index_str)
        if index < len(self.playlist_entries):
            name, uri = self.playlist_entries[index]
            self.play_uri(uri)
            self.notify(f"Playing playlist: {name}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self.set_focus(None)
        self.run_search(text)
