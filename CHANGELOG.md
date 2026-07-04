# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org).

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
