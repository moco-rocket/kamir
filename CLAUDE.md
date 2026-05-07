# Kamir — Claude Code Project Rules

## Language
- All production code must be written in Python (3.11+).
- All code comments must be written in English.
- User-facing strings (CLI output, logs) may be in Japanese or English.

## Dependency Management
- Use `uv` for all dependency and virtual environment management.
- Never use `pip install` directly; use `uv add` or `uv sync`.
- Dependencies are declared in `pyproject.toml`.

## Architecture — Separation of Concerns
Keep the following concerns strictly separate. Do not mix them in a single module:

| Layer | Responsibility |
|---|---|
| `kamir/db/` | Loading and querying MTGJSON (`AllPrintings.sqlite`) |
| `kamir/filter/` | Card filtering logic (pure functions, no I/O) |
| `kamir/images/` | Image fetching from Scryfall and local caching |
| `kamir/render/` | PDF rendering and card layout logic |
| `kamir/printer/` | Printer integration (sending PDFs to the system printer) |
| `kamir/cli.py` | CLI entry point only; no business logic |
| `kamir/config.py` | Configuration loading from `config.toml` |

## Card Filtering
- Card filtering functions must be **pure functions**: same input → same output, no side effects, no I/O.
- Place all filtering logic in `kamir/filter/`.
- Filtering criteria (allowed sets, card types, layout rules) must be data-driven, not hardcoded conditionals.

## Testing
- Write tests for every new piece of logic added.
- Tests live in `tests/` mirroring the `kamir/` structure.
- **No network access in tests.** Mock or fixture all HTTP calls (Scryfall API, etc.).
- Use real SQLite databases only from local fixture files; never download during tests.
- Run tests with `uv run pytest`.

## Raspberry Pi Compatibility
- Assume the deployment target is **Raspberry Pi OS Bookworm (64-bit), headless**.
- Do not use OpenCV (`cv2`). Use Pillow (`PIL`) for all image processing.
- Do not assume a display is available (`DISPLAY` env var may be unset).
- Prefer lightweight dependencies; avoid packages that require compilation of large C extensions.
- All long-running operations must be resumable (idempotent): skip already-processed items.

## General Coding Rules
- Prefer pure functions over stateful classes where practical.
- Do not add error handling for impossible cases; validate only at system boundaries (CLI args, external API responses, file I/O).
- Do not add comments explaining what the code does; only add comments explaining non-obvious *why*.
- Do not create extra abstraction layers beyond what a task requires.
- Default to no docstrings; add a one-line docstring only when the function's purpose is not obvious from its name and signature.
