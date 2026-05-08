from unittest.mock import MagicMock

from kamir.hardware.display import ManaDisplay
from kamir.hardware.leds import ErrorLed


class _ConcreteDisplay:
    def show_value(self, value: int) -> None: ...
    def show_busy(self, value: int) -> None: ...
    def show_error(self) -> None: ...
    def show_off(self) -> None: ...


class _ConcreteDisplayMissingMethod:
    def show_value(self, value: int) -> None: ...
    def show_busy(self, value: int) -> None: ...
    def show_error(self) -> None: ...
    # show_off missing


class _ConcreteLed:
    def on(self) -> None: ...
    def off(self) -> None: ...
    def blink(self) -> None: ...


class _ConcreteLedMissingMethod:
    def on(self) -> None: ...
    def off(self) -> None: ...
    # blink missing


class TestManaDisplayProtocol:
    def test_concrete_class_satisfies_protocol(self):
        assert isinstance(_ConcreteDisplay(), ManaDisplay)

    def test_missing_method_does_not_satisfy_protocol(self):
        assert not isinstance(_ConcreteDisplayMissingMethod(), ManaDisplay)

    def test_mock_satisfies_protocol(self):
        mock = MagicMock(spec=ManaDisplay)
        assert isinstance(mock, ManaDisplay)


class TestErrorLedProtocol:
    def test_concrete_class_satisfies_protocol(self):
        assert isinstance(_ConcreteLed(), ErrorLed)

    def test_missing_method_does_not_satisfy_protocol(self):
        assert not isinstance(_ConcreteLedMissingMethod(), ErrorLed)

    def test_mock_satisfies_protocol(self):
        mock = MagicMock(spec=ErrorLed)
        assert isinstance(mock, ErrorLed)
