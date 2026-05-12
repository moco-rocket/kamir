from kamir.domain import Card, TokenSpec
from kamir.play.display import format_card, format_token, _WIDTH


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


def _spec(**overrides) -> TokenSpec:
    base = dict(
        name="Grizzly Bears",
        type_line="Creature - Bear",
        oracle_text="",
        power="2",
        toughness="2",
    )
    return TokenSpec(**{**base, **overrides})


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


class TestFormatToken:
    def test_name_in_second_line(self):
        lines = format_token(_spec()).split("\n")
        assert "Grizzly Bears" in lines[1]

    def test_contains_type_line(self):
        assert "Creature - Bear" in format_token(_spec())

    def test_contains_pt(self):
        assert "2/2" in format_token(_spec())

    def test_mana_cost_not_present(self):
        assert "{1}{G}" not in format_token(_spec())

    def test_expansion_not_present(self):
        assert "2ED" not in format_token(_spec())

    def test_empty_oracle_no_placeholder(self):
        # New design: empty oracle shows nothing, not "(no text)"
        assert "(no text)" not in format_token(_spec(oracle_text=""))

    def test_oracle_text_rendered(self):
        assert "Flying, vigilance" in format_token(_spec(oracle_text="Flying, vigilance"))

    def test_no_pt_shows_placeholder(self):
        assert "?/?" in format_token(_spec(power="", toughness=""))

    def test_name_before_pt(self):
        lines = format_token(_spec()).split("\n")
        name_line = next(i for i, ln in enumerate(lines) if "Grizzly Bears" in ln)
        pt_line = next(i for i, ln in enumerate(lines) if "2/2" in ln)
        assert name_line < pt_line

    def test_pt_before_type_line(self):
        lines = format_token(_spec()).split("\n")
        pt_line = next(i for i, ln in enumerate(lines) if "2/2" in ln)
        type_line = next(i for i, ln in enumerate(lines) if "Creature" in ln)
        assert pt_line < type_line

    def test_art_area_indicator_present(self):
        # Terminal display shows an art area label
        output = format_token(_spec())
        assert "アート欄" in output
