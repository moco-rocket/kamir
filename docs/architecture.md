# Kamir — Architecture

## Technology Stack

| Concern | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Ecosystem, RPi compatibility |
| Dependency management | uv | Fast, reproducible, lockfile-based |
| Database | SQLite (stdlib `sqlite3`) | No server; file-based; ships with Python |
| CLI | `argparse` (stdlib) | No extra dependency |
| Configuration | `tomllib` (stdlib 3.11+) + `config.toml` | No extra dependency |
| Thermal printing | Raw ESC/POS bytes over file I/O (stdlib only) | No extra dependency; direct write to `/dev/usb/lp0` |
| Card art processing | `Pillow` | Image resize and 1-bit dithering for ESC/POS raster output |
| Testing | `pytest` + `pytest-mock` | Standard; easy fixture support |

Removed from the previous scope:
- `ReportLab` — PDF generation removed; ESC/POS text output replaces it
- `requests` — Scryfall API is called via stdlib `urllib` only (during `build-db`)

---

## Subsystem Split

Kamir is divided into three subsystems. Each subsystem has a distinct runtime context and
operator. They communicate only through the shared SQLite database and the shared domain model.

```
┌─────────────────────────────────────────────────────────────────┐
│  Subsystem 1: Database Builder                                   │
│  Run once (setup). Operator: system owner.                       │
│  Input:  AllPrintings.sqlite (manual download)                   │
│  Output: kamir_cardpool.sqlite                                   │
│  Modules: kamir/db/, kamir/filter/                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │  kamir_cardpool.sqlite
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Subsystem 2: Play App                                           │
│  Run during a game session. Operator: player.                    │
│  Input:  mana value (integer, from player)                       │
│  Output: selected Card (to terminal + printer trigger)           │
│  Modules: kamir/play/                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │  Card (domain object)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Subsystem 3: Printing/Rendering                                 │
│  On-demand, triggered by Play App.                               │
│  Input:  Card (domain object)                                    │
│  Output: ESC/POS bytes → MJ-5890K thermal printer               │
│  Modules: kamir/printer/                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Shared Domain Model

All three subsystems exchange data using a single `Card` dataclass defined in `kamir/domain.py`.
No subsystem passes raw `dict` rows to another subsystem.

```python
@dataclass(frozen=True)
class Card:
    name: str
    mana_value: int
    mana_cost: str
    type_line: str
    oracle_text: str
    power: str
    toughness: str
    expansion: str
    collector_number: str
    layout: str
```

The database builder produces `Card` objects. The play app selects `Card` objects from the
database. The printer/renderer accepts a `Card` object and formats it for output.

---

## Repository Structure

Kamir remains a **single repository**. See the decision rationale in
[`docs/adr/0001-system-scope.md`](adr/0001-system-scope.md).

### Target Directory Layout

```
kamir-rewrite/
├── pyproject.toml
├── uv.lock
├── config.toml
├── CLAUDE.md
├── docs/
│   ├── requirements.md
│   ├── architecture.md
│   ├── rules-note.md
│   ├── printing.md
│   └── adr/
│       ├── 0001-system-scope.md
│       └── 0002-printing-strategy.md
├── kamir/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Argument parsing; wires subsystems together
│   ├── config.py           # Load config.toml
│   ├── domain.py           # Card dataclass (shared by all subsystems)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── art.py          # Fetch card art from Scryfall; store/load raster blobs
│   │   ├── load.py         # Open AllPrintings.sqlite; iter raw dicts; all_set_codes()
│   │   └── write.py        # Create and populate kamir_cardpool.sqlite
│   ├── filter/
│   │   ├── __init__.py
│   │   └── cards.py        # Pure functions: is_creature(), filter_cards(), …
│   ├── play/
│   │   ├── __init__.py
│   │   ├── select.py       # Query card pool by mana value; return random Card
│   │   └── display.py      # Format Card for terminal output
│   ├── printer/
│   │   ├── __init__.py
│   │   ├── image.py        # Resize/dither card art to ESC/POS RasterImage
│   │   ├── render.py       # Compose ESC/POS instruction list from Card
│   │   └── send.py         # Encode instructions to bytes; write to MJ-5890K
│   └── utils/
│       ├── __init__.py
│       └── log.py          # Logging setup
├── data/
│   └── db/                 # AllPrintings.sqlite + kamir_cardpool.sqlite
├── logs/
│   └── kamir.log
└── tests/
    ├── conftest.py
    ├── test_db.py          # Unit tests for db/write.py + db/load.py
    ├── test_db_art.py      # Unit tests for db/art.py
    ├── test_display.py     # Unit tests for play/display.py
    ├── test_filter.py      # Unit tests for kamir/filter/cards.py
    ├── test_image.py       # Unit tests for printer/image.py
    ├── test_render.py      # Unit tests for printer/render.py
    ├── test_select.py      # Unit tests for play/select.py
    └── test_send.py        # Unit tests for printer/send.py
```

### Modules Removed from the Previous Design

| Module | Reason for removal |
|---|---|
| `kamir/images/` | Replaced by `kamir/db/art.py` + `kamir/printer/image.py` |
| `kamir/render/pdf.py` | PDF rendering replaced by ESC/POS text output |
| `kamir/render/layout.py` | Layout constants specific to the removed PDF renderer |

---

## Module Responsibilities

### `kamir/domain.py`
Defines the `Card` frozen dataclass. No logic, no I/O. Imported by all other modules.

### `kamir/db/`
- `load.py`: opens `AllPrintings.sqlite` in read-only mode; returns raw `dict` rows.
  Also provides `all_set_codes()` to derive the full physical-play set list from the DB.
  No filtering logic here.
- `art.py`: fetches card art from the Scryfall API during `build-db`; stores and loads
  pre-rendered ESC/POS raster blobs in `kamir_cardpool.sqlite`.
- `write.py`: creates `kamir_cardpool.sqlite`; writes `Card` objects as rows.
  Preserves existing data by default; pass `force=True` to drop and recreate.

### `kamir/filter/`
Pure functions only. Input: raw `dict` rows from MTGJSON. Output: `Card` objects or booleans.

- `is_creature(card: dict) -> bool`
- `is_allowed_set(card: dict, allowed_sets: set[str]) -> bool`
- `is_front_face(card: dict) -> bool`
- `has_valid_collector_number(card: dict) -> bool`
- `is_within_base_set(card: dict) -> bool`
- `is_funny(card: dict) -> bool`
- `is_reprint(card: dict) -> bool`
- `has_supported_layout(card: dict) -> bool`
- `to_card(card: dict) -> Card` — convert passing dict to a `Card`
- `filter_cards(raw: list[dict], allowed: set[str]) -> list[Card]`

### `kamir/play/`
- `select.py`: queries `kamir_cardpool.sqlite` for cards at a given mana value;
  returns one uniformly random `Card`. Accepts an injectable random source for testing.
- `display.py`: formats a `Card` as a multi-line terminal string. Pure function.

### `kamir/printer/`
- `render.py`: converts a `Card` (and optional `RasterImage`) into an ordered list of
  ESC/POS instructions. Pure function; no hardware dependency.
- `image.py`: fetches the card's art_crop image from the Scryfall API; resizes and
  dithers it to a 384×192 dot 1-bit bitmap; returns a `RasterImage` instruction (or
  `None` if the fetch fails). This is the only module with network I/O.
- `send.py`: encodes the instruction list to raw ESC/POS bytes and writes them
  directly to the device file (e.g. `/dev/usb/lp0`). This is the only module with hardware I/O.

### `kamir/cli.py`
Parses arguments, loads config, and wires subsystems together. No business logic.

---

## Data Flow

### Database Builder (setup)
```
AllPrintings.sqlite
        │
        ▼
   db/load.py          raw dict rows
        │
        ▼
  filter/cards.py      Card objects
        │
        ▼
   db/write.py         kamir_cardpool.sqlite
        │
        ▼
    db/art.py          Scryfall API → ESC/POS raster blobs → kamir_cardpool.sqlite
```

### Play Loop (game time)
```
Player input (mana value)
        │
        ▼
  play/select.py       random Card from kamir_cardpool.sqlite
        │
        ├──► play/display.py    → terminal output
        │
        └──► printer/render.py  → ESC/POS layout
                  │
                  ▼
             printer/send.py    → MJ-5890K
```

---

## Configuration (`config.toml`)

```toml
[paths]
mtgjson_db = "data/db/AllPrintings.sqlite"
kamir_db   = "data/db/kamir_cardpool.sqlite"
log_file   = "logs/kamir.log"

[printer]
device     = "/dev/usb/lp0" # USB path to MJ-5890K on Raspberry Pi

[sets]
allowed = [
  "LEA", "LEB", "2ED",
  # ... full list in config.toml, not in code
]
```

---

## Phased Implementation Plan

### Phase 1 — Database Builder ✅
Scope: introduce the `Card` domain model, revise filter logic to produce `Card` objects,
ensure tests pass.

- Add `kamir/domain.py` with the `Card` dataclass.
- Revise `kamir/filter/cards.py`: add `to_card()`, update `filter_cards()` to return
  `list[Card]`.
- Revise `kamir/db/write.py` to accept `list[Card]`.
- Update `kamir/cli.py` to remove image and PDF stages.
- Remove `kamir/images/`, `kamir/render/`, and related dependencies from `pyproject.toml`.
- Milestone: `kamir build-db` produces a correct `kamir_cardpool.sqlite`.

### Phase 2 — Play App ✅
Scope: interactive creature selection and terminal display.

- Add `kamir/play/select.py` with `select_creature(db_path, mana_value, rng)`.
- Add `kamir/play/display.py` with `format_card(card) -> str`.
- Add `kamir play` command to `kamir/cli.py` (interactive loop).
- Milestone: `kamir play` allows selecting cards and displays them; no printer yet.

### Phase 3 — Printing ✅
Scope: ESC/POS text rendering and MJ-5890K integration.

- Add `kamir/printer/render.py` with `render_card(card) -> list[Instruction]`.
- Add `kamir/printer/send.py` with `print_card(card, device)`.
- Wire play loop to printer in `kamir/cli.py`.
- Add `kamir print-test --mv X` command for standalone hardware testing.
- Raw ESC/POS bytes written directly to the device file; no additional library needed.
- Milestone: `kamir play` prints a card slip on the MJ-5890K after each selection.

### Phase 4 — Hardware Integration & Polish
Scope: end-to-end testing on Raspberry Pi, configuration tuning.

- Test full play loop on Raspberry Pi OS Bookworm + MJ-5890K.
- Tune printer profile, paper cut settings, and character encoding in `config.toml`.
- Handle edge cases: mana value with zero cards in pool, printer not connected.
- Optional: GPIO button to trigger play instead of keyboard.

---

## Key Design Decisions

**1. Single repository.**
The three subsystems share a domain model and communicate through a single SQLite file.
Splitting into multiple repos would add packaging and deployment complexity with no benefit
for a single-operator personal tool on a Raspberry Pi. See ADR-0001.

**2. ESC/POS text rendering instead of PDF or bitmap.**
Thermal printers are optimised for text. A re-composed text layout of name, mana cost,
type, oracle text, and P/T is more readable on a 58mm slip than a scaled-down card image,
requires no artwork licensing consideration, and prints in under a second. See ADR-0002.

**3. Pure functions for filtering and rendering.**
Both the card filtering logic (`filter/`) and the card layout rendering (`printer/render.py`)
are pure functions. This makes them independently testable without hardware or database access.

**4. Injected random source.**
`select.py` accepts a `random.Random` instance rather than calling `random.choice` directly.
This allows tests to use a fixed seed for deterministic assertions.

**5. Artwork fetched at build time, not at play time.**
Scryfall `art_crop` images are downloaded during `kamir build-db` and cached as
pre-rendered ESC/POS raster blobs in `kamir_cardpool.sqlite`. During gameplay, the
raster blob is read from the DB and sent to the printer with no network access.
The printed card shows the art crop followed by the text re-render.
