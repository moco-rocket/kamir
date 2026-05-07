from kamir.domain import Card
from kamir.printer.render import Cut, Rule, TextLine, _PRINTER_WIDTH, render_card


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


class TestRenderCard:
    def test_ends_with_cut(self):
        assert isinstance(render_card(_card())[-1], Cut)

    def test_name_is_bold_and_uppercase(self):
        bold = [i for i in render_card(_card()) if isinstance(i, TextLine) and i.bold]
        assert any("GRIZZLY BEARS" in line.text for line in bold)

    def test_mana_cost_present(self):
        text = " ".join(i.text for i in render_card(_card()) if isinstance(i, TextLine))
        assert "{1}{G}" in text

    def test_type_line_present(self):
        text = " ".join(i.text for i in render_card(_card()) if isinstance(i, TextLine))
        assert "Creature - Bear" in text

    def test_power_toughness_present(self):
        text = " ".join(i.text for i in render_card(_card()) if isinstance(i, TextLine))
        assert "2/2" in text

    def test_expansion_present(self):
        text = " ".join(i.text for i in render_card(_card()) if isinstance(i, TextLine))
        assert "2ED" in text

    def test_empty_oracle_shows_placeholder(self):
        text = " ".join(i.text for i in render_card(_card(oracle_text="")) if isinstance(i, TextLine))
        assert "(no text)" in text

    def test_oracle_wrapped_at_printer_width(self):
        long_text = "A" * (_PRINTER_WIDTH + 10)
        for instr in render_card(_card(oracle_text=long_text)):
            if isinstance(instr, TextLine):
                assert len(instr.text) <= _PRINTER_WIDTH

    def test_has_at_least_three_rules(self):
        rules = [i for i in render_card(_card()) if isinstance(i, Rule)]
        assert len(rules) >= 3

    def test_long_name_splits_to_two_bold_lines(self):
        long_name = "A" * 30
        bold = [i for i in render_card(_card(name=long_name, mana_cost="{W}{W}{W}")) if isinstance(i, TextLine) and i.bold]
        assert len(bold) == 2

    def test_no_pt_omits_slash(self):
        text = " ".join(i.text for i in render_card(_card(power="", toughness="")) if isinstance(i, TextLine))
        assert "/" not in text
