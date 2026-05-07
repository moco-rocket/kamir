from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from kamir.cli import stage_play
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


def _cfg(db_path: Path, auto_print: bool) -> dict:
    return {
        "paths": {"kamir_db": db_path},
        "printer": {"device": "/dev/null"},
        "play": {"auto_print": auto_print},
    }


class TestAutoprint:
    def test_auto_print_true_prints_without_prompt(self, pool_db, mocker):
        mock_print_card = mocker.patch("kamir.cli.print_card")
        mocker.patch("kamir.cli.load_art", return_value=None)
        # First input: mana value, second: quit
        with patch("builtins.input", side_effect=["2", "q"]):
            stage_play(_cfg(pool_db, auto_print=True))
        mock_print_card.assert_called_once()

    def test_auto_print_false_prints_on_enter(self, pool_db, mocker):
        mock_print_card = mocker.patch("kamir.cli.print_card")
        mocker.patch("kamir.cli.load_art", return_value=None)
        # mana value → confirm (Enter) → quit
        with patch("builtins.input", side_effect=["2", "", "q"]):
            stage_play(_cfg(pool_db, auto_print=False))
        mock_print_card.assert_called_once()

    def test_auto_print_false_skips_on_q(self, pool_db, mocker):
        mock_print_card = mocker.patch("kamir.cli.print_card")
        mocker.patch("kamir.cli.load_art", return_value=None)
        # mana value → skip with q → quit
        with patch("builtins.input", side_effect=["2", "q", "q"]):
            stage_play(_cfg(pool_db, auto_print=False))
        mock_print_card.assert_not_called()

    def test_auto_print_false_skips_on_n(self, pool_db, mocker):
        mock_print_card = mocker.patch("kamir.cli.print_card")
        mocker.patch("kamir.cli.load_art", return_value=None)
        with patch("builtins.input", side_effect=["2", "n", "q"]):
            stage_play(_cfg(pool_db, auto_print=False))
        mock_print_card.assert_not_called()

    def test_default_is_auto_print(self, pool_db, mocker):
        mock_print_card = mocker.patch("kamir.cli.print_card")
        mocker.patch("kamir.cli.load_art", return_value=None)
        # cfg without [play] section — should default to auto_print=True
        cfg = {"paths": {"kamir_db": pool_db}, "printer": {"device": "/dev/null"}}
        with patch("builtins.input", side_effect=["2", "q"]):
            stage_play(cfg)
        mock_print_card.assert_called_once()
