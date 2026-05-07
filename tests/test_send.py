from kamir.domain import Card
from kamir.printer.render import RasterImage, render_card
from kamir.printer.send import _encode, _BOLD_ON, _CUT_FULL, _ESC_STAR, _INIT, print_card


def _card(**overrides) -> Card:
    base = dict(
        name="Grizzly Bears",
        mana_value=2,
        mana_cost="{1}{G}",
        type_line="Creature - Bear",
        oracle_text="",
        power="2",
        toughness="2",
        expansion="2ED",
        collector_number="178",
        layout="normal",
    )
    return Card(**{**base, **overrides})


class TestEncode:
    def test_starts_with_init_sequence(self):
        data = _encode(render_card(_card()))
        assert data[:2] == _INIT

    def test_contains_bold_on(self):
        data = _encode(render_card(_card()))
        assert _BOLD_ON in data

    def test_contains_cut_sequence(self):
        data = _encode(render_card(_card()))
        assert _CUT_FULL in data

    def test_name_encoded_uppercase(self):
        data = _encode(render_card(_card()))
        assert b"GRIZZLY BEARS" in data

    def test_non_ascii_replaced(self):
        card = _card(oracle_text="Ûlrich attacks.")
        data = _encode(render_card(card))
        assert b"?" in data              # replacement character inserted
        assert b"\xc3\x9b" not in data  # no raw UTF-8 bytes for Û

    def test_raster_image_encoded(self):
        art = RasterImage(data=bytes(24 * 144), width_bytes=24, height=144)
        data = _encode(render_card(_card(), art))
        # ESC * 0 nL=192 nH=0 — 8-dot single density, 192 dots wide
        assert _ESC_STAR + bytes([192, 0]) in data


class TestPrintCard:
    def test_writes_bytes_to_device_file(self, tmp_path):
        device = tmp_path / "fake_printer"
        device.touch()
        print_card(_card(), str(device))
        assert device.stat().st_size > 0

    def test_output_is_valid_bytes(self, tmp_path):
        device = tmp_path / "fake_printer"
        device.touch()
        print_card(_card(), str(device))
        data = device.read_bytes()
        assert data[:2] == _INIT
        assert _CUT_FULL in data

    def test_includes_raster_when_art_provided(self, tmp_path):
        art = RasterImage(data=bytes(24 * 144), width_bytes=24, height=144)
        device = tmp_path / "fake_printer"
        device.touch()
        print_card(_card(), str(device), art)
        assert _ESC_STAR in device.read_bytes()
