import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kamir.play.gpio_session import GpioPlaySession

log = logging.getLogger(__name__)


class _ButtonHandler:
    """Disambiguates short press from long press for a gpiozero Button.

    gpiozero fires when_pressed immediately on contact and when_held after
    hold_time. Without disambiguation a long press triggers both the
    short-press action and the long-press action. This class fixes that by
    deferring the short-press action to when_released and suppressing it when
    a hold was detected.

    Wire up as:
        btn.when_pressed  = handler.on_press
        btn.when_held     = handler.on_held
        btn.when_released = handler.on_release
    """

    def __init__(
        self,
        on_short: Callable[[], None] | None = None,
        on_long: Callable[[], None] | None = None,
    ) -> None:
        self._on_short = on_short
        self._on_long = on_long
        self._held = False

    def on_press(self) -> None:
        self._held = False

    def on_held(self) -> None:
        self._held = True
        if self._on_long is not None:
            self._on_long()

    def on_release(self) -> None:
        if not self._held and self._on_short is not None:
            self._on_short()


def _create_handlers(session: "GpioPlaySession") -> dict[str, _ButtonHandler]:
    return {
        "mv_up":   _ButtonHandler(on_short=session.increase_mana_value),
        "mv_down": _ButtonHandler(on_short=session.decrease_mana_value,
                                  on_long=session.reset_mana_value),
        "summon":  _ButtonHandler(on_short=session.summon,
                                  on_long=session.reprint_last),
        "power":   _ButtonHandler(on_long=session.shutdown),
    }


def run(
    session: "GpioPlaySession",
    pins: dict,
    bounce_time: float = 0.05,
    hold_time: float = 1.0,
) -> None:
    """Block until the POWER button is long-pressed, dispatching events to session.

    Button actions:
      mv_up   short → increase_mana_value()
      mv_down short → decrease_mana_value()
      mv_down long  → reset_mana_value()
      summon  short → summon()
      summon  long  → reprint_last()
      power   long  → shutdown()   # stops this process only — does NOT power off the Pi

    Requires gpiozero (pre-installed on Raspberry Pi OS).
    Callbacks run on gpiozero background threads; GpioPlaySession's
    threading.Lock ensures only one print job runs at a time.
    """
    try:
        from gpiozero import Button
    except ImportError as e:
        raise ImportError(
            "gpiozero is required for GPIO play mode. "
            "On Raspberry Pi OS: sudo apt install python3-gpiozero"
        ) from e

    handlers = _create_handlers(session)
    buttons = {
        name: Button(pins[name], pull_up=True,
                     bounce_time=bounce_time, hold_time=hold_time)
        for name in handlers
    }
    for name, h in handlers.items():
        btn = buttons[name]
        btn.when_pressed  = h.on_press
        btn.when_held     = h.on_held
        btn.when_released = h.on_release

    log.info(
        "GPIO runner started — mv_up=%s mv_down=%s summon=%s power=%s "
        "(bounce=%.2fs hold=%.1fs)",
        pins["mv_up"], pins["mv_down"], pins["summon"], pins["power"],
        bounce_time, hold_time,
    )
    session.wait_for_shutdown()
    log.info(
        "GPIO runner stopped. "
        "To power off the Raspberry Pi run: sudo shutdown -h now"
    )
