import argparse
import logging
from pathlib import Path

from kamir import config as cfg_mod
from kamir.db.load import open_source, iter_raw_cards
from kamir.db.write import create_kamir_db, insert_cards
from kamir.filter.cards import filter_cards
from kamir.utils import log as log_mod

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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kamir",
        description="Kamir — Momir Basic play tool for Raspberry Pi",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build-db", help="Build kamir_cardpool.sqlite from AllPrintings.sqlite")

    args = parser.parse_args()

    raw_cfg = cfg_mod.load(args.config)
    root = (args.config.parent if args.config else Path(".")).resolve()
    cfg = _resolve(raw_cfg, root)

    log_mod.setup(cfg["paths"]["log_file"], level=logging.DEBUG if args.debug else logging.INFO)

    if args.command == "build-db":
        stage_build_db(cfg)
