from dataclasses import dataclass


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


@dataclass(frozen=True)
class TokenSpec:
    name: str
    type_line: str
    power: str
    toughness: str
    oracle_text: str = ""


def card_to_token_spec(card: Card) -> TokenSpec:
    return TokenSpec(
        name=card.name,
        type_line=card.type_line,
        power=card.power,
        toughness=card.toughness,
        oracle_text=card.oracle_text,
    )
