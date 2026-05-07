import sqlite3
from pathlib import Path


def open_source(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def iter_raw_cards(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            c.name,
            c.faceName,
            c.asciiName,
            c.manaValue,
            c.manaCost,
            c.type,
            c.types,
            c.text,
            c.setCode,
            c.power,
            c.toughness,
            c.layout,
            c.number,
            c.side,
            c.isFunny,
            c.isReprint,
            s.baseSetSize
        FROM cards c
        JOIN sets s ON c.setCode = s.code
        """
    )
    return [dict(row) for row in cur.fetchall()]
