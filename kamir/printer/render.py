from dataclasses import dataclass

from kamir.domain import Card, TokenSpec
from kamir.filter.cards import wrap_oracle

_PRINTER_WIDTH = 32

# Blank lines used as the art drawing space when no art image is provided.
# Chosen to approximate the physical height of a 192-dot Scryfall art raster
# at the default ESC/POS line spacing (~30 dots/line).
_TOKEN_ART_LINES = 6


@dataclass(frozen=True)
class TextLine:
    text: str
    bold: bool = False


@dataclass(frozen=True)
class Rule:
    thick: bool = True  # True = "=", False = "-"


@dataclass(frozen=True)
class Cut:
    pass


@dataclass(frozen=True)
class RasterImage:
    data: bytes       # 1-bit packed bitmap, ESC/POS polarity (1=print)
    width_bytes: int  # dots / 8
    height: int       # dots


Instruction = TextLine | Rule | Cut | RasterImage


def _header(name: str, mana_cost: str) -> list[TextLine]:
    name_upper = name.upper()
    gap = _PRINTER_WIDTH - len(name_upper) - len(mana_cost)
    if gap >= 1:
        return [TextLine(f"{name_upper}{' ' * gap}{mana_cost}", bold=True)]
    # Name and cost do not fit on one line; cost drops to its own line.
    return [TextLine(name_upper, bold=True), TextLine(mana_cost, bold=True)]


def _footer(expansion: str, power: str, toughness: str) -> TextLine:
    pt = f"{power}/{toughness}" if (power or toughness) else ""
    exp = f"[{expansion}]"
    gap = _PRINTER_WIDTH - len(exp) - len(pt)
    if gap >= 1:
        return TextLine(f"{exp}{' ' * gap}{pt}")
    return TextLine(f"{exp}  {pt}")


def render_card(card: Card, art: RasterImage | None = None) -> list[Instruction]:
    """Convert a Card to an ordered list of ESC/POS print instructions."""
    out: list[Instruction] = []

    out.append(TextLine(""))
    out.append(Rule(thick=True))
    out.extend(_header(card.name, card.mana_cost))
    out.append(Rule(thick=True))
    if art is not None:
        out.append(art)
        out.append(Rule(thick=False))
    out.append(TextLine(card.type_line))
    out.append(Rule(thick=False))

    oracle = wrap_oracle(card.oracle_text, width=_PRINTER_WIDTH) or "(no text)"
    for line in oracle.split("\n"):
        out.append(TextLine(line))

    out.append(Rule(thick=False))
    out.append(_footer(card.expansion, card.power, card.toughness))
    out.append(Rule(thick=True))
    for _ in range(3):
        out.append(TextLine(""))
    out.append(Cut())

    return out


def _name_centered(name: str) -> TextLine:
    pad = (_PRINTER_WIDTH - len(name)) // 2
    return TextLine(" " * max(0, pad) + name, bold=True)


def _pt_centered(power: str, toughness: str) -> TextLine:
    pt = f"{power}/{toughness}" if (power and toughness) else (power or toughness or "?/?")
    pad = (_PRINTER_WIDTH - len(pt)) // 2
    return TextLine(" " * max(0, pad) + pt, bold=True)


def render_token(spec: TokenSpec, art: RasterImage | None = None) -> list[Instruction]:
    """Convert a TokenSpec to an ESC/POS instruction list.

    Layout: centred name → fixed-height art space (or blank drawing area) →
    bold P/T → type line → optional oracle text → cut.
    When art is None, blank lines fill the same approximate space so all
    tokens print at the same physical height.
    """
    out: list[Instruction] = []

    out.append(TextLine(""))
    out.append(Rule(thick=True))
    out.append(_name_centered(spec.name))
    out.append(Rule(thick=True))

    if art is not None:
        out.append(art)
    else:
        for _ in range(_TOKEN_ART_LINES):
            out.append(TextLine(""))

    out.append(Rule(thick=True))
    out.append(_pt_centered(spec.power, spec.toughness))
    out.append(Rule(thick=True))
    out.append(TextLine(spec.type_line))

    oracle = wrap_oracle(spec.oracle_text, width=_PRINTER_WIDTH)
    if oracle:
        out.append(Rule(thick=False))
        for line in oracle.split("\n"):
            out.append(TextLine(line))
        out.append(Rule(thick=False))

    out.append(Rule(thick=True))
    for _ in range(3):
        out.append(TextLine(""))
    out.append(Cut())

    return out
