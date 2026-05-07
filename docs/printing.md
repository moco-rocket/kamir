# Kamir — Printing Guide

## Target Hardware: MJ-5890K

The MJ-5890K is a compact 58mm thermal receipt printer. Key specifications relevant to Kamir:

| Property | Value |
|---|---|
| Paper width | 58mm |
| Printable width | ~48mm (384 dots at 8 dots/mm) |
| Resolution | 203 DPI |
| Protocol | ESC/POS (standard thermal receipt protocol) |
| Connection | USB (appears as `/dev/usb/lp0` on Linux) |
| Default character width | 32 characters per line (Font A) |
| Character width (Font B) | ~42 characters per line (smaller font) |

On Raspberry Pi OS, the printer is accessible without a CUPS driver. The raw USB device
(`/dev/usb/lp0`) can be written to directly using ESC/POS byte sequences.

---

## Printed Card Layout

The printed slip is a **re-composed text representation** of the card. It is not a copy of
the original card frame or artwork. The layout is designed to be readable at arm's length
during a tabletop game.

### Layout Specification

```
                                  ← 3 blank lines (leading margin)
================================  ← full-width rule (=)
FERVENT CHAMPION           {R}    ← name (bold, uppercase) + mana cost (right)
================================
Creature - Human Knight           ← type line
--------------------------------  ← thin rule (-)
Haste.
Whenever Fervent Champion
attacks, another target attacking
Knight you control gains first
strike until end of turn.
Equip abilities you activate that
target Fervent Champion cost
{2} less.
--------------------------------
[ELD]                        1/1  ← expansion + P/T (bold, right-aligned)
================================  ← closing rule
                                  ← 3 blank lines before paper cut
```

### Design Rules

- **Width**: 32 characters (Font A). Every line of text wraps at 32 characters.
- **Name**: uppercase, bold, left-aligned. Truncated to fit on one line if necessary.
- **Mana cost**: right-aligned on the same line as the name.
  If name + mana cost exceed 32 chars, the mana cost moves to its own line.
- **Type line**: normal weight, below the header rule.
- **Oracle text**: normal weight, word-wrapped at 32 chars. Paragraphs separated by a
  blank line. Keyword abilities are listed one per line. MTGJSON stores ability
  separators as the two-character sequence `\n`; these are normalized to line breaks
  before rendering.
- **P/T**: bold, right-aligned on the bottom line with the expansion code left-aligned.
  Format: `N/N`.
- **Rules**: `=` lines use the full width; `-` lines use the full width.
- **Mana symbols**: rendered as `{W}`, `{U}`, `{B}`, `{R}`, `{G}`, `{X}`, etc.
  (the same notation used in oracle text). No Unicode glyphs are used, as thermal
  printer character encoding support is inconsistent.
- **Paper cut**: a full cut is issued after 3 blank lines following the closing rule.
  3 blank lines also precede the opening rule. This margin prevents the paper cutter
  from clipping text on either edge of the slip.

### Example Output (32-char width)

```
================================
SERRA ANGEL            {3}{W}{W}
================================
Creature - Angel
--------------------------------
Flying, vigilance
--------------------------------
[ALL]                        4/4
================================
```

```
================================
EMRAKUL, THE AEONS TORN {15}
================================
Creature - Eldrazi
--------------------------------
This spell can't be countered.
When you cast this spell, take
an extra turn after this one.
Flying, protection from colored
spells, annihilator 6
Emrakul can't be blocked except
by three or more creatures.
--------------------------------
[ROE]                      15/15
================================
```

---

## Hardware Setup on Raspberry Pi

1. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/moco-rocket/kamir.git
   cd kamir
   uv sync
   ```
3. Create `config.toml` in the project root (see README for the full template).
4. Place `AllPrintings.sqlite` in `data/db/` and build the card pool:
   ```bash
   mkdir -p data/db
   mv AllPrintings.sqlite data/db/
   kamir build-db
   ```
5. Connect the MJ-5890K to the Raspberry Pi via USB.
6. Verify the device is recognized:
   ```bash
   ls /dev/usb/lp*
   lsusb | grep -i thermal
   ```
7. Grant the `kamir` user access to the printer device (log out and back in after):
   ```bash
   sudo usermod -aG lp $USER
   ```
8. Test the connection:
   ```bash
   kamir print-test --mv 4
   ```

---

## Why Not PDF or Bitmap?

See [`docs/adr/0002-printing-strategy.md`](adr/0002-printing-strategy.md) for the full
decision record. In summary:

- PDF printing via CUPS is fragile on headless Raspberry Pi and adds complex dependencies.
- Printing a bitmap scan of the original card frame raises artwork copyright concerns and
  produces poor output on the coarse thermal paper surface.
- A text re-render is faster (< 1 second), uses minimal paper, has no licensing concern,
  and is actually more legible for game purposes than a small scaled-down card image.
