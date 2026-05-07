import sqlite3

import pytest

from kamir.domain import Card
from kamir.db.write import create_kamir_db, insert_cards


@pytest.fixture
def kamir_conn(tmp_path):
    db_path = tmp_path / "kamir_cardpool.sqlite"
    conn = create_kamir_db(db_path)
    yield conn
    conn.close()


def _sample_card(**overrides) -> Card:
    base = dict(
        name="Grizzly Bears",
        mana_value=2,
        mana_cost="{1}{G}",
        type_line="Creature - Bear",
        oracle_text="No abilities.",
        expansion="2ED",
        power="2",
        toughness="2",
        layout="normal",
        collector_number="178",
    )
    return Card(**{**base, **overrides})


class TestCreateKamirDb:
    def test_cards_table_exists(self, kamir_conn):
        cur = kamir_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        assert "cards" in tables

    def test_preserves_existing_rows_on_reopen(self, tmp_path):
        # Calling create_kamir_db on an existing DB must not wipe stored data
        # (art_raster blobs in particular would otherwise be lost on every rebuild).
        path = tmp_path / "test.sqlite"
        conn1 = create_kamir_db(path)
        insert_cards(conn1, [_sample_card()])
        conn1.close()

        conn2 = create_kamir_db(path)
        cur = conn2.cursor()
        cur.execute("SELECT COUNT(*) FROM cards")
        assert cur.fetchone()[0] == 1
        conn2.close()


class TestInsertCards:
    def test_insert_single(self, kamir_conn):
        insert_cards(kamir_conn, [_sample_card()])
        cur = kamir_conn.cursor()
        cur.execute("SELECT name, mana_value FROM cards")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "Grizzly Bears"
        assert rows[0][1] == 2

    def test_insert_multiple(self, kamir_conn):
        cards = [_sample_card(), _sample_card(name="Llanowar Elves", mana_value=1)]
        insert_cards(kamir_conn, cards)
        cur = kamir_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cards")
        assert cur.fetchone()[0] == 2

    def test_duplicate_name_ignored(self, kamir_conn):
        card = _sample_card()
        insert_cards(kamir_conn, [card, card])
        cur = kamir_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cards")
        assert cur.fetchone()[0] == 1

    def test_all_fields_stored(self, kamir_conn):
        insert_cards(kamir_conn, [_sample_card()])
        cur = kamir_conn.cursor()
        cur.execute("SELECT * FROM cards WHERE name = 'Grizzly Bears'")
        row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert row["mana_cost"] == "{1}{G}"
        assert row["type_line"] == "Creature - Bear"
        assert row["oracle_text"] == "No abilities."
        assert row["expansion"] == "2ED"
        assert row["power"] == "2"
        assert row["toughness"] == "2"
        assert row["layout"] == "normal"
        assert row["collector_number"] == "178"
