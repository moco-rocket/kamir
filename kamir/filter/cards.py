import textwrap
import unicodedata

from kamir.domain import Card

_DFC_LAYOUTS = {"transform", "meld", "modal_dfc"}
SUPPORTED_LAYOUTS = {"normal", "adventure", "leveler"} | _DFC_LAYOUTS


def is_creature(card: dict) -> bool:
    types = card.get("types", "") or ""
    return "Creature" in types


def is_allowed_set(card: dict, allowed_sets: set[str]) -> bool:
    return card.get("setCode", "") in allowed_sets


def has_valid_collector_number(card: dict) -> bool:
    try:
        int(str(card.get("number", "")))
        return True
    except ValueError:
        return False


def is_front_face(card: dict) -> bool:
    """True for single-faced cards and for the front face (side='a') of DFCs."""
    side = card.get("side")
    return side is None or side == "a"


def is_within_base_set(card: dict) -> bool:
    try:
        return int(card.get("number", 0)) <= int(card.get("baseSetSize", 0))
    except (TypeError, ValueError):
        return False


def is_funny(card: dict) -> bool:
    return bool(card.get("isFunny", 0))


def is_reprint(card: dict) -> bool:
    return bool(card.get("isReprint", 0))


def has_supported_layout(card: dict) -> bool:
    return card.get("layout", "") in SUPPORTED_LAYOUTS


def normalize_oracle(text: str) -> str:
    """Strip diacritics and normalize whitespace in oracle text."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return ascii_only


def canonical_name(card: dict) -> str:
    """Return the printable card name, preferring asciiName then faceName then name."""
    return card.get("asciiName") or card.get("faceName") or card.get("name", "")


def wrap_oracle(text: str, width: int = 39) -> str:
    """Wrap oracle text: double-spaces become paragraph breaks, lines wrap at width."""
    if not text:
        return ""
    paragraphs = text.replace("  ", "\n").split("\n")
    lines: list[str] = []
    for para in paragraphs:
        wrapped = textwrap.wrap(para, width)
        lines.extend(wrapped if wrapped else [""])
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def to_card(card: dict) -> Card:
    """Convert a raw MTGJSON card dict to a Card domain object."""
    oracle_raw = (card.get("text") or "").replace("•", "*").replace("—", "-").replace("â", "a")
    return Card(
        name=canonical_name(card),
        mana_value=int(card.get("manaValue") or 0),
        mana_cost=(card.get("manaCost") or "").replace("—", "-"),
        type_line=(card.get("type") or "").replace("—", "-"),
        oracle_text=normalize_oracle(oracle_raw),
        expansion=card.get("setCode", ""),
        power=card.get("power", "") or "",
        toughness=card.get("toughness", "") or "",
        layout=card.get("layout", ""),
        collector_number=str(card.get("number", "")),
    )


def filter_cards(raw_cards: list[dict], allowed_sets: set[str]) -> list[Card]:
    """Return filtered Card objects from raw MTGJSON dicts."""
    seen: set[str] = set()
    result: list[Card] = []

    for card in raw_cards:
        if not (
            is_creature(card)
            and is_allowed_set(card, allowed_sets)
            and is_front_face(card)
            and has_valid_collector_number(card)
            and not is_funny(card)
            and not is_reprint(card)
            and is_within_base_set(card)
            and has_supported_layout(card)
        ):
            continue

        name = canonical_name(card)
        if name in seen:
            continue
        seen.add(name)

        result.append(to_card(card))

    return result
