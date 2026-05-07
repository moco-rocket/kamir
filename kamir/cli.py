import argparse
import logging
import sqlite3
from pathlib import Path

import requests

from kamir import config as cfg_mod
from kamir.db.load import open_source, iter_raw_cards
from kamir.db.write import create_kamir_db, insert_cards
from kamir.filter.cards import filter_cards
from kamir.images.cache import fetch_and_cache, is_cached, image_path
from kamir.render.pdf import write_card_pdf
from kamir.utils import log as log_mod
from kamir.utils.progress import track

log = logging.getLogger(__name__)


def _resolve(cfg: dict, root: Path) -> dict:
    """Make all configured paths absolute relative to root."""
    paths = {k: root / v for k, v in cfg["paths"].items()}
    return {**cfg, "paths": paths}


def stage_build_db(cfg: dict) -> None:
    paths = cfg["paths"]
    allowed = set(cfg["sets"]["allowed"])

    log.info("Opening source database: %s", paths["mtgjson_db"])
    src_conn = open_source(paths["mtgjson_db"])
    raw_cards = iter_raw_cards(src_conn)
    src_conn.close()

    log.info("Filtering %d raw cards", len(raw_cards))
    filtered = filter_cards(raw_cards, allowed)
    log.info("%d cards passed filter", len(filtered))

    dest_conn = create_kamir_db(paths["kamir_db"])
    insert_cards(dest_conn, filtered)
    dest_conn.close()
    log.info("Database written: %s", paths["kamir_db"])


def stage_fetch_images(cfg: dict) -> None:
    paths = cfg["paths"]
    img_cfg = cfg["image"]
    scryfall = cfg["scryfall"]

    resize = (img_cfg["resize_w"], img_cfg["resize_h"])
    crop = tuple(img_cfg["crop"])

    conn = sqlite3.connect(paths["kamir_db"])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT name, expansion, number, mana_value, layout FROM cards ORDER BY mana_value, name"
    )
    cards = [dict(row) for row in cur.fetchall()]
    conn.close()

    session = requests.Session()
    to_fetch = [c for c in cards if not is_cached(paths["img_dir"], c)]
    log.info("%d images to fetch (%d already cached)", len(to_fetch), len(cards) - len(to_fetch))

    for card in track(to_fetch, desc="Fetching images"):
        fetch_and_cache(
            card,
            img_dir=paths["img_dir"],
            placeholder=paths["placeholder"],
            base_url=scryfall["base_url"],
            session=session,
            resize=resize,
            crop=crop,
            request_delay=scryfall["request_delay"],
        )


def stage_make_pdfs(cfg: dict) -> None:
    paths = cfg["paths"]

    conn = sqlite3.connect(paths["kamir_db"])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM cards ORDER BY mana_value, name")
    cards = [dict(row) for row in cur.fetchall()]
    conn.close()

    mv_str = lambda c: str(c["mana_value"])
    safe = lambda c: c["name"].replace("/", "-")
    to_render = [
        c for c in cards
        if not (paths["pdf_dir"] / mv_str(c) / f"{safe(c)}.pdf").exists()
    ]
    log.info("%d PDFs to render (%d already done)", len(to_render), len(cards) - len(to_render))

    for card in track(to_render, desc="Rendering PDFs"):
        img = image_path(paths["img_dir"], card)
        if not img.exists():
            log.warning("Missing image for '%s', skipping PDF", card["name"])
            continue
        write_card_pdf(card, img, paths["pdf_dir"])


def main() -> None:
    parser = argparse.ArgumentParser(prog="kamir", description="Kamir proxy card generator")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("build-db", help="Stage 1: build kamir_cardpool.sqlite")
    sub.add_parser("fetch-images", help="Stage 2: fetch card images from Scryfall")
    sub.add_parser("make-pdfs", help="Stage 3: render proxy PDFs")
    sub.add_parser("run", help="Run all stages in sequence")

    args = parser.parse_args()

    raw_cfg = cfg_mod.load(args.config)
    root = (args.config.parent if args.config else Path(".")).resolve()
    cfg = _resolve(raw_cfg, root)

    log_mod.setup(cfg["paths"]["log_file"], level=logging.DEBUG if args.debug else logging.INFO)

    stages = {
        "build-db": stage_build_db,
        "fetch-images": stage_fetch_images,
        "make-pdfs": stage_make_pdfs,
    }

    if args.stage == "run":
        for name, fn in stages.items():
            log.info("=== Stage: %s ===", name)
            fn(cfg)
    else:
        stages[args.stage](cfg)
