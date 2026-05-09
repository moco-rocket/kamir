try:
    from gpiozero import LED as _GpioLED
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class GpioErrorLed:
    """ErrorLed backed by a single GPIO output pin via gpiozero.

    Requires gpiozero (pre-installed on Raspberry Pi OS; or ``uv add gpiozero``).
    """

    def __init__(self, pin: int) -> None:
        if not _AVAILABLE:
            raise ImportError(
                "gpiozero package not installed. "
                "On Raspberry Pi OS: sudo apt install python3-gpiozero\n"
                "Otherwise: uv add gpiozero"
            )
        self._led = _GpioLED(pin)

    def on(self) -> None:
        self._led.on()

    def off(self) -> None:
        self._led.off()

    def blink(self) -> None:
        self._led.blink(on_time=0.2, off_time=0.2, n=3, background=True)
