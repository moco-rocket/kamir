import logging

log = logging.getLogger(__name__)

# 7-segment encodings (common-cathode, bit order: dp-g-f-e-d-c-b-a)
_SEG_DASH = 0x40   # "-"
_SEG_E    = 0x79   # "E"
_SEG_r    = 0x50   # "r"

try:
    import tm1637 as _tm1637_lib
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class Tm1637Display:
    """ManaDisplay backed by a TM1637 4-digit 7-segment LED module.

    Requires the ``tm1637`` package (``uv add tm1637``).
    Segment layout assumes a standard 4-digit common-cathode TM1637 module.
    """

    def __init__(self, clk: int, dio: int, brightness: int = 7) -> None:
        if not _AVAILABLE:
            raise ImportError(
                "tm1637 package not installed. "
                "Run: uv add tm1637"
            )
        self._tm = _tm1637_lib.TM1637(clk=clk, dio=dio, brightness=brightness)

    def show_value(self, value: int) -> None:
        self._tm.number(value)

    def show_busy(self, value: int) -> None:
        # Four dashes while a print job is running.
        self._tm.write([_SEG_DASH] * 4)

    def show_error(self) -> None:
        # "Err " — segments for E, r, r, blank.
        self._tm.write([_SEG_E, _SEG_r, _SEG_r, 0x00])

    def show_off(self) -> None:
        self._tm.write([0x00, 0x00, 0x00, 0x00])
