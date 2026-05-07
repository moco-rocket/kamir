# Kamir — Requirements

## Overview

Kamir is a tool for generating printable proxy cards for a Momir Basic-like Magic: The Gathering variant.
It extracts creature cards from the MTGJSON database, fetches card artwork from Scryfall,
and produces printer-ready PDFs organized by mana value.
The tool is designed to run headlessly on a Raspberry Pi.

---

## Functional Requirements

### F1 — Database Building

- Load `AllPrintings.sqlite` from the local filesystem (downloaded separately from mtgjson.com).
- Filter cards to an allowed set list defined in `config.toml`.
- Include only creature cards with a valid mana value (0–16).
- Handle the following card layouts correctly: `normal`, `adventure`, `transform`, `meld`, `modal_dfc`, `leveler`.
- For double-faced cards, select the front face (the face whose name matches the card's primary name).
- Exclude joke sets, non-English printings, and cards without a valid collector number.
- Write filtered results to `kamir_cardpool.sqlite` in the configured output directory.
- Operation must be idempotent: re-running rebuilds the output database from scratch.

### F2 — Image Fetching

- Fetch card artwork from the Scryfall API using set code and collector number.
- Convert fetched images to grayscale.
- Resize and crop images to the canonical size (100×171 px).
- Save images under `data/img/{mana_value}/{card_id}.jpg`.
- Skip cards whose image file already exists (resumable).
- On fetch failure, log the error and save a placeholder image; do not abort the entire run.
- Respect Scryfall API rate limits (minimum 1-second delay between requests).

### F3 — PDF Generation

- Generate one PDF file per card at `data/pdf/{mana_value}/{card_id}.pdf`.
- Card PDF dimensions: 48 mm × 67 mm.
- Include the following elements on each card:
  - Card name (top-left)
  - Mana cost (top-right)
  - Card artwork (centered)
  - Type line
  - Oracle text (auto-wrapped; font size scales down for long text)
  - Expansion code (bottom-left)
  - Power/Toughness (bottom-right, bold)
- Skip cards whose PDF already exists (resumable).

### F4 — CLI

- Provide a single entry point: `kamir` (or `python -m kamir`).
- Support running all stages in sequence: `kamir run`.
- Support running individual stages: `kamir build-db`, `kamir fetch-images`, `kamir make-pdfs`.
- Display a progress bar for each stage.
- Write structured logs to `logs/kamir.log` in addition to stdout.

### F5 — Printer Integration (future)

- Provide a `kamir print --mv <N>` command to send the PDFs for a given mana value to the system printer.
- Out of scope for the initial implementation.

---

## Non-Functional Requirements

### NFR1 — Platform
- Target: Raspberry Pi OS Bookworm (64-bit), headless (no display).
- Python 3.11 or later.
- Dependency management via `uv`.

### NFR2 — Resumability
- Every stage must be idempotent and resumable after interruption.
- Already-processed items (existing image files, existing PDF files) are skipped automatically.

### NFR3 — Lightweight Dependencies
- Do not use OpenCV. Use Pillow for all image processing.
- Minimize dependencies that require large compiled C extensions.

### NFR4 — Testability
- Card filtering logic must be pure functions that can be tested without I/O.
- No network access in tests; all external calls are mocked or replaced with fixtures.

### NFR5 — Configuration
- All tuneable parameters (allowed sets, paths, image dimensions, API base URL) are defined in `config.toml`.
- No hardcoded magic values in production code.

---

## Out of Scope

- Graphical user interface.
- Online multiplayer or digital card game logic.
- Card legality checking or rules enforcement.
- Support for non-creature card types.
- Fetching `AllPrintings.sqlite` automatically (user downloads it manually).
