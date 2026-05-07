from dataclasses import dataclass

from kamir.domain import Card
from kamir.filter.cards import wrap_oracle

_PRINTER_WIDTH = 32


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
