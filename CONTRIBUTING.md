# Contributing to Disco Terminal

Thanks for your interest! This is a small project — the process is simple.

## Dev setup

```sh
git clone https://github.com/VinnyVanGogh/discoterminal
cd discoterminal
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

```sh
pytest              # 50+ tests, all headless/mocked — no Spotify account needed
ruff check src tests
mypy src
```

CI runs the same three on Linux, macOS, and Windows.

## What's especially welcome

- **Linux and Windows testing.** The playerctl and Web API backends are
  CI-tested but need real-world reports. If something breaks on your
  machine, an issue with the traceback is a genuine contribution.
- Visualizer styles and palettes — see `visualizer.py`; a style is a
  function from `(columns, height)` to rows of characters, a palette is a
  6-color bottom→top tuple.
- Terminal compatibility notes (which art renderer works where).

## Style

- Match the existing code: typed signatures, small modules, workers for
  anything that blocks.
- Tests mock the network/subprocess boundary (`spotify`, `webapi`,
  `lyrics`) — see `tests/conftest.py` for the pattern.
- Conventional-commit-ish messages (`feat:`, `fix:`, `docs:`…).
