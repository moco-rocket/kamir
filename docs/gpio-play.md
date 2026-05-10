# Kamir — GPIO Play Mode

GPIO button-driven Momir Basic on a Raspberry Pi.
Press buttons to set mana value and summon creatures; the thermal printer
outputs a card receipt automatically.

---

## Hardware

| Component | Notes |
|---|---|
| Raspberry Pi (any model with 40-pin GPIO) | Bookworm 64-bit recommended |
| MJ-5890K thermal printer | USB `/dev/usb/lp0` |
| 4× tactile push buttons | pull-up wired (BCM pins below) |
| Grove - 4-Digit Display (TM1637) | CLK/DIO wired to BCM pins below |
| 1× LED + 220 Ω resistor | error indicator |

---

## Wiring

### Buttons (BCM pin numbers, pull-up to 3.3 V via internal pull-up)

| Button | BCM pin | Action (short press) | Action (long press ≥ 1 s) |
|---|---|---|---|
| POWER | 5 | — | Stop process (+ OS poweroff if `os_shutdown = true`) |
| MV DOWN | 13 | Decrease mana value | Reset mana value to 0 |
| MV UP | 19 | Increase mana value | — |
| SUMMON | 26 | Summon & print card | Reprint last card |

Wire each button between the BCM pin and GND. Internal pull-ups are enabled
by gpiozero (`pull_up=True`).

### Grove - 4-Digit Display (TM1637)

| Grove wire | Raspberry Pi pin |
|---|---|
| CLK (yellow) | BCM 23 (physical 16) |
| DIO (white) | BCM 24 (physical 18) |
| VCC (red) | 3.3 V or 5 V |
| GND (black) | GND |

> **Package name:** `raspberrypi-tm1637` (PyPI).  
> **Import name:** `import tm1637` — do **not** install the unrelated `tm1637` package.

### Error LED

Wire an LED (with 220 Ω series resistor) between BCM 21 (physical 40) and GND.

---

## Software Setup

Install kamir with `uv tool install` — GPIO dependencies are declared with
`sys_platform == 'linux'` markers and install automatically on the Pi:

```bash
uv tool install git+https://github.com/moco-rocket/kamir.git
# or upgrade an existing install:
uv tool upgrade kamir
```

This installs `gpiozero`, `raspberrypi-tm1637`, and `lgpio` alongside kamir.

### polkit setup (required for `os_shutdown = true`)

By default, polkit only allows `systemctl poweroff` from interactive login sessions.
A polkit rule grants the same permission to the kamir service process.
A ready-made rule file is provided in `deploy/`:

```bash
sudo cp deploy/10-kamir-poweroff.pkla \
    /etc/polkit-1/localauthority/50-local.d/
```

No reboot or service restart needed — polkit picks up the file immediately.

Skip this step if you leave `os_shutdown = false` (the default).

---

## config.toml

Uncomment and adjust the GPIO section in `config.toml`:

```toml
[gpio.play]
initial_mana_value = 0
min_mana_value     = 0
max_mana_value     = 16
bounce_time        = 0.05
hold_time          = 1.0
os_shutdown        = true   # long-press POWER runs: systemctl poweroff

[gpio.buttons]   # BCM pin numbers
power   = 5
mv_down = 13
mv_up   = 19
summon  = 26

[gpio.display]
clk            = 23
dio            = 24
brightness     = 2
digits         = 4
visible_digits = 2
right_align    = true

[gpio.error_led]
pin = 21
```

---

## Standalone Tests (Before Running `gpio-play`)

Run these checks individually before starting the full session.
The scripts below use kamir's own modules; run them via the cloned repo:

```bash
cd ~/dev/kamir   # or wherever you cloned the repo
uv run python3
```

### Button test

Press each button and verify GPIO reads correctly:

```python
from gpiozero import Button
import time

for pin, name in [(5, "POWER"), (13, "MV_DOWN"), (19, "MV_UP"), (26, "SUMMON")]:
    b = Button(pin, pull_up=True)
    print(f"Press {name} (BCM {pin}) ...")
    b.wait_for_press()
    print(f"  {name} pressed OK")
    time.sleep(0.3)
```

### 7-segment display test

Verify the Grove 4-Digit Display shows values 0–16 then error/off:

```python
from kamir.hardware.tm1637_display import Tm1637Display
import time

d = Tm1637Display(clk=23, dio=24, brightness=2)
for mv in range(17):
    d.show_value(mv)
    time.sleep(0.2)
d.show_busy(0)   # "----"
time.sleep(0.5)
d.show_error()   # "Err "
time.sleep(0.5)
d.show_off()
print("Display test complete")
```

### Error LED test

```python
from kamir.hardware.gpio_led import GpioErrorLed
import time

led = GpioErrorLed(pin=21)
led.on();  time.sleep(1)
led.off(); time.sleep(0.5)
led.blink()   # 3 short blinks in background
time.sleep(2)
print("LED test complete")
```

---

## Running `gpio-play`

```bash
kamir --config config.toml gpio-play
```

Long-press POWER (≥ 1 s) to stop the process cleanly
(and power off the OS if `os_shutdown = true` in `[gpio.play]`).
The display shows `----` while printing and returns to the mana value on completion.
On error (no card at that MV, or printer fault) the display shows `Err` and the
error LED blinks three times.

---

## systemd Autostart

**Enable systemd only after manual testing is confirmed working.**

A template is provided at `deploy/kamir-gpio-play.service.example`.
Two placeholders must be replaced before installing:

| Placeholder | What to put |
|---|---|
| `CHANGE_THIS_REPO_DIR` | Absolute path to the cloned repository, e.g. `/home/pi/dev/kamir` |
| `CHANGE_THIS_KAMIR_BIN` | Path to the `kamir` binary — see below |

**`KAMIR_BIN` by install method:**

```
uv tool install  →  /home/pi/.local/bin/kamir        (or: which kamir)
dev checkout     →  /home/pi/dev/kamir/.venv/bin/kamir
```

**Install steps:**

```bash
# 1. Copy the template
cp deploy/kamir-gpio-play.service.example /tmp/kamir-gpio-play.service

# 2. Edit the two placeholders
#    CHANGE_THIS_REPO_DIR  → e.g. /home/pi/dev/kamir
#    CHANGE_THIS_KAMIR_BIN → e.g. /home/pi/.local/bin/kamir  (uv tool install)
nano /tmp/kamir-gpio-play.service

# 3. Install and enable
sudo cp /tmp/kamir-gpio-play.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kamir-gpio-play

# 4. Confirm it started
sudo journalctl -u kamir-gpio-play -f
```

To stop and disable:

```bash
sudo systemctl disable --now kamir-gpio-play
```
