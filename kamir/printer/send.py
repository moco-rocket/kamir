from kamir.domain import Card
from kamir.printer.image import fetch_art
from kamir.printer.render import Cut, Instruction, RasterImage, Rule, TextLine, render_card

_ESC = b"\x1b"
_GS = b"\x1d"
_INIT = _ESC + b"@"          # ESC @ — initialize printer, clear buffer
_BOLD_ON = _ESC + b"E\x01"
_BOLD_OFF = _ESC + b"E\x00"
_CUT_FULL = _GS + b"VA\x00"  # GS V A 0 — full paper cut
_GS_RASTER = _GS + b"\x76\x30\x00"  # GS v 0 — raster bit image (normal density)

_RULE_THICK = ("=" * 32 + "\n").encode("ascii")
_RULE_THIN = ("-" * 32 + "\n").encode("ascii")


def _encode(instructions: list[Instruction]) -> bytes:
    buf = bytearray(_INIT)
    for instr in instructions:
        if isinstance(instr, TextLine):
            if instr.bold:
                buf += _BOLD_ON
            buf += (instr.text + "\n").encode("ascii", errors="replace")
            if instr.bold:
                buf += _BOLD_OFF
        elif isinstance(instr, Rule):
            buf += _RULE_THICK if instr.thick else _RULE_THIN
        elif isinstance(instr, RasterImage):
            buf += _GS_RASTER
            buf += bytes([
                instr.width_bytes & 0xFF,
                (instr.width_bytes >> 8) & 0xFF,
                instr.height & 0xFF,
                (instr.height >> 8) & 0xFF,
            ])
            buf += instr.data
        elif isinstance(instr, Cut):
            buf += _CUT_FULL
    return bytes(buf)


def print_card(card: Card, device: str) -> None:
    """Render card and write ESC/POS bytes to the thermal printer device."""
    art = fetch_art(card)
    data = _encode(render_card(card, art))
    with open(device, "wb") as f:
        f.write(data)
