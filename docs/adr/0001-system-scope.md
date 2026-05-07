# ADR-0001: System Scope — Play Tool, Not Batch Processor

**Date**: 2026-05-07
**Status**: Accepted

---

## Context

The initial implementation of Kamir is a batch pipeline:

1. Load `AllPrintings.sqlite`
2. Filter creature cards
3. Fetch artwork from Scryfall for every card in the pool (~3,000+ images)
4. Render each card as a 48×67mm PDF
5. Store all PDFs locally

This was designed as a pre-generation tool: run once, cache everything, then print
individual PDFs on demand. The approach mirrors a reference implementation that targeted
desktop PDF printing.

The actual use case is different. Kamir is a tabletop tool for playing Momir Basic in
paper. During a game, a player declares a mana value and immediately needs:
1. A randomly selected creature at that mana value.
2. A printed slip identifying the creature, placed on the table as a token.

The batch pipeline is the wrong shape for this problem:
- Fetching 3,000+ images before play can begin takes hours and requires significant storage.
- Pre-rendering PDFs for all cards is wasted work: only one card per mana value per game
  turn is ever needed.
- A thermal receipt printer (MJ-5890K) is not a PDF printer; the rendering pipeline
  produces the wrong output format.
- The image fetch and PDF render stages add `requests`, `Pillow`, and `ReportLab` as
  runtime dependencies. None of these are needed for the play path.

---

## Options Considered

### Option A: Keep the batch pipeline; add a `play` command on top
Add `kamir play --mv X` that picks a random PDF from the pre-generated set and sends it
to the printer.

**Problems**:
- Still requires the 3,000-image pre-generation step before first use.
- Does not address the wrong output format (PDF → thermal printer).
- Keeps unnecessary complexity in the codebase.

### Option B: Rewrite around the play workflow; keep only the database builder
The database builder (MTGJSON → filtered SQLite) is still needed — it remains as a
one-time setup step. The image fetch and PDF render stages are removed. The play app
queries the database directly at game time and triggers the printer for each selected card.

**Benefits**:
- Setup is fast: building the card pool database takes minutes, not hours.
- No image storage required (gigabytes of artwork images eliminated).
- The dependency graph is dramatically simpler.
- The output format (ESC/POS text to thermal printer) matches the target hardware.

### Option C: Split into separate repositories
Separate repos for `kamir-db-builder`, `kamir-play`, and `kamir-printer`.

**Problems**:
- Overkill for a single-operator personal tool on a Raspberry Pi.
- Shared domain model (`Card`) would need a separate published package.
- Deployment becomes three `git clone` + `uv sync` operations.

---

## Decision

**Option B**: rewrite the system around the play workflow.

The database builder is retained as a setup step. Everything else is rebuilt:
- The play app (`kamir/play/`) is the primary feature.
- The printer/rendering subsystem (`kamir/printer/`) replaces PDF generation.
- Image fetching (`kamir/images/`) and PDF rendering (`kamir/render/`) are removed.
- The repository remains a single package.

---

## Consequences

- `kamir/images/` is deleted.
- `kamir/render/` is deleted.
- `kamir/play/` is added.
- `kamir/printer/` gains ESC/POS rendering and hardware I/O (previously a stub).
- `kamir/domain.py` is added as the shared `Card` dataclass.
- `pyproject.toml` loses `requests`, `Pillow`, `ReportLab`; gains `python-escpos`.
- The CLI changes: `build-db` is retained; `fetch-images` and `make-pdfs` are removed;
  `play` and `print-test` are added.
- `config.toml` loses `[image]`, `[pdf]`, and `[scryfall]` sections; gains `[printer]`.
- First-time setup time drops from hours to minutes.
- Storage requirement drops from several GB to tens of MB.
