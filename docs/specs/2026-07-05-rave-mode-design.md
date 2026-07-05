# Rave mode

`R` cycles: **off → pulse → takeover → off**. `Escape` also exits takeover.

## Pulse
Normal layout. Each detected beat rethemes the entire app (borders,
buttons, visualizer, labels) to a random palette — never the same one
twice in a row. The user's saved palette is untouched; exiting rave
restores it. Theme swaps skip the status-refresh path (no subprocess per
beat).

## Takeover
Adds the `rave-takeover` class, hiding sidebar, now-playing card,
progress, controls, search, and footer — the visualizer fills the
terminal, still beat-strobing, with `♪ artist — track ♪` centered above
it (updates on track change via the beat handler).

## Beat detection (visualizer.py)
Runs in the cava frame-reader thread. Frame energy = sum of bar values;
rolling window of 24 frames (~2s). A beat = energy ≥ 1.4× the window
average, rate-limited to one per 250ms (max 4 flashes/sec, below common
photosensitivity risk thresholds). Beats are relative to the song's own
energy: quiet tracks pulse rarely, loud drops slam. The detector only
runs when the app registers an `on_beat` callback.

## Testing
Unit: detector fires on spikes, respects the rate cap. Pilot: R-cycle
transitions, takeover class add/remove, palette restore, Escape exit,
beats ignored while off.
