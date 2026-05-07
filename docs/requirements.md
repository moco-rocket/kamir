# Kamir — Requirements

## Overview

Kamir is an interactive tabletop tool for playing Momir Basic in paper using a Raspberry Pi
and an MJ-5890K thermal printer. A player declares a mana value, discards a land, and Kamir
randomly selects a creature from the card pool, displays its information, and prints a
readable card-like slip on the thermal printer. The slip is placed on the table as the token.

The system does **not** implement any MTG rules engine. Life totals, combat, and all other
game actions are handled by the players themselves.

---

## Subsystems

Kamir is composed of three independent subsystems that share a common domain model:

| Subsystem | When it runs | Primary user |
|---|---|---|
| **Database Builder** | One-time setup, or after a card pool update | Operator |
| **Play App** | During a game session | Player |
| **Printing/Rendering** | On demand, triggered by the Play App | Triggered automatically |

---

## Functional Requirements

### F1 — Database Builder

The database builder is a setup-time operation, not part of the play loop.

- Load `AllPrintings.sqlite` from the local filesystem (downloaded separately from mtgjson.com).
- Filter cards to the Momir-eligible creature pool:
  - Only creatures with a valid whole-number mana value (0–15 inclusive).
  - Only cards from the allowed set list defined in `config.toml`.
  - Exclude joke sets, non-base-set collector numbers, and non-front faces of DFCs.
  - Exclude reprints: keep only the first printed version of each unique creature name.
  - Supported layouts: `normal`, `adventure`, `transform`, `meld`, `modal_dfc`, `leveler`.
- Write filtered results to `kamir_cardpool.sqlite` in the configured data directory.
- Re-running the builder rebuilds the database from scratch (idempotent).
- Display a progress indicator during the build.

### F2 — Play App

The play app is the primary user-facing feature.

- Present the player with a prompt to enter a mana value (integer 0–15).
- Validate the input and report clearly if no creatures exist at that mana value.
- Randomly select one creature from the pool at the given mana value (uniform distribution).
- Display the selected card's information in the terminal:
  - Name, mana cost, type line, oracle text, power/toughness.
- Ask the player to confirm before printing (or auto-print if configured).
- After printing, return to the prompt for the next selection.
- Support a clean exit (Ctrl-C or `q`).

### F3 — Printing/Rendering

The printed output is a readable re-composition of card information, **not** a copy of the
original card artwork or frame.

- Compose a text-based card layout from the selected creature's data:
  - Card name (bold, prominent)
  - Mana cost
  - Type line
  - Oracle text (word-wrapped to printer width)
  - Power/Toughness (bold, prominent)
- Send the composed layout to the MJ-5890K thermal printer via ESC/POS protocol.
- The layout must be readable during a tabletop game at arm's length.
- Paper usage per card: minimal (a few centimetres of 58mm receipt paper).
- No artwork is fetched, stored, or printed.

### F4 — CLI

- `kamir build-db` — run the database builder.
- `kamir play` — enter interactive play mode.
- `kamir print-test --mv X` — select a random card at mana value X and print it
  (for hardware setup and testing, no confirmation prompt).
- `kamir --debug <command>` — enable verbose logging.
- `kamir --config <path>` — use an alternative `config.toml`.

---

## Non-Functional Requirements

### NFR1 — Platform
- Target: Raspberry Pi OS Bookworm (64-bit), headless (no display).
- Python 3.11 or later.
- Dependency management via `uv`.

### NFR2 — Resumability
- The database builder must be safe to interrupt and re-run.
- The play loop must not leave the system in an inconsistent state on Ctrl-C.

### NFR3 — Lightweight Dependencies
- Do not use OpenCV. Use Pillow only if image manipulation is required elsewhere.
- Minimize dependencies that require large compiled C extensions.
- The play-path dependencies (play + printer) must install cleanly on Raspberry Pi OS Bookworm arm64.

### NFR4 — Testability
- Filter logic must be pure functions testable without I/O.
- Card selection (random) must accept an injectable random source for deterministic tests.
- Printer rendering must be testable without hardware (text output only in tests).
- No network access in tests.

### NFR5 — Configuration
- All tunable parameters (allowed sets, printer device path, mana value bounds) are in `config.toml`.
- No hardcoded values in production code.

### NFR6 — Randomness
- Card selection within a mana value must be uniformly random.
- The random seed must not be fixed in production (use system entropy).

---

## Out of Scope

- Graphical user interface or web interface.
- MTG rules enforcement (stack, combat, triggered abilities, life totals).
- Scryfall image fetching or any artwork reproduction.
- PDF generation.
- Online multiplayer or any network play.
- Support for non-creature card types.
- Automatic download of `AllPrintings.sqlite`.
- GPIO or physical button integration (deferred to a future phase).
