import random
from pathlib import Path

import pytest

from kamir.db.write import create_kamir_db, insert_cards
from kamir.domain import Card
from kamir.play.select import load_pool, select_creature, find_by_name


def _card(**overrides) -> Card:
    base = dict(
        name="Grizzly Bears",
        mana_value=2,
        mana_cost="{1}{G}",
        type_line="Creature - Bear",
        oracle_text="",
        power="2",
        toughness="2",
        expansion="2ED",
        collector_number="178",
        layout="normal",
    )
    return Card(**{**base, **overrides})


@pytest.fixture
def db_path(tmp_path) -> Path:
    path = tmp_path / "kamir_cardpool.sqlite"
    conn = create_kamir_db(path)
    insert_cards(conn, [
        _card(name="Llanowar Elves", mana_value=1, mana_cost="{G}",
              type_line="Creature - Elf Druid", oracle_text="{T}: Add {G}.",
              power="1", toughness="1", expansion="LEA", collector_number="176"),
        _card(name="Grizzly Bears", mana_value=2),
        _card(name="Craw Wurm", mana_value=6, mana_cost="{4}{G}{G}",
              type_line="Creature - Wurm", power="6", toughness="4",
              expansion="2ED", collector_number="92"),
    ])
    conn.close()
    return path


class TestLoadPool:
    def test_returns_cards_at_mana_value(self, db_path):
        pool = load_pool(db_path, 2)
        assert len(pool) == 1
        assert pool[0].name == "Grizzly Bears"

    def test_empty_for_unknown_value(self, db_path):
        assert load_pool(db_path, 99) == []

    def test_returns_card_objects(self, db_path):
        pool = load_pool(db_path, 1)
        assert isinstance(pool[0], Card)
        assert pool[0].mana_value == 1


class TestSelectCreature:
    def test_returns_card_at_mana_value(self, db_path):
        card = select_creature(db_path, 2)
        assert card is not None
        assert card.mana_value == 2

    def test_empty_pool_returns_none(self, db_path):
        assert select_creature(db_path, 99) is None

    def test_injected_rng_is_deterministic(self, db_path):
        card_a = select_creature(db_path, 2, rng=random.Random(42))
        card_b = select_creature(db_path, 2, rng=random.Random(42))
        assert card_a == card_b

    def test_default_rng_returns_valid_card(self, db_path):
        card = select_creature(db_path, 6)
        assert card is not None
        assert card.name == "Craw Wurm"


class TestFindByName:
    def test_exact_match(self, db_path):
        card = find_by_name(db_path, "Grizzly Bears")
        assert card is not None
        assert card.name == "Grizzly Bears"

    def test_case_insensitive(self, db_path):
        card = find_by_name(db_path, "grizzly bears")
        assert card is not None
        assert card.name == "Grizzly Bears"

    def test_not_found_returns_none(self, db_path):
        assert find_by_name(db_path, "Black Lotus") is None

    def test_returns_card_object(self, db_path):
        card = find_by_name(db_path, "Llanowar Elves")
        assert isinstance(card, Card)
        assert card.mana_value == 1
