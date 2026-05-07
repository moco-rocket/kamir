import dataclasses
import sqlite3
from pathlib import Path

from kamir.domain import Card

_CREATE_CARDS = """
CREATE TABLE IF NOT EXISTS cards (
    name             TEXT PRIMARY KEY,
    mana_value       INTEGER,
    mana_cost        TEXT,
    type_line        TEXT,
    oracle_text      TEXT,
    expansion        TEXT,
    power            TEXT,
    toughness        TEXT,
    layout           TEXT,
    collector_number TEXT,
    art_raster       BLOB
)
"""


def create_kamir_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(_CREATE_CARDS)
    conn.commit()
    return conn


def insert_cards(conn: sqlite3.Connection, cards: list[Card]) -> None:
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR IGNORE INTO cards
            (name, mana_value, mana_cost, type_line, oracle_text,
             expansion, power, toughness, layout, collector_number)
        VALUES
            (:name, :mana_value, :mana_cost, :type_line, :oracle_text,
             :expansion, :power, :toughness, :layout, :collector_number)
        """,
        [dataclasses.asdict(c) for c in cards],
    )
    conn.commit()
