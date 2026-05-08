from pathlib import Path
from unittest.mock import patch

import pytest

from kamir.domain import Card
from kamir.play.gpio_session import GpioPlaySession


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
        collector_number="178",
        layout="normal",
    )
    return Card(**{**base, **overrides})


@pytest.fixture
def session() -> GpioPlaySession:
    return GpioPlaySession(
        db_path=Path("fake.sqlite"),
        device="/dev/null",
        initial_mv=3,
        min_mv=0,
        max_mv=10,
    )


class TestManaValue:
    def test_initial_value(self):
        s = GpioPlaySession(Path("x.sqlite"), "/dev/null", initial_mv=5)
        assert s.current_mv == 5

    def test_default_initial_value(self):
        s = GpioPlaySession(Path("x.sqlite"), "/dev/null")
        assert s.current_mv == 0

    def test_default_min_max(self):
        s = GpioPlaySession(Path("x.sqlite"), "/dev/null")
        assert s.min_mana_value == 0
        assert s.max_mana_value == 16

    def test_increase(self, session):
        session.current_mv = 3
        session.increase_mana_value()
        assert session.current_mv == 4

    def test_increase_capped_at_max(self, session):
        session.current_mv = session.max_mana_value
        session.increase_mana_value()
        assert session.current_mv == session.max_mana_value

    def test_decrease(self, session):
        session.current_mv = 3
        session.decrease_mana_value()
        assert session.current_mv == 2

    def test_decrease_floored_at_min(self, session):
        session.current_mv = session.min_mana_value
        session.decrease_mana_value()
        assert session.current_mv == session.min_mana_value

    def test_reset_returns_to_min(self, session):
        session.current_mv = 7
        session.reset_mana_value()
        assert session.current_mv == session.min_mana_value


class TestSummon:
    def test_print_card_called_when_card_found(self, session):
        card = _card()
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=card) as mock_sel,
            patch("kamir.play.gpio_session.load_art", return_value=None) as mock_art,
            patch("kamir.play.gpio_session.print_card") as mock_print,
        ):
            session.summon()
            mock_sel.assert_called_once_with(session.db_path, session.current_mv)
            mock_art.assert_called_once_with(session.db_path, card)
            mock_print.assert_called_once_with(card, session.device, None)

    def test_last_card_saved_after_summon(self, session):
        card = _card()
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=card),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            session.summon()
            assert session.last_card is card

    def test_print_card_not_called_when_no_card(self, session):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=None),
            patch("kamir.play.gpio_session.print_card") as mock_print,
        ):
            session.summon()
            mock_print.assert_not_called()

    def test_last_card_unchanged_when_no_card(self, session):
        session.last_card = None
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            session.summon()
            assert session.last_card is None

    def test_ignored_while_printing(self, session):
        session._printing = True
        with patch("kamir.play.gpio_session.select_creature") as mock_sel:
            session.summon()
            mock_sel.assert_not_called()

    def test_print_error_does_not_propagate(self, session):
        card = _card()
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=card),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("no device")),
        ):
            session.summon()  # should not raise

    def test_printing_flag_cleared_after_success(self, session):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            session.summon()
            assert not session._printing

    def test_printing_flag_cleared_after_error(self, session):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("no device")),
        ):
            session.summon()
            assert not session._printing


class TestReprintLast:
    def test_reprints_last_card(self, session):
        card = _card()
        session.last_card = card
        with (
            patch("kamir.play.gpio_session.load_art", return_value=None) as mock_art,
            patch("kamir.play.gpio_session.print_card") as mock_print,
        ):
            session.reprint_last()
            mock_art.assert_called_once_with(session.db_path, card)
            mock_print.assert_called_once_with(card, session.device, None)

    def test_no_op_when_last_card_is_none(self, session):
        session.last_card = None
        with patch("kamir.play.gpio_session.print_card") as mock_print:
            session.reprint_last()
            mock_print.assert_not_called()

    def test_ignored_while_printing(self, session):
        session._printing = True
        session.last_card = _card()
        with patch("kamir.play.gpio_session.print_card") as mock_print:
            session.reprint_last()
            mock_print.assert_not_called()

    def test_reprint_error_does_not_propagate(self, session):
        session.last_card = _card()
        with (
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("gone")),
        ):
            session.reprint_last()  # should not raise

    def test_printing_flag_cleared_after_reprint_error(self, session):
        session.last_card = _card()
        with (
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("gone")),
        ):
            session.reprint_last()
            assert not session._printing
