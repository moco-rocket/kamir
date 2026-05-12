import logging
import subprocess
import threading
from pathlib import Path

from kamir.db.art import load_art
from kamir.domain import Card, card_to_token_spec
from kamir.hardware.display import ManaDisplay
from kamir.hardware.leds import ErrorLed
from kamir.play.select import select_creature
from kamir.printer.send import print_token

log = logging.getLogger(__name__)


class GpioPlaySession:
    def __init__(
        self,
        db_path: Path,
        device: str,
        initial_mv: int = 0,
        min_mv: int = 0,
        max_mv: int = 16,
        display: ManaDisplay | None = None,
        error_led: ErrorLed | None = None,
        os_shutdown: bool = False,
    ) -> None:
        self.db_path = db_path
        self.device = device
        self.min_mana_value = min_mv
        self.max_mana_value = max_mv
        self.current_mv = initial_mv
        self.last_card: Card | None = None
        self._print_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._display = display
        self._error_led = error_led
        self._os_shutdown = os_shutdown
        self._signal_value()

    def _signal_value(self) -> None:
        if self._display is not None:
            self._display.show_value(self.current_mv)

    def _signal_busy(self) -> None:
        if self._display is not None:
            self._display.show_busy(self.current_mv)

    def _signal_error(self) -> None:
        if self._display is not None:
            self._display.show_error()
        if self._error_led is not None:
            self._error_led.blink()

    def increase_mana_value(self) -> None:
        if self.current_mv < self.max_mana_value:
            self.current_mv += 1
            self._signal_value()

    def decrease_mana_value(self) -> None:
        if self.current_mv > self.min_mana_value:
            self.current_mv -= 1
            self._signal_value()

    def reset_mana_value(self) -> None:
        self.current_mv = self.min_mana_value
        self._signal_value()

    def summon(self) -> None:
        if not self._print_lock.acquire(blocking=False):
            log.debug("summon() ignored: print in progress")
            return
        try:
            self._signal_busy()
            card = select_creature(self.db_path, self.current_mv)
            if card is None:
                log.warning("No creatures at MV %d in pool", self.current_mv)
                self._signal_error()
                return
            try:
                art = load_art(self.db_path, card)
                print_token(card_to_token_spec(card), self.device, art)
                self.last_card = card
                log.info("Summoned: %s (MV %d)", card.name, card.mana_value)
                self._signal_value()
            except OSError as e:
                log.error("Print failed for '%s': %s", card.name, e)
                self._signal_error()
        finally:
            self._print_lock.release()

    def reprint_last(self) -> None:
        if self.last_card is None:
            return
        if not self._print_lock.acquire(blocking=False):
            log.debug("reprint_last() ignored: print in progress")
            return
        try:
            self._signal_busy()
            art = load_art(self.db_path, self.last_card)
            print_token(card_to_token_spec(self.last_card), self.device, art)
            log.info("Reprinted: %s (MV %d)", self.last_card.name, self.last_card.mana_value)
            self._signal_value()
        except OSError as e:
            log.error("Reprint failed for '%s': %s", self.last_card.name, e)
            self._signal_error()
        finally:
            self._print_lock.release()

    def wait_for_shutdown(self) -> None:
        self._shutdown_event.wait()

    def shutdown(self) -> None:
        if self._display is not None:
            self._display.show_off()
        self._shutdown_event.set()
        if self._os_shutdown:
            log.info("shutdown() — initiating OS poweroff")
            subprocess.run(["systemctl", "poweroff"], check=False)
        else:
            log.info("shutdown() — gpio-play process stopped. To power off: sudo shutdown -h now")
