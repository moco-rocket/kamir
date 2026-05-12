from kamir.domain import Card, TokenSpec
from kamir.filter.cards import wrap_oracle

_WIDTH = 64
_THICK = "=" * _WIDTH
_THIN = "-" * _WIDTH

_TOKEN_ART_LABEL = "＜ アート欄 ＞"


def _header(name: str, mana_cost: str) -> str:
    gap = _WIDTH - len(name) - len(mana_cost)
    if gap < 1:
        return f"{name}  {mana_cost}"
    return f"{name}{' ' * gap}{mana_cost}"


def _footer(expansion: str, power: str, toughness: str) -> str:
    pt = f"{power}/{toughness}"
    exp = f"[{expansion}]"
    gap = _WIDTH - len(exp) - len(pt)
    if gap < 1:
        return f"{exp}  {pt}"
    return f"{exp}{' ' * gap}{pt}"


def format_card(card: Card) -> str:
    """Format a Card as a multi-line terminal display string."""
    oracle = wrap_oracle(card.oracle_text, width=_WIDTH - 2) or "(no text)"
    oracle_block = "\n".join(f"  {line}" for line in oracle.split("\n"))

    return "\n".join([
        _THICK,
        _header(card.name, card.mana_cost),
        _THICK,
        f"  {card.type_line}",
        _THIN,
        oracle_block,
        _THIN,
        _footer(card.expansion, card.power, card.toughness),
        _THICK,
    ])


def _centered(text: str) -> str:
    pad = (_WIDTH - len(text)) // 2
    return " " * max(0, pad) + text


def format_token(spec: TokenSpec) -> str:
    """Format a TokenSpec as a terminal display string matching the printed token layout."""
    pt = f"{spec.power}/{spec.toughness}" if (spec.power and spec.toughness) else (spec.power or spec.toughness or "?/?")

    oracle = wrap_oracle(spec.oracle_text, width=_WIDTH - 2)
    if oracle:
        oracle_section = "\n".join([_THIN, *[f"  {line}" for line in oracle.split("\n")], _THIN])
    else:
        oracle_section = ""

    lines = [
        _THICK,
        _centered(spec.name),
        _THICK,
        "",
        _centered(_TOKEN_ART_LABEL),
        "",
        _THICK,
        _centered(pt),
        _THICK,
        f"  {spec.type_line}",
    ]
    if oracle_section:
        lines.append(oracle_section)
    lines.append(_THICK)
    return "\n".join(lines)
