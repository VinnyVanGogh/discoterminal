# spotui

A Spotify terminal UI for macOS. Album art in your terminal, a real-time audio
visualizer powered by [cava], full-app color theming, lyrics, and playback
control — without leaving your shell or focusing the Spotify window.

<!-- TODO: demo GIF — record with `vhs` or asciinema, drop here -->
<!-- ![demo](docs/demo.gif) -->

Built with [Textual]. Talks to Spotify two ways: the [shpotify] CLI
(AppleScript) for instant local control, and the Spotify Web API (OAuth PKCE)
for your library, search, devices, and queue.

## Features

- 🎨 **Now playing card** with album art (sixel/TGP/halfcell), live progress
  bar, and click-to-seek
- 📊 **Audio visualizer** — embedded cava, 8 render styles (area, bars,
  mirror, peaks, outline, dots, led, rain), 14 color palettes
- 🌈 **Whole-app theming** — pick a palette and every border, button, and
  label recolors to match
- 🔀 **Card flip** — artist info (genres, followers, popularity, top tracks)
  with artist photo
- 📻 **Your playlists** in a collapsible sidebar, fetched live from your
  account
- 🔍 **Search anything** — tracks, albums, playlists, artists — pick from a
  results modal
- 🎤 **Lyrics** via [lrclib.net] (no API key)
- ♥ **Like/unlike** the current track, ⏭ **queue viewer**, 📱 **device
  switcher**
- ⌨️ Everything keyboard-driven; playback via Web API so the Spotify app
  never steals focus

## Install

```sh
brew install shpotify cava            # local control + visualizer
pipx install spotui                   # or: pip install spotui
spotui
```

Requires macOS, Python 3.11+, the Spotify desktop app, and a Spotify Premium
account (a Feb 2026 Spotify policy requires Premium for Web-API dev-mode
apps).

## Spotify API setup (one time)

1. Go to the [Spotify developer dashboard] and create an app.
   - If the **Web API checkbox is greyed out** on the create form (a known
     dashboard bug): create the app *without* it, then Edit the app and add
     Web API there — it won't be greyed out on edit.
2. Add redirect URI: `http://127.0.0.1:8888/callback`
3. Copy the **Client ID** into `~/.config/spotui/config.json`:

   ```json
   { "client_id": "your-client-id-here" }
   ```

   (or `export SPOTIPY_CLIENT_ID=...`)

4. First launch opens a browser to log in once; the token is cached after.
   No client secret needed — spotui uses the PKCE flow.

## Visualizer audio setup (optional)

macOS has no built-in way for apps to hear system output, so cava needs a
loopback device:

```sh
brew install blackhole-2ch
sudo killall coreaudiod              # load the driver
swift scripts/setup-audio.swift      # create + activate a Multi-Output device
```

The script builds a "Spotify TUI Multi-Out" device (your speakers +
BlackHole) via CoreAudio and switches the system output to it. spotui
auto-detects BlackHole and points cava at it. Skip all this and the
visualizer simply shows a hint instead.

> Note: with a Multi-Output device active, macOS volume keys are disabled
> (aggregate-device limitation). Use spotui's `+`/`-` — they control
> Spotify's own volume.

Turn it off / undo:

```sh
swift scripts/setup-audio.swift off      # back to speakers (device kept)
swift scripts/setup-audio.swift remove   # back to speakers + delete the device
```

Re-running without arguments turns it back on. Or just pick any output in
System Settings → Sound.

## Keys

| Key | Action |
|-----|--------|
| `space` | Play / pause |
| `n` / `p` | Next / previous track |
| `+` / `-` | Volume up / down |
| `l` | ♥ Like / unlike current track |
| `i` | Flip card: song ↔ artist info |
| `y` | Lyrics |
| `u` | Queue viewer |
| `d` | Device switcher |
| `/` | Search (Enter → results picker) |
| `b` | Toggle playlist sidebar |
| `v` | Toggle visualizer |
| `shift+V` | Visualizer style picker |
| `c` | Color palette / theme picker |
| click progress bar | Seek |
| `q` | Quit |

Startup arguments: `spotui next`, `spotui <playlist name>`, `spotui play
artist NF` — opens the TUI and runs the action.

## Config reference

`~/.config/spotui/config.json`:

| Key | Values | Default |
|-----|--------|---------|
| `client_id` | Spotify app client ID | — |
| `visualizer_style` | `area` `bars` `mirror` `peaks` `outline` `dots` `led` `rain` | `area` |
| `visualizer_colors` | `aurora` `synthwave` `matrix` `fire` `ocean` `mono` `sunset` `vaporwave` `rainbow` `ice` `lava` `candy` `gold` `cyberpunk` | `aurora` |
| `art_renderer` | `auto` `sixel` `tgp` `halfcell` `unicode` | `auto` |

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check src tests
```

Tests run headless with mocked Spotify backends — no account or audio setup
needed.

## License

MIT

[cava]: https://github.com/karlstav/cava
[Textual]: https://textual.textualize.io
[shpotify]: https://github.com/hnarayanan/shpotify
[lrclib.net]: https://lrclib.net
[Spotify developer dashboard]: https://developer.spotify.com/dashboard
