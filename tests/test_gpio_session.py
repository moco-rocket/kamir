from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from kamir.domain import Card
from kamir.hardware.display import ManaDisplay
from kamir.hardware.leds import ErrorLed
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
        session._print_lock.acquire()
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

    def test_lock_released_after_success(self, session):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            session.summon()
            assert not session._print_lock.locked()

    def test_lock_released_after_error(self, session):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("no device")),
        ):
            session.summon()
            assert not session._print_lock.locked()


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
        session._print_lock.acquire()
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

    def test_lock_released_after_reprint_error(self, session):
        session.last_card = _card()
        with (
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("gone")),
        ):
            session.reprint_last()
            assert not session._print_lock.locked()


class TestShutdown:
    def test_shutdown_sets_event(self):
        import threading
        s = GpioPlaySession(Path("x.sqlite"), "/dev/null")
        assert not s._shutdown_event.is_set()
        s.shutdown()
        assert s._shutdown_event.is_set()

    def test_wait_for_shutdown_unblocks_after_shutdown(self):
        import threading
        s = GpioPlaySession(Path("x.sqlite"), "/dev/null")
        unblocked = threading.Event()
        t = threading.Thread(target=lambda: (s.wait_for_shutdown(), unblocked.set()), daemon=True)
        t.start()
        s.shutdown()
        t.join(timeout=1.0)
        assert unblocked.is_set()


@pytest.fixture
def display() -> MagicMock:
    return MagicMock(spec=ManaDisplay)


@pytest.fixture
def error_led() -> MagicMock:
    return MagicMock(spec=ErrorLed)


@pytest.fixture
def hw_session(display, error_led) -> GpioPlaySession:
    return GpioPlaySession(
        db_path=Path("fake.sqlite"),
        device="/dev/null",
        initial_mv=3,
        min_mv=0,
        max_mv=10,
        display=display,
        error_led=error_led,
    )


class TestDisplayIntegration:
    def test_init_calls_show_value(self, display):
        GpioPlaySession(Path("x.sqlite"), "/dev/null", initial_mv=5, display=display)
        display.show_value.assert_called_once_with(5)

    def test_no_display_does_not_raise_on_init(self):
        GpioPlaySession(Path("x.sqlite"), "/dev/null", initial_mv=5)

    def test_increase_calls_show_value(self, hw_session, display):
        hw_session.current_mv = 3
        display.reset_mock()
        hw_session.increase_mana_value()
        display.show_value.assert_called_once_with(4)

    def test_increase_at_max_does_not_call_show_value(self, hw_session, display):
        hw_session.current_mv = hw_session.max_mana_value
        display.reset_mock()
        hw_session.increase_mana_value()
        display.show_value.assert_not_called()

    def test_decrease_calls_show_value(self, hw_session, display):
        hw_session.current_mv = 3
        display.reset_mock()
        hw_session.decrease_mana_value()
        display.show_value.assert_called_once_with(2)

    def test_decrease_at_min_does_not_call_show_value(self, hw_session, display):
        hw_session.current_mv = hw_session.min_mana_value
        display.reset_mock()
        hw_session.decrease_mana_value()
        display.show_value.assert_not_called()

    def test_reset_calls_show_value(self, hw_session, display):
        hw_session.current_mv = 7
        display.reset_mock()
        hw_session.reset_mana_value()
        display.show_value.assert_called_once_with(hw_session.min_mana_value)

    def test_summon_success_show_busy_then_show_value(self, hw_session, display):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            display.reset_mock()
            hw_session.summon()
        assert display.method_calls == [
            call.show_busy(hw_session.current_mv),
            call.show_value(hw_session.current_mv),
        ]

    def test_summon_no_card_calls_show_error_and_blink(self, hw_session, display, error_led):
        with patch("kamir.play.gpio_session.select_creature", return_value=None):
            display.reset_mock()
            error_led.reset_mock()
            hw_session.summon()
        display.show_error.assert_called_once()
        error_led.blink.assert_called_once()

    def test_summon_no_card_does_not_call_show_value(self, hw_session, display):
        with patch("kamir.play.gpio_session.select_creature", return_value=None):
            display.reset_mock()
            hw_session.summon()
        display.show_value.assert_not_called()

    def test_summon_print_error_calls_show_error_and_blink(self, hw_session, display, error_led):
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("no device")),
        ):
            display.reset_mock()
            error_led.reset_mock()
            hw_session.summon()
        display.show_error.assert_called_once()
        error_led.blink.assert_called_once()

    def test_reprint_success_show_busy_then_show_value(self, hw_session, display):
        hw_session.last_card = _card()
        with (
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            display.reset_mock()
            hw_session.reprint_last()
        assert display.method_calls == [
            call.show_busy(hw_session.current_mv),
            call.show_value(hw_session.current_mv),
        ]

    def test_reprint_print_error_calls_show_error_and_blink(self, hw_session, display, error_led):
        hw_session.last_card = _card()
        with (
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card", side_effect=OSError("gone")),
        ):
            display.reset_mock()
            error_led.reset_mock()
            hw_session.reprint_last()
        display.show_error.assert_called_once()
        error_led.blink.assert_called_once()

    def test_reprint_no_last_card_no_display_call(self, hw_session, display):
        hw_session.last_card = None
        display.reset_mock()
        hw_session.reprint_last()
        display.show_busy.assert_not_called()

    def test_shutdown_calls_show_off(self, hw_session, display):
        hw_session.shutdown()
        display.show_off.assert_called_once()

    def test_no_display_no_raise_on_all_operations(self):
        s = GpioPlaySession(Path("x.sqlite"), "/dev/null")
        with (
            patch("kamir.play.gpio_session.select_creature", return_value=_card()),
            patch("kamir.play.gpio_session.load_art", return_value=None),
            patch("kamir.play.gpio_session.print_card"),
        ):
            s.increase_mana_value()
            s.decrease_mana_value()
            s.reset_mana_value()
            s.summon()
            s.reprint_last()
            s.shutdown()
