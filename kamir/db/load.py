import sqlite3
from pathlib import Path

# Set types that contain no sanctioned physical-game cards.
_EXCLUDED_SET_TYPES = frozenset({
    "alchemy", "archenemy", "funny", "memorabilia", "minigame",
    "planechase", "promo", "token", "treasure_chest", "vanguard",
})


def open_source(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def all_set_codes(conn: sqlite3.Connection) -> set[str]:
    """Return every set code suitable for physical play (no Un-sets, no digital-only)."""
    placeholders = ",".join("?" * len(_EXCLUDED_SET_TYPES))
    cur = conn.cursor()
    cur.execute(
        f"SELECT code FROM sets WHERE type NOT IN ({placeholders}) AND isOnlineOnly = 0",
        tuple(_EXCLUDED_SET_TYPES),
    )
    return {row[0] for row in cur.fetchall()}


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
