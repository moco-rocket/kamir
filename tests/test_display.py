from kamir.domain import Card
from kamir.play.display import format_card, _WIDTH


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


class TestFormatCard:
    def test_contains_name(self):
        assert "Grizzly Bears" in format_card(_card())

    def test_contains_mana_cost(self):
        assert "{1}{G}" in format_card(_card())

    def test_contains_type_line(self):
        assert "Creature - Bear" in format_card(_card())

    def test_contains_power_toughness(self):
        assert "2/2" in format_card(_card())

    def test_contains_expansion(self):
        assert "2ED" in format_card(_card())

    def test_no_oracle_shows_placeholder(self):
        assert "(no text)" in format_card(_card(oracle_text=""))

    def test_oracle_text_rendered(self):
        output = format_card(_card(oracle_text="Flying, vigilance"))
        assert "Flying, vigilance" in output

    def test_long_oracle_wrapped(self):
        long_text = "A" * (_WIDTH + 10)
        output = format_card(_card(oracle_text=long_text))
        for line in output.split("\n"):
            assert len(line) <= _WIDTH + 2  # +2 for leading spaces in oracle block

    def test_header_name_and_cost_on_same_line(self):
        card = _card(name="Serra Angel", mana_cost="{3}{W}{W}")
        header_line = format_card(card).split("\n")[1]
        assert "Serra Angel" in header_line
        assert "{3}{W}{W}" in header_line
