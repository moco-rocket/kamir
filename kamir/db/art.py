import logging
import sqlite3
from pathlib import Path

from kamir.domain import Card
from kamir.printer.image import _HEIGHT_DOTS, _WIDTH_DOTS, fetch_art
from kamir.printer.render import RasterImage

log = logging.getLogger(__name__)


def fetch_and_store_art(db_path: Path, cards: list[Card]) -> None:
    """Download card art from Scryfall and cache as ESC/POS raster in the DB.

    Skips cards that already have art stored. Safe to call repeatedly.
    Failures per card are silently skipped (art will be absent for that card).
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        pending = [
            c for c in cards
            if cur.execute(
                "SELECT art_raster FROM cards WHERE name = ?", (c.name,)
            ).fetchone()[0] is None
        ]
        total = len(pending)
        if total == 0:
            log.info("Art: all %d cards already cached", len(cards))
            return

        log.info("Art: downloading %d cards...", total)
        ok = 0
        for i, card in enumerate(pending, 1):
            art = fetch_art(card)
            if art is not None:
                cur.execute(
                    "UPDATE cards SET art_raster = ? WHERE name = ?",
                    (art.data, card.name),
                )
                conn.commit()
                ok += 1
            if i % 100 == 0:
                log.info("Art: %d/%d (%d stored)", i, total, ok)

        log.info("Art: complete — %d/%d images stored", ok, total)
    finally:
        conn.close()


def load_art(db_path: Path, card: Card) -> RasterImage | None:
    """Load cached card art raster from the DB, or None if not available."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT art_raster FROM cards WHERE name = ?", (card.name,)
        ).fetchone()
        if row and row[0] is not None:
            return RasterImage(
                data=bytes(row[0]),
                width_bytes=_WIDTH_DOTS // 8,
                height=_HEIGHT_DOTS,
            )
        return None
    finally:
        conn.close()
