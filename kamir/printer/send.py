import logging
import os

from kamir.domain import Card
from kamir.printer.render import Cut, Instruction, RasterImage, Rule, TextLine, render_card

log = logging.getLogger(__name__)

_ESC = b"\x1b"
_GS = b"\x1d"
_INIT = _ESC + b"@"          # ESC @ — initialize printer, clear buffer
_BOLD_ON = _ESC + b"E\x01"
_BOLD_OFF = _ESC + b"E\x00"
_CUT_FULL = _GS + b"VA\x00"  # GS V A 0 — full paper cut
# ESC * 0 — 8-dot single-density bit image (more widely supported than GS v 0)
_ESC_STAR = _ESC + b"\x2a\x00"
_ESC_LINESP_8 = _ESC + b"\x33\x08"  # ESC 3 8 — set line spacing to 8 dots
_ESC_LINESP_DEF = _ESC + b"\x32"    # ESC 2 — restore default line spacing
_LF = b"\x0a"

_RULE_THICK = ("=" * 32 + "\n").encode("ascii")
_RULE_THIN = ("-" * 32 + "\n").encode("ascii")


def _raster_bands(instr: RasterImage) -> bytes:
    """Encode a row-major raster as ESC * 8-dot single-density column bands.

    GS v 0 is not supported by all budget printers; ESC * is universal.
    The stored raster is row-major (each byte = 8 horizontal dots); ESC *
    expects column-major within each 8-row band (each byte = 8 vertical dots).
    """
    raster = instr.data
    wb = instr.width_bytes     # bytes per row
    w = wb * 8                 # dots wide
    nL, nH = w & 0xFF, w >> 8
    band_header = _ESC_STAR + bytes([nL, nH])

    out = bytearray(_ESC_LINESP_8)
    for band in range(instr.height // 8):
        out += band_header
        base = band * 8 * wb
        for c_g in range(wb):       # column group (8 columns per group)
            rows = [raster[base + d * wb + c_g] for d in range(8)]
            for k in range(8):      # column within group
                col_byte = 0
                shift = 7 - k
                for d in range(8):  # dot row within band
                    col_byte |= ((rows[d] >> shift) & 1) << (7 - d)
                out.append(col_byte)
        out += _LF
    out += _ESC_LINESP_DEF
    return bytes(out)


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
            expected = instr.width_bytes * instr.height
            if len(instr.data) != expected:
                raise ValueError(
                    f"RasterImage data {len(instr.data)} B != "
                    f"width_bytes*height={expected} B — re-run 'kamir build-db --force'"
                )
            buf += _raster_bands(instr)
        elif isinstance(instr, Cut):
            buf += _CUT_FULL
    return bytes(buf)


def print_card(card: Card, device: str, art: RasterImage | None = None) -> None:
    """Render card and write ESC/POS bytes to the thermal printer device."""
    data = _encode(render_card(card, art))
    log.debug("print_card: %d B → %s", len(data), device)
    fd = os.open(device, os.O_WRONLY)
    try:
        pos = 0
        while pos < len(data):
            pos += os.write(fd, data[pos:])
    finally:
        os.close(fd)
