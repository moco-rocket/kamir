import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kamir.play.gpio_session import GpioPlaySession

log = logging.getLogger(__name__)


def run(session: "GpioPlaySession", pins: dict) -> None:
    """Block until the POWER button is pressed, dispatching button events to session.

    Requires gpiozero (pre-installed on Raspberry Pi OS).
    Button callbacks run on gpiozero background threads; GpioPlaySession's
    threading.Lock ensures only one print job runs at a time.
    """
    try:
        from gpiozero import Button
    except ImportError as e:
        raise ImportError(
            "gpiozero is required for GPIO play mode. "
            "On Raspberry Pi OS: sudo apt install python3-gpiozero"
        ) from e

    mv_up   = Button(pins["mv_up"],   pull_up=True, bounce_time=0.05)
    mv_down = Button(pins["mv_down"], pull_up=True, bounce_time=0.05)
    summon  = Button(pins["summon"],  pull_up=True, bounce_time=0.05)
    power   = Button(pins["power"],   pull_up=True, bounce_time=0.05)

    mv_up.when_pressed   = session.increase_mana_value
    mv_down.when_pressed = session.decrease_mana_value
    summon.when_pressed  = session.summon
    power.when_pressed   = session.shutdown

    log.info(
        "GPIO runner started — mv_up=%s mv_down=%s summon=%s power=%s",
        pins["mv_up"], pins["mv_down"], pins["summon"], pins["power"],
    )
    session.wait_for_shutdown()
    log.info("GPIO runner stopped.")
