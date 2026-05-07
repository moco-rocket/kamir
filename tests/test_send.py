from kamir.domain import Card
from kamir.printer.render import render_card
from kamir.printer.send import _encode, _BOLD_ON, _CUT_FULL, _INIT, print_card


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
