from unittest.mock import MagicMock

from kamir.hardware.display import ManaDisplay
from kamir.hardware.leds import ErrorLed
from kamir.hardware.tm1637_display import _DIGIT_SEGS, _format_segments


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


class TestFormatSegments:
    """Tests for _format_segments — no hardware required."""

    def test_zero_is_zero_padded(self):
        segs = _format_segments(0, digits=4, visible_digits=2, right_align=True)
        assert segs == [0x00, 0x00, _DIGIT_SEGS[0], _DIGIT_SEGS[0]]

    def test_single_digit_is_zero_padded(self):
        segs = _format_segments(4, digits=4, visible_digits=2, right_align=True)
        assert segs == [0x00, 0x00, _DIGIT_SEGS[0], _DIGIT_SEGS[4]]

    def test_two_digit_value(self):
        segs = _format_segments(10, digits=4, visible_digits=2, right_align=True)
        assert segs == [0x00, 0x00, _DIGIT_SEGS[1], _DIGIT_SEGS[0]]

    def test_max_two_digit_value(self):
        segs = _format_segments(16, digits=4, visible_digits=2, right_align=True)
        assert segs == [0x00, 0x00, _DIGIT_SEGS[1], _DIGIT_SEGS[6]]

    def test_left_align(self):
        segs = _format_segments(4, digits=4, visible_digits=2, right_align=False)
        assert segs == [_DIGIT_SEGS[0], _DIGIT_SEGS[4], 0x00, 0x00]

    def test_value_clamped_to_max(self):
        # 99 is the max for visible_digits=2; 100 should be clamped to 99
        segs = _format_segments(100, digits=4, visible_digits=2, right_align=True)
        expected = _format_segments(99, digits=4, visible_digits=2, right_align=True)
        assert segs == expected

    def test_value_clamped_to_zero(self):
        segs = _format_segments(-1, digits=4, visible_digits=2, right_align=True)
        assert segs == _format_segments(0, digits=4, visible_digits=2, right_align=True)

    def test_output_length_equals_digits(self):
        for d in (2, 4, 6):
            assert len(_format_segments(5, digits=d, visible_digits=2)) == d

    def test_all_digits_9(self):
        segs = _format_segments(99, digits=4, visible_digits=2, right_align=True)
        assert segs == [0x00, 0x00, _DIGIT_SEGS[9], _DIGIT_SEGS[9]]


class TestErrorLedProtocol:
    def test_concrete_class_satisfies_protocol(self):
        assert isinstance(_ConcreteLed(), ErrorLed)

    def test_missing_method_does_not_satisfy_protocol(self):
        assert not isinstance(_ConcreteLedMissingMethod(), ErrorLed)

    def test_mock_satisfies_protocol(self):
        mock = MagicMock(spec=ErrorLed)
        assert isinstance(mock, ErrorLed)
