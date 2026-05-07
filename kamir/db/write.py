import sqlite3
from pathlib import Path

_CREATE_CARDS = """
CREATE TABLE cards (
    name         TEXT PRIMARY KEY,
    mana_value   INTEGER,
    mana_cost    TEXT,
    type         TEXT,
    oracle       TEXT,
    expansion    TEXT,
    power        TEXT,
    toughness    TEXT,
    layout       TEXT,
    number       TEXT,
    release_date TEXT
)
"""

_CREATE_EXPANSIONS = """
CREATE TABLE expansions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name_code    TEXT,
    base_set_size INTEGER,
    release_date TEXT
)
"""


def create_kamir_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS cards")
    cur.execute("DROP TABLE IF EXISTS expansions")
    cur.execute(_CREATE_CARDS)
    cur.execute(_CREATE_EXPANSIONS)
    conn.commit()
    return conn


def insert_cards(conn: sqlite3.Connection, cards: list[dict]) -> None:
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR IGNORE INTO cards
            (name, mana_value, mana_cost, type, oracle,
             expansion, power, toughness, layout, number, release_date)
        VALUES
            (:name, :mana_value, :mana_cost, :type, :oracle,
             :expansion, :power, :toughness, :layout, :number, :release_date)
        """,
        cards,
    )
    conn.commit()
