import logging
from pathlib import Path

from kamir.db.art import load_art
from kamir.domain import Card
from kamir.hardware.display import ManaDisplay
from kamir.hardware.leds import ErrorLed
from kamir.play.select import select_creature
from kamir.printer.send import print_card

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
    ) -> None:
        self.db_path = db_path
        self.device = device
        self.min_mana_value = min_mv
        self.max_mana_value = max_mv
        self.current_mv = initial_mv
        self.last_card: Card | None = None
        self._printing = False
        self._display = display
        self._error_led = error_led
        if self._display is not None:
            self._display.show_value(self.current_mv)

    def increase_mana_value(self) -> None:
        if self.current_mv < self.max_mana_value:
            self.current_mv += 1
            if self._display is not None:
                self._display.show_value(self.current_mv)

    def decrease_mana_value(self) -> None:
        if self.current_mv > self.min_mana_value:
            self.current_mv -= 1
            if self._display is not None:
                self._display.show_value(self.current_mv)

    def reset_mana_value(self) -> None:
        self.current_mv = self.min_mana_value
        if self._display is not None:
            self._display.show_value(self.current_mv)

    def summon(self) -> None:
        if self._printing:
            log.debug("summon() ignored: print in progress")
            return
        self._printing = True
        try:
            if self._display is not None:
                self._display.show_busy(self.current_mv)
            card = select_creature(self.db_path, self.current_mv)
            if card is None:
                log.warning("No creatures at MV %d in pool", self.current_mv)
                if self._display is not None:
                    self._display.show_error()
                if self._error_led is not None:
                    self._error_led.blink()
                return
            try:
                art = load_art(self.db_path, card)
                print_card(card, self.device, art)
                self.last_card = card
                log.info("Summoned: %s (MV %d)", card.name, card.mana_value)
                if self._display is not None:
                    self._display.show_value(self.current_mv)
            except OSError as e:
                log.error("Print failed for '%s': %s", card.name, e)
                if self._display is not None:
                    self._display.show_error()
                if self._error_led is not None:
                    self._error_led.blink()
        finally:
            self._printing = False

    def reprint_last(self) -> None:
        if self._printing:
            log.debug("reprint_last() ignored: print in progress")
            return
        if self.last_card is None:
            return
        self._printing = True
        try:
            if self._display is not None:
                self._display.show_busy(self.current_mv)
            art = load_art(self.db_path, self.last_card)
            print_card(self.last_card, self.device, art)
            log.info("Reprinted: %s (MV %d)", self.last_card.name, self.last_card.mana_value)
            if self._display is not None:
                self._display.show_value(self.current_mv)
        except OSError as e:
            log.error("Reprint failed for '%s': %s", self.last_card.name, e)
            if self._display is not None:
                self._display.show_error()
            if self._error_led is not None:
                self._error_led.blink()
        finally:
            self._printing = False

    def shutdown(self) -> None:
        log.info("shutdown() called — hardware shutdown not wired yet")
        if self._display is not None:
            self._display.show_off()
