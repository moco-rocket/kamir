from pathlib import Path
from unittest.mock import patch

import pytest

from kamir.cli import stage_build_pool, stage_play
from kamir.config import Pool, RuntimeConfig
from kamir.db.write import create_kamir_db, insert_cards
from kamir.domain import Card


def _card(**overrides) -> Card:
    base = dict(
        name="Grizzly Bears",
        mana_value=2,
        mana_cost="{1}{G}",
        type_line="Creature - Bear",
        oracle_text="",
        power="2",
        toughness="2",
        expansion="2ED",
        layout="normal",
        collector_number="178",
    )
    return Card(**{**base, **overrides})


@pytest.fixture
def pool_db(tmp_path) -> Path:
    db_path = tmp_path / "kamir_cardpool.sqlite"
    conn = create_kamir_db(db_path)
    insert_cards(conn, [_card()])
    conn.close()
    return db_path


def _pool(db_path: Path, sets: list[str] | str = ["2ED"]) -> Pool:
    return Pool(
        name="test",
        path=db_path,
        mtgjson_db=Path("/dev/null"),
        sets=sets,
    )


def _runtime(auto_print: bool = True) -> RuntimeConfig:
    return RuntimeConfig(
        log_file=Path("/dev/null"),
        auto_print=auto_print,
        printer_device="/dev/null",
        default_pool="test",
    )


class TestBuildPool:
    def test_string_wildcard_uses_all_set_codes(self, tmp_path, mocker):
        mock_all = mocker.patch("kamir.cli.all_set_codes", return_value={"2ED"})
        mocker.patch("kamir.cli.open_source")
        mocker.patch("kamir.cli.iter_raw_cards", return_value=[])
        mocker.patch("kamir.cli.filter_cards", return_value=[])
        mocker.patch("kamir.cli.create_kamir_db")
        mocker.patch("kamir.cli.insert_cards")
        mocker.patch("kamir.cli.fetch_and_store_art")
        stage_build_pool(_pool(tmp_path / "out.sqlite", sets="*"))
        mock_all.assert_called_once()

    def test_list_wildcard_uses_all_set_codes(self, tmp_path, mocker):
        mock_all = mocker.patch("kamir.cli.all_set_codes", return_value={"2ED"})
        mocker.patch("kamir.cli.open_source")
        mocker.patch("kamir.cli.iter_raw_cards", return_value=[])
        mocker.patch("kamir.cli.filter_cards", return_value=[])
        mocker.patch("kamir.cli.create_kamir_db")
        mocker.patch("kamir.cli.insert_cards")
        mocker.patch("kamir.cli.fetch_and_store_art")
        stage_build_pool(_pool(tmp_path / "out.sqlite", sets=["*"]))
        mock_all.assert_called_once()

    def test_explicit_list_does_not_use_all_set_codes(self, tmp_path, mocker):
        mock_all = mocker.patch("kamir.cli.all_set_codes", return_value={"2ED"})
        mocker.patch("kamir.cli.open_source")
        mocker.patch("kamir.cli.iter_raw_cards", return_value=[])
        mocker.patch("kamir.cli.filter_cards", return_value=[])
        mocker.patch("kamir.cli.create_kamir_db")
        mocker.patch("kamir.cli.insert_cards")
        mocker.patch("kamir.cli.fetch_and_store_art")
        stage_build_pool(_pool(tmp_path / "out.sqlite", sets=["2ED", "LEA"]))
        mock_all.assert_not_called()


class TestAutoprint:
    def test_auto_print_true_prints_without_prompt(self, pool_db, mocker):
        mock_print = mocker.patch("kamir.cli.print_token")
        mocker.patch("kamir.cli.load_art", return_value=None)
        with patch("builtins.input", side_effect=["2", "q"]):
            stage_play(_runtime(auto_print=True), _pool(pool_db))
        mock_print.assert_called_once()

    def test_auto_print_false_prints_on_enter(self, pool_db, mocker):
        mock_print = mocker.patch("kamir.cli.print_token")
        mocker.patch("kamir.cli.load_art", return_value=None)
        with patch("builtins.input", side_effect=["2", "", "q"]):
            stage_play(_runtime(auto_print=False), _pool(pool_db))
        mock_print.assert_called_once()

    def test_auto_print_false_skips_on_q(self, pool_db, mocker):
        mock_print = mocker.patch("kamir.cli.print_token")
        mocker.patch("kamir.cli.load_art", return_value=None)
        with patch("builtins.input", side_effect=["2", "q", "q"]):
            stage_play(_runtime(auto_print=False), _pool(pool_db))
        mock_print.assert_not_called()

    def test_auto_print_false_skips_on_n(self, pool_db, mocker):
        mock_print = mocker.patch("kamir.cli.print_token")
        mocker.patch("kamir.cli.load_art", return_value=None)
        with patch("builtins.input", side_effect=["2", "n", "q"]):
            stage_play(_runtime(auto_print=False), _pool(pool_db))
        mock_print.assert_not_called()

    def test_default_is_auto_print(self, pool_db, mocker):
        mock_print = mocker.patch("kamir.cli.print_token")
        mocker.patch("kamir.cli.load_art", return_value=None)
        with patch("builtins.input", side_effect=["2", "q"]):
            stage_play(_runtime(), _pool(pool_db))
        mock_print.assert_called_once()
