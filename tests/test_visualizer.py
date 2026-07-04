from rich.text import Text

from discoterminal.visualizer import PALETTES, STYLES, SpectrumRenderer, _sample


def test_sample_resizes_to_width():
    assert len(_sample(list(range(100)), 40)) == 40
    assert _sample([], 10) == []
    assert _sample([1, 2, 3], 0) == []


def test_every_style_and_palette_renders_exact_width():
    renderer = SpectrumRenderer()
    cols = [(i * 3) % 9 for i in range(40)]
    for style in STYLES:
        for palette in PALETTES:
            for _ in range(4):  # stateful styles (peaks, rain) need frames
                markup = renderer.render(cols, 10, style, palette)
            lines = markup.split("\n")
            assert len(lines) == 10
            for line in lines:
                assert Text.from_markup(line).cell_len == 40


def test_peaks_fall_between_frames():
    renderer = SpectrumRenderer()
    renderer.render([8] * 10, 10, "peaks")
    high = list(renderer._peaks)
    for _ in range(5):
        renderer.render([0] * 10, 10, "peaks")
    assert all(
        after < before for after, before in zip(renderer._peaks, high, strict=True)
    )


def test_unknown_style_falls_back_to_area():
    renderer = SpectrumRenderer()
    markup = renderer.render([4] * 10, 5, "nonsense")
    assert len(markup.split("\n")) == 5


def test_rain_survives_resize_narrower():
    renderer = SpectrumRenderer()
    # spawn drops at a wide width
    for _ in range(20):
        renderer.render([8] * 150, 20, "rain")
    assert renderer._drops, "expected some drops to have spawned"
    # shrink the terminal — stale drops beyond the new width must be culled
    for _ in range(5):
        markup = renderer.render([8] * 100, 20, "rain")
    assert all(x < 100 for x, _y, _s in renderer._drops)
    assert len(markup.split("\n")) == 20
