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
