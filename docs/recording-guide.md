# 📼 README Media Recording Guide

Re-recording all README media in kitty for sharp art and coherent flow.
**Name each file by its shot number** (`1.png`, `2.gif`, `3.gif`, …), drop
them all in `~/Downloads/discoterminal-media/`, and tell Claude — renaming and README updates are handled from there. GIFs straight from
CleanShot are perfect — anything over ~5 MB gets downscaled before commit.

## One-time setup (before recording anything)

- [ ] **kitty window**: ~**145 × 42 cells** (kitty shows `cols×rows` while
  drag-resizing). Landscape, matches README proportions.
- [ ] **Font size 13** (`Cmd +` / `Cmd -`) — readable in GIFs without
  being cramped.
- [ ] **Art renderer**: `"art_renderer": "auto"` in
  `~/.config/spotify_player/config.json` (sharp TGP in kitty).
- [ ] **Audio**: Multi-Out active so the visualizer dances
  (`swift scripts/setup-audio.swift` if it's off).
- [ ] **macOS Do Not Disturb ON** — no notification banners in shots.
- [ ] **Pick a demo track** with album art, synced lyrics on lrclib
  (check with `y` first), and real dynamics for the visualizer/rave.
- [ ] **Palette**: start on `cyberpunk` or `synthwave` — most photogenic.
- [ ] **Privacy check**: your playlist sidebar is visible in several
  shots — rename/hide anything you don't want on the README/PyPI.
- [ ] **CleanShot**: Record → select the kitty window → GIF (or MP4 — conversion is free on Claude's side if GIF export is slow). Keep clips
  **5–10 s** (rave gets 10–15).
- [ ] **Pace**: pause ~1 s between keypresses so viewers can follow.
  Prefer keys over mouse — footer highlights show what you pressed.

## Shot list — name files by number, tick as you go

- [ ] **1** — `1.png` → now-playing.png *(hero)*
  Full app, track playing **from a playlist** (so "📻 Playing from:" shows), viz mid-dance, art visible. The money still.
- [ ] **2** — `2.gif` → visualizer-colors.gif
  Press `c` → arrow through 2–3 palettes, Enter on one. Whole app rethemes each time.
- [ ] **3** — `3.gif` → visualizer-styles.gif
  `shift+V` → pick `rain` → `shift+V` → `led` → `shift+V` → `peaks`.
- [ ] **4** — `4.gif` → artist-song-lyrics-card.gif
  `y` for lyrics, let the highlight advance 2–3 lines, then `i` for artist card, then `i` back.
- [ ] **5** — `5.gif` → search-feature.gif
  `/` → type an artist → Enter → results modal → pick a track.
- [ ] **6** — `6.gif` → playlist-function.gif
  Click/Enter a playlist → **track browser modal** (new!) → pick a track mid-list.
- [ ] **7** — `7.png` → liked-songs.png *(new)*
  Select **♥ Liked Songs** at the top of the sidebar, screenshot the open modal.
- [ ] **8** — `8.gif` → playback-controls.gif
  `space` pause → `space` play → `n` next → **click the progress bar** to seek.
- [ ] **9** — `9.png` → artist-info.png
  Artist card still (`i`) — genres/followers/top tracks visible.
- [ ] **10** — `10.png` → lyrics.png
  Lyrics card still (`y`) with a line highlighted.
- [ ] **11** — `11.png` → color-options-card.png
  `c` picker open (shows the color swatches).
- [ ] **12** — `12.png` → visualizer-styles-card.png
  `shift+V` picker open.
- [ ] **13** — `13.png` → queue-card.png
  `u` queue modal open.
- [ ] **14** — `14.png` → collapsed-visualizer-and-playlists.png
  `b` (sidebar hidden) + `v` (viz hidden) — the minimal layout.
- [ ] **15** — `15.gif` → visualizer-on-5-secs.gif
  `v` off → `v` on, viz reacting.
- [ ] **16** — `16.gif` → rave-mode.gif *(new, 10–15 s)*
  `shift+R` (pulse — let 3–4 beats strobe) → `shift+R` (kaleido TAKEOVER — let a drop hit) → `Escape`. Record during the loudest part of the track.

## Handoff

```sh
mkdir -p ~/Downloads/discoterminal-media   # drop 1.png … 16.gif here
```

Then say the word. Claude will: rename to the final names above,
downscale any GIF over ~5 MB (README load times), add the two new
README sections (Liked Songs, 🕺 Rave mode — rave likely becomes the
top "See it move" demo), commit, and push. Any number you skip keeps its
current media.

## Bonus (optional)

- [ ] **17** — `17.gif` — vertical rave for Instagram: resize kitty tall
  (~95 × 55), takeover mode, 10 s. Won't go in the README; gets the
  blurred-background 1080×1920 treatment for stories.
