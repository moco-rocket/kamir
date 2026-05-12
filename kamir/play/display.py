from kamir.domain import Card
from kamir.filter.cards import wrap_oracle

_WIDTH = 64
_THICK = "=" * _WIDTH
_THIN = "-" * _WIDTH


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


def _pt_centered(power: str, toughness: str) -> str:
    pt = f"{power}/{toughness}" if (power and toughness) else (power or toughness or "?/?")
    pad = (_WIDTH - len(pt)) // 2
    return " " * pad + pt


def _token_footer(name: str, expansion: str) -> str:
    exp = f"[{expansion}]"
    gap = _WIDTH - len(name) - len(exp)
    if gap < 1:
        return f"{name}  {exp}"
    return f"{name}{' ' * gap}{exp}"


def format_token(card: Card) -> str:
    """Format a Card as a token-layout terminal display string (P/T first)."""
    oracle = wrap_oracle(card.oracle_text, width=_WIDTH - 2) or "(no text)"
    oracle_block = "\n".join(f"  {line}" for line in oracle.split("\n"))

    return "\n".join([
        _THICK,
        _pt_centered(card.power, card.toughness),
        _THICK,
        f"  {card.type_line}",
        _THIN,
        oracle_block,
        _THIN,
        _token_footer(card.name, card.expansion),
        _THICK,
    ])
