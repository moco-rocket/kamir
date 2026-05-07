# Kamir — Architecture

## Technology Stack

| Concern | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Ecosystem, RPi compatibility |
| Dependency management | uv | Fast, reproducible, lockfile-based |
| Image processing | Pillow (PIL) | Lightweight; no OpenCV needed on RPi |
| PDF generation | ReportLab | Proven; fine-grained layout control |
| Database | SQLite (stdlib `sqlite3`) | No server; file-based; ships with Python |
| CLI | `argparse` (stdlib) | No extra dependency; sufficient for this tool |
| Progress display | `tqdm` | Lightweight; works in headless terminals |
| Configuration | `tomllib` (stdlib, 3.11+) + `config.toml` | No extra dependency |
| Testing | `pytest` + `pytest-mock` | Standard; easy fixture support |

---

## Directory Layout

```
kamir-rewrite/
├── pyproject.toml            # Project metadata and dependencies (uv)
├── uv.lock                   # Locked dependency tree
├── config.toml               # Runtime configuration (paths, sets, API settings)
├── CLAUDE.md                 # Claude Code project rules
├── docs/
│   ├── requirements.md
│   └── architecture.md
├── kamir/
│   ├── __init__.py
│   ├── __main__.py           # `python -m kamir` entry point
│   ├── cli.py                # Argument parsing and stage dispatch
│   ├── config.py             # Load and validate config.toml
│   ├── db/
│   │   ├── __init__.py
│   │   ├── load.py           # Open AllPrintings.sqlite; raw queries
│   │   └── write.py          # Create and populate kamir_cardpool.sqlite
│   ├── filter/
│   │   ├── __init__.py
│   │   └── cards.py          # Pure functions: is_creature(), allowed_set(), select_face(), …
│   ├── images/
│   │   ├── __init__.py
│   │   ├── fetch.py          # Scryfall HTTP fetch + retry logic
│   │   ├── cache.py          # Check / store / read local image cache
│   │   └── process.py        # Grayscale, resize, crop (Pillow only)
│   ├── render/
│   │   ├── __init__.py
│   │   ├── layout.py         # Card layout constants and coordinate helpers
│   │   └── pdf.py            # ReportLab PDF generation per card
│   ├── printer/
│   │   ├── __init__.py
│   │   └── send.py           # Send PDF to system printer (future)
│   └── utils/
│       ├── __init__.py
│       ├── log.py            # Logging setup (file + stdout)
│       └── progress.py       # tqdm wrapper
├── data/
│   ├── db/                   # AllPrintings.sqlite (manual download) + kamir_cardpool.sqlite
│   ├── img/                  # {mana_value}/{card_id}.jpg
│   └── pdf/                  # {mana_value}/{card_id}.pdf
├── resources/
│   └── no_image.jpg          # Placeholder for failed image fetches
├── logs/
│   └── kamir.log             # Structured run log
└── tests/
    ├── conftest.py           # Shared fixtures (in-memory SQLite, sample card dicts)
    ├── test_filter.py        # Unit tests for kamir/filter/cards.py
    ├── test_process.py       # Unit tests for image processing (no network)
    ├── test_render.py        # Unit tests for PDF layout helpers
    └── test_db.py            # Unit tests for DB write logic (in-memory SQLite)
```

---

## Module Responsibilities

### `kamir/db/`
Owns all interaction with SQLite files.

- `load.py`: Opens `AllPrintings.sqlite` in read-only mode; exposes query helpers that return plain `dict` rows. No filtering logic here.
- `write.py`: Creates `kamir_cardpool.sqlite`; writes rows produced by the filter layer. Idempotent (drops and recreates tables on each run).

### `kamir/filter/`
Pure functions only. Receives data as dicts, returns bools or transformed dicts. No I/O.

- `is_creature(card: dict) -> bool`
- `is_allowed_set(card: dict, allowed_sets: set[str]) -> bool`
- `has_valid_collector_number(card: dict) -> bool`
- `select_face(card: dict) -> dict` — picks the correct face for DFC cards
- `normalize_oracle(text: str) -> str` — strips diacritics, normalizes whitespace

### `kamir/images/`
Owns Scryfall communication and the local image cache.

- `fetch.py`: Constructs Scryfall URLs, makes HTTP requests with retry/backoff, respects rate limits. Returns raw bytes.
- `cache.py`: Determines the local path for a card's image; checks existence; writes processed bytes to disk.
- `process.py`: Pure image transformation (Pillow): grayscale → resize → crop. Input: bytes. Output: bytes.

### `kamir/render/`
Owns PDF layout. Does not access the network or the database directly.

- `layout.py`: Named constants for dimensions, margins, font sizes, coordinate offsets.
- `pdf.py`: Accepts a card dict + image bytes → produces a PDF bytes object via ReportLab. Text wrapping and dynamic font sizing live here.

### `kamir/printer/` (future)
Shells out to `lp` or equivalent to send a PDF to the system printer. Kept isolated so it can be swapped or mocked easily.

### `kamir/cli.py`
Parses arguments, loads config, wires stages together, manages progress bars and logging. Contains no business logic.

---

## Data Flow

```
AllPrintings.sqlite
        │
        ▼
   db/load.py          (raw card rows as dicts)
        │
        ▼
  filter/cards.py      (pure functions → filtered card list)
        │
        ▼
   db/write.py         (persist to kamir_cardpool.sqlite)
        │
        ▼
  images/fetch.py      (Scryfall API → raw bytes)
  images/process.py    (bytes → processed bytes)
  images/cache.py      (write to data/img/)
        │
        ▼
  render/pdf.py        (card dict + image bytes → PDF bytes)
  render/             (write to data/pdf/)
        │
        ▼
  printer/send.py      (future: lp / CUPS)
```

---

## Configuration (`config.toml`)

```toml
[paths]
mtgjson_db  = "data/db/AllPrintings.sqlite"
kamir_db    = "data/db/kamir_cardpool.sqlite"
img_dir     = "data/img"
pdf_dir     = "data/pdf"
log_file    = "logs/kamir.log"
placeholder = "resources/no_image.jpg"

[image]
width  = 100
height = 171
# Crop box applied after resize (left, upper, right, lower) on the 223x310 source
crop   = [26, 47, 197, 147]

[pdf]
card_width_mm  = 48
card_height_mm = 67

[scryfall]
base_url       = "https://api.scryfall.com"
request_delay  = 1.0   # seconds between requests

[sets]
allowed = [
  "LEA", "LEB", "2ED",
  # ... full list defined here, not in code
]
```

---

## Key Design Decisions

**1. No OpenCV.**
The reference implementation uses `cv2` for image processing. On Raspberry Pi, building OpenCV from source or using the ARM wheel is fragile. Pillow handles all required operations (grayscale, resize, crop) with no native dependencies beyond `libjpeg`.

**2. Pure functions for filtering.**
Card filtering criteria (set allowlists, layout rules, face selection) change often. Keeping them as pure functions makes them trivially testable and easy to extend without touching I/O code.

**3. Idempotent stages.**
Any stage can be interrupted (power loss, Ctrl-C) and restarted. Each stage checks for existing output before processing a card. The DB build stage is the exception: it always rebuilds from scratch (fast enough to not matter).

**4. No database ORM.**
`sqlite3` from the standard library is sufficient. An ORM would add a dependency and obscure the SQL that matters for understanding the card schema.

**5. Printer integration is isolated from day one.**
Even though it is out of scope for v1, the `kamir/printer/` package is defined now so that it never bleeds into render or CLI logic later.
