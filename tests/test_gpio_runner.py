from unittest.mock import MagicMock

import pytest

from kamir.play.gpio_runner import _ButtonHandler, _create_handlers


class TestButtonHandler:
    def test_short_press_fires_on_short(self):
        calls = []
        h = _ButtonHandler(on_short=lambda: calls.append("short"))
        h.on_press()
        h.on_release()
        assert calls == ["short"]

    def test_long_press_fires_on_long_not_short(self):
        calls = []
        h = _ButtonHandler(
            on_short=lambda: calls.append("short"),
            on_long=lambda: calls.append("long"),
        )
        h.on_press()
        h.on_held()
        h.on_release()
        assert calls == ["long"]

    def test_long_press_does_not_fire_short(self):
        short_calls = []
        h = _ButtonHandler(
            on_short=lambda: short_calls.append(1),
            on_long=lambda: None,
        )
        h.on_press()
        h.on_held()
        h.on_release()
        assert short_calls == []

    def test_short_press_only_no_long_defined(self):
        calls = []
        h = _ButtonHandler(on_short=lambda: calls.append("short"))
        h.on_press()
        h.on_release()
        assert calls == ["short"]

    def test_long_press_only_no_short_defined(self):
        calls = []
        h = _ButtonHandler(on_long=lambda: calls.append("long"))
        h.on_press()
        h.on_held()
        h.on_release()
        assert calls == ["long"]

    def test_power_short_press_does_nothing(self):
        calls = []
        h = _ButtonHandler(on_long=lambda: calls.append("long"))
        h.on_press()
        h.on_release()
        assert calls == []

    def test_held_flag_resets_on_next_press(self):
        short_calls = []
        long_calls = []
        h = _ButtonHandler(
            on_short=lambda: short_calls.append(1),
            on_long=lambda: long_calls.append(1),
        )
        # First interaction: long press
        h.on_press()
        h.on_held()
        h.on_release()
        # Second interaction: short press — must fire short, not long
        h.on_press()
        h.on_release()
        assert short_calls == [1]
        assert long_calls == [1]

    def test_no_callbacks_defined_does_not_raise(self):
        h = _ButtonHandler()
        h.on_press()
        h.on_held()
        h.on_release()


class TestCreateHandlers:
    @pytest.fixture
    def session(self):
        return MagicMock()

    def test_mv_up_short_calls_increase(self, session):
        h = _create_handlers(session)["mv_up"]
        h.on_press()
        h.on_release()
        session.increase_mana_value.assert_called_once()
        session.decrease_mana_value.assert_not_called()

    def test_mv_up_long_does_nothing(self, session):
        h = _create_handlers(session)["mv_up"]
        h.on_press()
        h.on_held()
        h.on_release()
        session.increase_mana_value.assert_not_called()

    def test_mv_down_short_calls_decrease(self, session):
        h = _create_handlers(session)["mv_down"]
        h.on_press()
        h.on_release()
        session.decrease_mana_value.assert_called_once()
        session.reset_mana_value.assert_not_called()

    def test_mv_down_long_calls_reset_not_decrease(self, session):
        h = _create_handlers(session)["mv_down"]
        h.on_press()
        h.on_held()
        h.on_release()
        session.reset_mana_value.assert_called_once()
        session.decrease_mana_value.assert_not_called()

    def test_summon_short_calls_summon(self, session):
        h = _create_handlers(session)["summon"]
        h.on_press()
        h.on_release()
        session.summon.assert_called_once()
        session.reprint_last.assert_not_called()

    def test_summon_long_calls_reprint_not_summon(self, session):
        h = _create_handlers(session)["summon"]
        h.on_press()
        h.on_held()
        h.on_release()
        session.reprint_last.assert_called_once()
        session.summon.assert_not_called()

    def test_power_short_does_nothing(self, session):
        h = _create_handlers(session)["power"]
        h.on_press()
        h.on_release()
        session.shutdown.assert_not_called()

    def test_power_long_calls_shutdown(self, session):
        h = _create_handlers(session)["power"]
        h.on_press()
        h.on_held()
        h.on_release()
        session.shutdown.assert_called_once()
