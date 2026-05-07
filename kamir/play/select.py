import random
import sqlite3
from pathlib import Path

from kamir.domain import Card


def _row_to_card(row: sqlite3.Row) -> Card:
    return Card(**{col: row[col] for col in row.keys()})


def load_pool(db_path: Path, mana_value: int) -> list[Card]:
    """Return all cards at the given mana value from the card pool DB."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """SELECT name, mana_value, mana_cost, type_line, oracle_text,
                  expansion, power, toughness, layout, collector_number
           FROM cards WHERE mana_value = ? ORDER BY name""",
        (mana_value,),
    )
    rows = cur.fetchall()
    conn.close()
    return [_row_to_card(row) for row in rows]


def select_creature(
    db_path: Path,
    mana_value: int,
    rng: random.Random | None = None,
) -> Card | None:
    """Return a uniformly random Card at mana_value, or None if the pool is empty."""
    pool = load_pool(db_path, mana_value)
    if not pool:
        return None
    if rng is None:
        rng = random.Random()
    return rng.choice(pool)


def find_by_name(db_path: Path, name: str) -> Card | None:
    """Return the Card with the given name (case-insensitive), or None if not found."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """SELECT name, mana_value, mana_cost, type_line, oracle_text,
                  expansion, power, toughness, layout, collector_number
           FROM cards WHERE name = ? COLLATE NOCASE""",
        (name,),
    )
    row = cur.fetchone()
    conn.close()
    return _row_to_card(row) if row else None
