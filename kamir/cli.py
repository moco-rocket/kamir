import argparse
import logging
from pathlib import Path

import kamir.config as cfg_mod
from kamir.config import Config, Pool, RuntimeConfig
from kamir.db.art import art_stats, fetch_and_store_art, load_art
from kamir.db.load import open_source, iter_raw_cards, all_set_codes
from kamir.db.write import create_kamir_db, insert_cards
from kamir.filter.cards import filter_cards
from kamir.play.display import format_token
from kamir.play.select import select_creature, find_by_name
from kamir.printer.send import print_token
from kamir.utils import log as log_mod

log = logging.getLogger(__name__)

_NO_CARD_POOL = "  カードプールが見つかりません。先に 'kamir pool build' を実行してください。"


def stage_build_pool(pool: Pool, force: bool = False) -> None:
    log.info("Opening source database: %s", pool.mtgjson_db)
    src_conn = open_source(pool.mtgjson_db)

    if pool.sets == "*" or pool.sets == ["*"]:
        allowed = all_set_codes(src_conn)
        log.info("sets = \"*\": resolved to %d set codes", len(allowed))
    else:
        allowed = set(pool.sets)

    raw_cards = iter_raw_cards(src_conn)
    src_conn.close()

    log.info("Filtering %d raw cards", len(raw_cards))
    filtered = filter_cards(raw_cards, allowed)
    log.info("%d cards passed filter", len(filtered))

    if force:
        log.info("--force: dropping existing DB")
    dest_conn = create_kamir_db(pool.path, force=force)
    insert_cards(dest_conn, filtered)
    dest_conn.close()
    log.info("Database written: %s", pool.path)

    fetch_and_store_art(pool.path, filtered)


def stage_pool_list(config: Config) -> None:
    if not config.pools:
        print("  プールが設定されていません。config.toml に [[pool]] を追加してください。")
        return
    default = config.runtime.default_pool
    for pool in config.pools:
        marker = "*" if pool.name == default else " "
        status = "構築済み" if pool.path.exists() else "未構築  "
        sets_label = "*" if pool.sets in ("*", ["*"]) else f"{len(pool.sets)} セット"
        print(f"  {marker} {pool.name:<20} {status}  ({sets_label})  {pool.path}")


def stage_art_status(pool: Pool) -> None:
    stats = art_stats(pool.path)
    if stats is None:
        print(_NO_CARD_POOL)
        return
    total, with_art = stats
    pct = 100 * with_art // total if total else 0
    print(f"  プール: {pool.name}")
    print(f"  カード総数: {total}")
    print(f"  アート取得済み: {with_art} ({pct}%)")
    if with_art < total:
        missing = total - with_art
        print(f"  未取得: {missing} — 'kamir pool build {pool.name}' を再実行してダウンロードできます。")


def stage_play(runtime: RuntimeConfig, pool: Pool) -> None:
    if not pool.path.exists():
        print(_NO_CARD_POOL)
        log.error("Card pool not found at %s. Run 'kamir pool build' first.", pool.path)
        return

    print(f"Kamir — Momir Basic  [{pool.name}]  (終了: q または Ctrl-C)")
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

        card = select_creature(pool.path, mv)
        if card is None:
            print(f"  マナ総量 {mv} のクリーチャーはプールに存在しません。")
            continue

        if not runtime.auto_print:
            try:
                confirm = input("  印刷しますか？ [Enter で印刷 / q でスキップ] ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if confirm in ("q", "n"):
                continue

        try:
            print_token(card, runtime.printer_device, load_art(pool.path, card))
            log.info("Printed: %s (MV %d)", card.name, card.mana_value)
        except OSError as e:
            print(f"  印刷エラー: {e}")
            log.error("Print failed for '%s': %s", card.name, e)


def stage_gpio_play(runtime: RuntimeConfig, pool: Pool) -> None:
    from kamir.play.gpio_runner import run as _gpio_run
    from kamir.play.gpio_session import GpioPlaySession

    gpio_cfg    = runtime.gpio
    play_cfg    = gpio_cfg.get("play", {})
    buttons_cfg = gpio_cfg.get("buttons", {})
    display_cfg = gpio_cfg.get("display")
    led_cfg     = gpio_cfg.get("error_led")

    if not pool.path.exists():
        print(_NO_CARD_POOL)
        log.error("Card pool not found: %s", pool.path)
        return

    if not buttons_cfg:
        print("  [runtime.gpio.buttons] の設定がありません。config.toml を確認してください。")
        log.error("No [runtime.gpio.buttons] config found.")
        return

    display = None
    if display_cfg:
        try:
            from kamir.hardware.tm1637_display import Tm1637Display
            brightness     = display_cfg.get("brightness", 7)
            digits         = display_cfg.get("digits", 4)
            visible_digits = display_cfg.get("visible_digits", 2)
            right_align    = display_cfg.get("right_align", True)
            display = Tm1637Display(
                clk=display_cfg["clk"],
                dio=display_cfg["dio"],
                brightness=brightness,
                digits=digits,
                visible_digits=visible_digits,
                right_align=right_align,
            )
            log.info(
                "TM1637 display on CLK=%s DIO=%s (brightness=%s digits=%s visible=%s)",
                display_cfg["clk"], display_cfg["dio"],
                brightness, digits, visible_digits,
            )
        except ImportError as e:
            log.warning("TM1637 display unavailable: %s — running without display", e)

    error_led = None
    if led_cfg:
        try:
            from kamir.hardware.gpio_led import GpioErrorLed
            error_led = GpioErrorLed(pin=led_cfg["pin"])
            log.info("Error LED on pin %s", led_cfg["pin"])
        except ImportError as e:
            log.warning("GPIO LED unavailable: %s — running without error LED", e)

    session = GpioPlaySession(
        pool.path, runtime.printer_device,
        initial_mv=play_cfg.get("initial_mana_value", 0),
        min_mv=play_cfg.get("min_mana_value", 0),
        max_mv=play_cfg.get("max_mana_value", 16),
        display=display,
        error_led=error_led,
        os_shutdown=play_cfg.get("os_shutdown", False),
    )

    bounce_time = play_cfg.get("bounce_time", 0.05)
    hold_time   = play_cfg.get("hold_time", 1.0)
    log.info(
        "Starting GPIO play session [%s]. Long-press POWER to stop "
        "(bounce=%.2fs hold=%.1fs).",
        pool.name, bounce_time, hold_time,
    )
    try:
        _gpio_run(session, buttons_cfg, bounce_time=bounce_time, hold_time=hold_time)
    except ImportError as e:
        print(f"  GPIO ライブラリが見つかりません: {e}")
        log.error("GPIO runner failed: %s", e)


def stage_print_test(
    runtime: RuntimeConfig,
    pool: Pool,
    mana_value: int | None = None,
    name: str | None = None,
) -> None:
    if not pool.path.exists():
        print(_NO_CARD_POOL)
        log.error("Card pool not found at %s.", pool.path)
        return

    if name is not None:
        card = find_by_name(pool.path, name)
        if card is None:
            print(f"  「{name}」はカードプールに存在しません。")
            return
    else:
        card = select_creature(pool.path, mana_value)
        if card is None:
            print(f"  マナ総量 {mana_value} のクリーチャーはプールに存在しません。")
            return

    print(format_token(card))
    print()
    try:
        print_token(card, runtime.printer_device, load_art(pool.path, card))
        log.info("print-test: %s (MV %d) → %s", card.name, card.mana_value, runtime.printer_device)
    except OSError as e:
        print(f"  印刷エラー: {e}")
        log.error("print-test failed: %s", e)


def _resolve_pool(config: Config, pool_name: str | None) -> Pool | None:
    name = pool_name or config.runtime.default_pool
    pool = config.get_pool(name)
    if pool is None:
        print(f"  プール '{name}' が見つかりません。'kamir pool list' で確認してください。")
    return pool


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kamir",
        description="Kamir — Momir Basic play tool for Raspberry Pi",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml (default: $KAMIR_CONFIG or ./config.toml)")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    pool_parser = sub.add_parser("pool", help="Card pool management")
    pool_sub = pool_parser.add_subparsers(dest="pool_command", required=True)
    pool_sub.add_parser("list", help="List configured pools")
    pb = pool_sub.add_parser("build", help="Build a card pool DB from AllPrintings.sqlite")
    pb.add_argument("name", nargs="?", default=None, help="Pool name (default: all pools)")
    pb.add_argument("--force", action="store_true", help="Drop and recreate the DB (re-downloads all art)")
    ps = pool_sub.add_parser("status", help="Show art download progress for a pool")
    ps.add_argument("name", nargs="?", default=None, help="Pool name (default: default pool)")

    play_p = sub.add_parser("play", help="Start an interactive Momir Basic play session")
    play_p.add_argument("--pool", metavar="NAME", default=None, help="Pool to use (default: runtime.default_pool)")

    gpio_p = sub.add_parser("gpio-play", help="GPIO button-driven play session (Raspberry Pi)")
    gpio_p.add_argument("--pool", metavar="NAME", default=None)

    pt = sub.add_parser("print-test", help="Print a card for hardware testing")
    pt.add_argument("--pool", metavar="NAME", default=None)
    pt_group = pt.add_mutually_exclusive_group(required=True)
    pt_group.add_argument("--mv", type=int, metavar="N", help="Random card at mana value N")
    pt_group.add_argument("--name", metavar="NAME", help="Specific card by name")

    args = parser.parse_args()

    config = cfg_mod.load(args.config)
    log_mod.setup(config.runtime.log_file, level=logging.DEBUG if args.debug else logging.INFO)

    if args.command == "pool":
        if args.pool_command == "list":
            stage_pool_list(config)
        elif args.pool_command == "build":
            if args.name is not None:
                pool = _resolve_pool(config, args.name)
                if pool is not None:
                    stage_build_pool(pool, force=args.force)
            else:
                for pool in config.pools:
                    stage_build_pool(pool, force=args.force)
        elif args.pool_command == "status":
            pool = _resolve_pool(config, args.name)
            if pool is not None:
                stage_art_status(pool)

    elif args.command == "play":
        pool = _resolve_pool(config, args.pool)
        if pool is not None:
            stage_play(config.runtime, pool)

    elif args.command == "gpio-play":
        pool = _resolve_pool(config, args.pool)
        if pool is not None:
            stage_gpio_play(config.runtime, pool)

    elif args.command == "print-test":
        pool = _resolve_pool(config, args.pool)
        if pool is not None:
            stage_print_test(config.runtime, pool, mana_value=args.mv, name=args.name)
