import argparse
import logging
from pathlib import Path

from kamir import config as cfg_mod
from kamir.db.load import open_source, iter_raw_cards
from kamir.db.write import create_kamir_db, insert_cards
from kamir.filter.cards import filter_cards
from kamir.play.display import format_card
from kamir.play.select import select_creature
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


def stage_play(cfg: dict) -> None:
    db_path = cfg["paths"]["kamir_db"]
    auto_print = cfg.get("play", {}).get("auto_print", False)

    if not db_path.exists():
        print("  カードプールが見つかりません。先に 'kamir build-db' を実行してください。")
        log.error("Card pool not found at %s. Run 'kamir build-db' first.", db_path)
        return

    print("Kamir — Momir Basic  (終了: q または Ctrl-C)")
    print()

    while True:
        try:
            raw = input("マナ総量 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if raw.lower() in ("q", "quit", "exit"):
            break

        try:
            mv = int(raw)
        except ValueError:
            print("  整数を入力してください。")
            continue

        if mv < 0:
            print("  0 以上の整数を入力してください。")
            continue

        card = select_creature(db_path, mv)
        if card is None:
            print(f"  マナ総量 {mv} のクリーチャーはプールに存在しません。")
            continue

        print()
        print(format_card(card))
        print()

        if not auto_print:
            try:
                confirm = input("  印刷しますか？ [y/N] > ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if confirm != "y":
                continue

        # Phase 3: printer.send.print_card(card, cfg["printer"])
        print("  (印刷機能は Phase 3 で実装予定)")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kamir",
        description="Kamir — Momir Basic play tool for Raspberry Pi",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build-db", help="Build kamir_cardpool.sqlite from AllPrintings.sqlite")
    sub.add_parser("play", help="Start an interactive Momir Basic play session")

    args = parser.parse_args()

    raw_cfg = cfg_mod.load(args.config)
    root = (args.config.parent if args.config else Path(".")).resolve()
    cfg = _resolve(raw_cfg, root)

    log_mod.setup(cfg["paths"]["log_file"], level=logging.DEBUG if args.debug else logging.INFO)

    if args.command == "build-db":
        stage_build_db(cfg)
    elif args.command == "play":
        stage_play(cfg)
