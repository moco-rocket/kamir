import logging
import sqlite3
import time
from pathlib import Path

from tqdm import tqdm

from kamir.domain import Card
from kamir.printer.image import (
    HEIGHT_DOTS,
    WIDTH_DOTS,
    batch_fetch_art_crop_urls,
    fetch_art_from_url,
)
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

        # Phase 1 — batch-fetch art_crop URLs (fast: ~N/75 API requests)
        n_batches = (total + 74) // 75
        log.info("Art: fetching metadata for %d cards (%d batches)...", total, n_batches)
        art_urls = batch_fetch_art_crop_urls(pending)
        log.info("Art: %d/%d URLs resolved", len(art_urls), total)

        # Phase 2 — download images (slow: one CDN request per card)
        ok = 0
        with tqdm(pending, desc="Art", unit="card", ncols=80, dynamic_ncols=True) as bar:
            for card in bar:
                url = art_urls.get(card.name)
                if url:
                    art = fetch_art_from_url(url)
                    if art is not None:
                        cur.execute(
                            "UPDATE cards SET art_raster = ? WHERE name = ?",
                            (art.data, card.name),
                        )
                        conn.commit()
                        ok += 1
                bar.set_postfix(ok=ok, fail=bar.n - ok)

        tqdm.write(f"Art: complete — {ok}/{total} images stored")
        log.info("Art: complete — %d/%d images stored", ok, total)
        if ok == 0:
            log.warning(
                "Art: no images were stored — check network access, "
                "or re-run `kamir build-db` once the network is available"
            )
    finally:
        conn.close()


def art_stats(db_path: Path) -> tuple[int, int] | None:
    """Return (total_cards, cards_with_art), or None if the DB doesn't exist or is incompatible."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total, COUNT(art_raster) AS with_art FROM cards"
        ).fetchone()
        return (row[0], row[1])
    except sqlite3.OperationalError:
        return None
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
                width_bytes=WIDTH_DOTS // 8,
                height=HEIGHT_DOTS,
            )
        return None
    except sqlite3.OperationalError:
        # art_raster column absent — DB was built before art support was added.
        # Run `kamir build-db` to rebuild with the current schema.
        log.warning("art_raster column missing — run `kamir build-db` to download art")
        return None
    finally:
        conn.close()
