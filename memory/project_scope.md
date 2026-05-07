---
name: Kamir project scope
description: Kamir is a Momir Basic tabletop play tool targeting Raspberry Pi + MJ-5890K thermal printer, not a batch PDF card generator
type: project
---

Kamir's real purpose is an interactive play tool for Momir Basic in paper: player declares
mana value X → random creature selected → card printed on MJ-5890K thermal printer as a token.

**Why:** The original reference implementation was a batch pipeline (fetch Scryfall images,
render PDFs). The real hardware target is a 58mm thermal receipt printer, not a desktop printer.

**How to apply:** 
- The three subsystems are: Database Builder (setup), Play App (primary feature), Printing/Rendering (on-demand).
- Scryfall image fetching and PDF generation are OUT of scope — removed in this rewrite.
- Printed output is a text re-render (ESC/POS), not a card image copy.
- `python-escpos` handles MJ-5890K over USB; no CUPS required.
- `kamir/images/` and `kamir/render/` are slated for deletion; `kamir/play/` is new.
- Shared domain model: `Card` dataclass in `kamir/domain.py`.
- Architecture and requirements are documented in `docs/` (requirements.md, architecture.md, rules-note.md, printing.md, adr/).
