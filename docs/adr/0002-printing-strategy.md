# ADR-0002: Printing Strategy — ESC/POS Text Re-render

**Date**: 2026-05-07
**Status**: Accepted

---

## Context

Kamir must print a card slip on an MJ-5890K 58mm thermal printer each time a creature is
selected during play. The printed slip serves as the token placed on the table; it must
clearly identify the creature (name, type, abilities, P/T) so both players can read it
at arm's length.

The previous design generated a 48×67mm PDF per card using ReportLab, embedding a
grayscale crop of the Scryfall card image. The printer target is now a thermal receipt
printer, not a desktop printer, so the output format must change.

Three approaches were evaluated.

---

## Options Considered

### Option A: Print pre-generated PDFs via CUPS

Generate PDFs as before; install CUPS on the Raspberry Pi; use `lp` to send PDFs to the
thermal printer with an appropriate CUPS driver.

**Problems**:
- CUPS installation on headless Raspberry Pi OS Bookworm is complex and fragile.
- Thermal printers require a specific CUPS raster driver (e.g., Gutenprint or a
  vendor-specific PPD). The MJ-5890K is a generic ESC/POS printer with no guaranteed CUPS
  support.
- PDF-to-raster conversion (via Ghostscript) at 203 DPI on a Raspberry Pi 4 takes 2–5
  seconds per page. This is a noticeable delay during gameplay.
- The approach still requires pre-generating thousands of PDFs before first use.
- Adds `ghostscript` and a CUPS stack as system dependencies.

### Option B: Render the card as a bitmap; send as ESC/POS raster

Fetch the Scryfall card image; scale it to 384×N pixels; send as an ESC/POS raster image
command (GS v 0).

**Problems**:
- Reproducing the original card artwork raises copyright concerns: Wizards of the Coast
  holds copyright on card illustrations and the card frame design.
- The MJ-5890K's thermal paper surface produces poor contrast for photographic images;
  grayscale halftoning at 203 DPI on receipt paper is difficult to read.
- Raster transfer is slow: a 384×500 pixel bitmap is ~190 KB uncompressed and takes
  several seconds over USB.
- Image fetching must happen at game time (per card, on demand), not pre-downloaded.
  This introduces network dependency during gameplay.
- Adds `Pillow` and `requests` back into the play-path dependency graph.

### Option C: Re-render the card as a text layout; send as ESC/POS text

Compose a structured text representation of the card's game-relevant data (name, mana cost,
type line, oracle text, P/T) and send it as ESC/POS text commands.

**Benefits**:
- ESC/POS text output is what thermal printers are optimised for: fast (< 1 second),
  high contrast, reliable.
- A text re-render of card data is more legible on narrow receipt paper than a scaled-down
  card image. Players need to read the oracle text; a text layout serves this better.
- No artwork is reproduced: no copyright concern.
- No network access is needed at game time.
- The rendering logic is a pure function (`Card → list[Instruction]`) that is trivially
  testable without hardware.
- Raw bytes are written directly to the device file (`/dev/usb/lp0`); no CUPS or system
  printer configuration is required, and no additional Python library is needed.
- Minimal paper usage: a typical card takes 6–10 cm of 58mm receipt paper.

**Trade-offs**:
- The slip does not show the card's artwork. Players unfamiliar with a selected creature
  will see only text.
- Mana symbols must be rendered in ASCII notation (`{W}`, `{U}`, etc.) rather than
  graphical glyphs, because thermal printer character encoding support is inconsistent.

---

## Decision

**Option C**: ESC/POS text re-render via raw byte writes to the device file.

The printed slip is a re-composed layout of the card's game-relevant data, not a copy
of the original card frame. This is consistent with the project's goals: a readable,
functional token for paper play, not a proxy for collecting or trading.

---

## Card Layout Design

See [`docs/printing.md`](../printing.md) for the full layout specification and examples.

In summary:
- 32 characters wide (Font A)
- Full-width horizontal rules separate sections
- Name: bold, uppercase, left; mana cost: right, same line
- Oracle text: word-wrapped at 32 chars
- P/T: bold, right-aligned; expansion: left-aligned, same line
- Full paper cut after the slip

---

## Consequences

- `kamir/printer/render.py` contains the pure text layout logic (returns `list[Instruction]`).
- `kamir/printer/send.py` encodes instructions to ESC/POS bytes and writes them to the device file.
- `kamir/printer/image.py` resizes/dithers card art to an ESC/POS raster (uses `Pillow`).
- `config.toml` gains a `[printer]` section with a `device` key (device file path).
- No Scryfall API calls occur during gameplay; art is pre-fetched during `kamir build-db`.
- Art is cached as ESC/POS raster blobs in `kamir_cardpool.sqlite` (not as image files on disk).
- `ReportLab` and `requests` are removed. `Pillow` is retained for art processing.
- The hardware setup step is `uv sync` + USB plug-in + one config entry; no CUPS required.
