import argparse
import logging
from pathlib import Path

from kamir import config as cfg_mod
from kamir.db.art import art_stats, fetch_and_store_art, load_art
from kamir.db.load import open_source, iter_raw_cards
from kamir.db.write import create_kamir_db, insert_cards
from kamir.filter.cards import filter_cards
from kamir.play.display import format_card
from kamir.play.select import select_creature
from kamir.printer.send import print_card
from kamir.utils import log as log_mod

log = logging.getLogger(__name__)


def _resolve(cfg: dict, root: Path) -> dict:
    """Make all configured paths absolute relative to root."""
    paths = {k: root / v for k, v in cfg["paths"].items()}
    return {**cfg, "paths": paths}


def stage_build_db(cfg: dict, force: bool = False) -> None:
    paths = cfg["paths"]
    allowed = set(cfg["sets"]["allowed"])

    log.info("Opening source database: %s", paths["mtgjson_db"])
    src_conn = open_source(paths["mtgjson_db"])
    raw_cards = iter_raw_cards(src_conn)
    src_conn.close()

    log.info("Filtering %d raw cards", len(raw_cards))
    filtered = filter_cards(raw_cards, allowed)
    log.info("%d cards passed filter", len(filtered))

    if force:
        log.info("--force: dropping existing DB")
    dest_conn = create_kamir_db(paths["kamir_db"], force=force)
    insert_cards(dest_conn, filtered)
    dest_conn.close()
    log.info("Database written: %s", paths["kamir_db"])

    fetch_and_store_art(paths["kamir_db"], filtered)


def stage_play(cfg: dict) -> None:
    db_path = cfg["paths"]["kamir_db"]
    device = cfg["printer"]["device"]

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

        try:
            print_card(card, device, load_art(db_path, card))
            log.info("Printed: %s (MV %d)", card.name, card.mana_value)
        except OSError as e:
            print(f"  印刷エラー: {e}")
            log.error("Print failed for '%s': %s", card.name, e)


def stage_art_status(cfg: dict) -> None:
    db_path = cfg["paths"]["kamir_db"]
    stats = art_stats(db_path)
    if stats is None:
        print("  カードプールが見つかりません。先に 'kamir build-db' を実行してください。")
        return
    total, with_art = stats
    pct = 100 * with_art // total if total else 0
    print(f"  カード総数: {total}")
    print(f"  アート取得済み: {with_art} ({pct}%)")
    if with_art < total:
        missing = total - with_art
        print(f"  未取得: {missing} — 'kamir build-db' を再実行してダウンロードできます。")


def stage_print_test(cfg: dict, mana_value: int) -> None:
    db_path = cfg["paths"]["kamir_db"]
    device = cfg["printer"]["device"]

    if not db_path.exists():
        print("  カードプールが見つかりません。先に 'kamir build-db' を実行してください。")
        log.error("Card pool not found at %s.", db_path)
        return

    card = select_creature(db_path, mana_value)
    if card is None:
        print(f"  マナ総量 {mana_value} のクリーチャーはプールに存在しません。")
        return

    print(format_card(card))
    print()
    try:
        print_card(card, device, load_art(db_path, card))
        log.info("print-test: %s (MV %d) → %s", card.name, card.mana_value, device)
    except OSError as e:
        print(f"  印刷エラー: {e}")
        log.error("print-test failed: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kamir",
        description="Kamir — Momir Basic play tool for Raspberry Pi",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)
    bdb = sub.add_parser("build-db", help="Build kamir_cardpool.sqlite from AllPrintings.sqlite")
    bdb.add_argument("--force", action="store_true", help="Drop and recreate the DB (re-downloads all art)")
    sub.add_parser("play", help="Start an interactive Momir Basic play session")
    sub.add_parser("art-status", help="Show how many cards have art downloaded")
    pt = sub.add_parser("print-test", help="Print a random card at a given mana value (hardware test)")
    pt.add_argument("--mv", type=int, required=True, metavar="N", help="Mana value")

    args = parser.parse_args()

    raw_cfg = cfg_mod.load(args.config)
    root = (args.config.parent if args.config else Path(".")).resolve()
    cfg = _resolve(raw_cfg, root)

    log_mod.setup(cfg["paths"]["log_file"], level=logging.DEBUG if args.debug else logging.INFO)

    if args.command == "build-db":
        stage_build_db(cfg, force=args.force)
    elif args.command == "play":
        stage_play(cfg)
    elif args.command == "art-status":
        stage_art_status(cfg)
    elif args.command == "print-test":
        stage_print_test(cfg, args.mv)
