# 7-segment encodings (common-cathode, bit order: dp-g-f-e-d-c-b-a)
_DIGIT_SEGS = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f]
_SEG_DASH   = 0x40  # "-"
_SEG_E      = 0x79  # "E"
_SEG_r      = 0x50  # "r"

try:
    import tm1637 as _tm1637_lib
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _format_segments(
    value: int,
    digits: int = 4,
    visible_digits: int = 2,
    right_align: bool = True,
) -> list[int]:
    """Return a ``digits``-length list of segment bytes encoding ``value``.

    The value is zero-padded to ``visible_digits`` and placed at the right
    (or left) end of the full digit array.  Values that exceed the range
    representable in ``visible_digits`` digits are clamped.

    Examples with digits=4, visible_digits=2, right_align=True:
      0  → [0x00, 0x00, 0x3f, 0x3f]  "  00"
      4  → [0x00, 0x00, 0x3f, 0x66]  "  04"
      10 → [0x00, 0x00, 0x06, 0x3f]  "  10"
      16 → [0x00, 0x00, 0x06, 0x7d]  "  16"
    """
    max_val = 10 ** visible_digits - 1
    clamped = max(0, min(value, max_val))
    digit_chars = str(clamped).zfill(visible_digits)
    segs = [0x00] * digits
    offset = (digits - visible_digits) if right_align else 0
    for i, ch in enumerate(digit_chars):
        segs[offset + i] = _DIGIT_SEGS[int(ch)]
    return segs


class Tm1637Display:
    """ManaDisplay backed by a TM1637 4-digit 7-segment LED module.

    Requires the ``raspberrypi-tm1637`` PyPI package (``import tm1637``).
    Segment layout assumes a standard 4-digit common-cathode TM1637 module.
    """

    def __init__(
        self,
        clk: int,
        dio: int,
        brightness: int = 7,
        digits: int = 4,
        visible_digits: int = 2,
        right_align: bool = True,
    ) -> None:
        if not _AVAILABLE:
            raise ImportError(
                "raspberrypi-tm1637 package not installed. "
                "Run: uv add raspberrypi-tm1637 gpiozero"
            )
        self._tm = _tm1637_lib.TM1637(clk=clk, dio=dio, brightness=brightness)
        self._digits = digits
        self._visible_digits = visible_digits
        self._right_align = right_align

    def show_value(self, value: int) -> None:
        self._tm.write(_format_segments(value, self._digits, self._visible_digits, self._right_align))

    def show_busy(self, value: int) -> None:
        # Four dashes while a print job is running.
        self._tm.write([_SEG_DASH] * self._digits)

    def show_error(self) -> None:
        # "Err " — segments for E, r, r, blank.
        segs = [_SEG_E, _SEG_r, _SEG_r, 0x00]
        self._tm.write(segs[: self._digits])

    def show_off(self) -> None:
        self._tm.write([0x00] * self._digits)
