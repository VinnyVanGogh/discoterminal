# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org).

## [0.2.2] — 2026-07-04

### Added
- ♥ Liked Songs pinned at the top of the sidebar — browse and play your
  saved tracks like any playlist (queues the first 100; the Web API has
  no playable context for the collection)

## [0.2.1] — 2026-07-04

### Changed
- Rain visualizer floor bars now scale to ~1/3 of the visualizer height
  (was a fixed 2 rows — a sliver on tall terminals)

## [0.2.0] — 2026-07-04

### Added
- Now-playing card shows the playback context ("Playing from: <playlist>")
- Selecting a playlist opens a track browser modal — play the whole
  playlist or jump to a specific track within it (playback continues in
  the playlist context)
- Compact shuffle/repeat indicators on the state line, live from the
  Web API (replaces the old text rows)

## [0.1.2] — 2026-07-04

### Fixed
- Rain visualizer crashed with IndexError when the terminal was resized
  narrower (stale droplets kept coordinates from the wider layout)
- A failed visualizer frame can no longer crash the whole app

## [0.1.1] — 2026-07-03

### Fixed
- README images now use absolute URLs so they render on PyPI
- Album-art retry timer no longer outlives the app on hidden widgets
  (Windows CI flake); all worker-scheduled renders tolerate shutdown

## [0.1.0] — 2026-07-03

Initial release. 🪩

### Added
- Now-playing card with album art (sixel/TGP/halfcell/unicode renderers),
  live progress bar, and click-to-seek
- Embedded [cava](https://github.com/karlstav/cava) audio visualizer —
  8 render styles (area, bars, mirror, peaks, outline, dots, led, rain),
  14 color palettes
- Whole-app theming derived from the active visualizer palette
- Synced lyrics card (lrclib.net) — current line highlighted and following
  playback, `[`/`]` sync nudge, plain-text fallback
- Artist card flip: genres, followers, popularity, top tracks, artist photo
- Live playlist sidebar, mixed search (tracks/albums/playlists/artists),
  queue viewer, device switcher, like/unlike
- Multi-platform playback backends: shpotify (macOS), playerctl (Linux),
  Spotify Web API (universal fallback; Windows experimental)
- macOS audio tooling: CoreAudio Multi-Output device creator
  (`scripts/setup-audio.swift`) and automatic output switching on
  launch/quit so cava hears system audio via BlackHole
- First-run setup checklist when no credentials are configured
- OAuth via Spotify PKCE flow — client ID only, no secret

[0.1.0]: https://github.com/VinnyVanGogh/discoterminal/releases/tag/v0.1.0
