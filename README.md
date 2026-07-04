# Disco Terminal

[![CI](https://github.com/VinnyVanGogh/discoterminal/actions/workflows/ci.yml/badge.svg)](https://github.com/VinnyVanGogh/discoterminal/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/discoterminal)](https://pypi.org/project/discoterminal/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://github.com/VinnyVanGogh/discoterminal/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Turn your terminal into a disco.** A Spotify TUI with album art, a
real-time [cava] audio visualizer, full-app color theming, synced lyrics,
and playback control — without leaving your shell or focusing the Spotify
window.

![Disco Terminal — now playing with live visualizer](docs/media/now-playing.png)

```sh
pipx install discoterminal
```

## See it move

Pick a palette and the whole app rethemes — visualizer, borders, buttons, labels:

![Switching color palettes live](docs/media/visualizer-colors.gif)

Eight visualizer styles (area, bars, mirror, peaks, outline, dots, led, rain):

![Cycling visualizer styles](docs/media/visualizer-styles.gif)

Synced lyrics follow the song, Spotify-style; the card flips between
now-playing, artist info, and lyrics:

![Lyrics and artist card](docs/media/artist-song-lyrics-card.gif)

<details>
<summary><b>More demos & screenshots</b> (search, playlists, playback, cards…)</summary>

### Search anything

![Search feature](docs/media/search-feature.gif)

### Playlists sidebar

![Playlist selection](docs/media/playlist-function.gif)

### Playback controls

![Playback controls](docs/media/playback-controls.gif)

### Cards & pickers

| | |
|---|---|
| ![Artist info card](docs/media/artist-info.png) | ![Lyrics card](docs/media/lyrics.png) |
| ![Color palette picker](docs/media/color-options-card.png) | ![Visualizer style picker](docs/media/visualizer-styles-card.png) |
| ![Queue viewer](docs/media/queue-card.png) | ![Collapsed sidebar & visualizer](docs/media/collapsed-visualizer-and-playlists.png) |

### Visualizer on / off

![Visualizer toggle](docs/media/visualizer-on-5-secs.gif)

</details>

Built with [Textual]. Playback control picks the best backend for your
platform automatically:

| Platform | Local control | Visualizer audio |
|----------|--------------|------------------|
| macOS | [shpotify] (AppleScript) | BlackHole loopback (setup script included) |
| Linux | [playerctl] (MPRIS) | PulseAudio/PipeWire monitor — works out of the box |
| Windows *(experimental)* | Spotify Web API | cava's native WASAPI loopback |

The Spotify Web API (OAuth PKCE) powers your library, search, devices, queue,
and is the universal control fallback. Override backend selection with
`{"backend": "shpotify" | "playerctl" | "webapi"}` in config.

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

macOS:

```sh
brew install shpotify cava            # local control + visualizer
pipx install discoterminal                 # or: pip install discoterminal
discoterminal
```

Linux:

```sh
sudo apt install playerctl cava       # or your distro's equivalent
pipx install discoterminal
discoterminal
```

Windows (experimental — [testers wanted](../../issues)):

```powershell
pip install discoterminal                  # control goes through the Web API
discoterminal                              # cava optional; needs a sixel-capable terminal
```

Requires Python 3.11+ and the Spotify desktop app. The Web API features
(playlists, search, queue, lyrics card, artist info) need a Premium account —
a Feb 2026 Spotify policy requires Premium for Web-API dev-mode apps. Local
playback control via shpotify/playerctl works without Premium.

## Spotify API setup (one time)

1. Go to the [Spotify developer dashboard] and create an app.
   - If the **Web API checkbox is greyed out** on the create form (a known
     dashboard bug): create the app *without* it, then Edit the app and add
     Web API there — it won't be greyed out on edit.
2. Add redirect URI: `http://127.0.0.1:8888/callback`
3. Copy the **Client ID** into `~/.config/discoterminal/config.json`:

   ```json
   { "client_id": "your-client-id-here" }
   ```

   (or `export SPOTIPY_CLIENT_ID=...`)

4. First launch opens a browser to log in once; the token is cached after.
   No client secret needed — discoterminal uses the PKCE flow.

## Visualizer audio setup (macOS only, optional)

Linux and Windows: nothing to do — cava captures system audio natively
(PulseAudio/PipeWire monitor, WASAPI loopback).

macOS has no built-in way for apps to hear system output, so cava needs a
loopback device:

```sh
brew install blackhole-2ch
sudo killall coreaudiod              # load the driver
swift scripts/setup-audio.swift      # create + activate a Multi-Output device
```

The script builds a "Spotify TUI Multi-Out" device (your speakers +
BlackHole) via CoreAudio and switches the system output to it. discoterminal
auto-detects BlackHole and points cava at it. Skip all this and the
visualizer simply shows a hint instead.

> Note: with a Multi-Output device active, macOS volume keys are disabled
> (aggregate-device limitation). Use discoterminal's `+`/`-` — they control
> Spotify's own volume.

Turn it off / undo:

```sh
swift scripts/setup-audio.swift off      # back to speakers (device kept)
swift scripts/setup-audio.swift remove   # back to speakers + delete the device
```

Re-running without arguments turns it back on. Or just pick any output in
System Settings → Sound.

**Automatic mode:** once the Multi-Out device exists, discoterminal switches to it
on launch and restores your previous output on quit — you only run the
setup script once, ever. Opt out with `{"auto_multiout": false}` in
config.json.

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

Startup arguments: `discoterminal next`, `discoterminal <playlist name>`, `discoterminal play
artist NF` — opens the TUI and runs the action.

## Config reference

`~/.config/discoterminal/config.json`:

| Key | Values | Default |
|-----|--------|---------|
| `client_id` | Spotify app client ID | — |
| `visualizer_style` | `area` `bars` `mirror` `peaks` `outline` `dots` `led` `rain` | `area` |
| `visualizer_colors` | `aurora` `synthwave` `matrix` `fire` `ocean` `mono` `sunset` `vaporwave` `rainbow` `ice` `lava` `candy` `gold` `cyberpunk` | `aurora` |
| `art_renderer` | `auto` `sixel` `tgp` `halfcell` `unicode` | `auto` |
| `auto_multiout` | `true` / `false` — switch to Multi-Out on launch, restore on quit (macOS) | `true` |
| `backend` | `shpotify` `playerctl` `webapi` — override auto-selection | auto |

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check src tests
mypy src
```

Tests run headless with mocked Spotify backends — no account or audio setup
needed. CI covers Linux, macOS, and Windows.

## License

MIT

[cava]: https://github.com/karlstav/cava
[Textual]: https://textual.textualize.io
[shpotify]: https://github.com/hnarayanan/shpotify
[playerctl]: https://github.com/altdesktop/playerctl
[lrclib.net]: https://lrclib.net
[Spotify developer dashboard]: https://developer.spotify.com/dashboard
