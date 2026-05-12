from kamir.domain import Card, TokenSpec
from kamir.printer.render import Cut, RasterImage, Rule, TextLine, _PRINTER_WIDTH, render_card, render_token


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

    def test_toughness_only_shows_pt(self):
        text = " ".join(i.text for i in render_card(_card(power="", toughness="*")) if isinstance(i, TextLine))
        assert "/*" in text

    def test_no_art_by_default(self):
        assert not any(isinstance(i, RasterImage) for i in render_card(_card()))

    def test_leading_blank_lines_before_content(self):
        instrs = render_card(_card())
        leading_blanks = 0
        for instr in instrs:
            if isinstance(instr, TextLine) and instr.text == "":
                leading_blanks += 1
            else:
                break
        assert leading_blanks >= 1

    def test_trailing_blank_lines_before_cut(self):
        instrs = render_card(_card())
        cut_idx = next(i for i, x in enumerate(instrs) if isinstance(x, Cut))
        trailing_blanks = 0
        for i in range(cut_idx - 1, -1, -1):
            if isinstance(instrs[i], TextLine) and instrs[i].text == "":
                trailing_blanks += 1
            else:
                break
        assert trailing_blanks >= 3

    def test_oracle_literal_backslash_n_produces_separate_lines(self):
        instrs = render_card(_card(oracle_text="Flying\\nHaste"))
        lines = [i.text for i in instrs if isinstance(i, TextLine)]
        assert "Flying" in lines
        assert "Haste" in lines

    def test_art_inserted_after_header_rule(self):
        art = RasterImage(data=bytes(48 * 192), width_bytes=48, height=192)
        instrs = render_card(_card(), art)
        art_idx = next(i for i, x in enumerate(instrs) if isinstance(x, RasterImage))
        # Must be preceded by the thick header rule (index 2 in normal layout)
        assert isinstance(instrs[art_idx - 1], Rule) and instrs[art_idx - 1].thick


class TestRenderToken:
    def test_ends_with_cut(self):
        assert isinstance(render_token(_spec())[-1], Cut)

    def test_name_is_bold_and_centered(self):
        bold = [i for i in render_token(_spec()) if isinstance(i, TextLine) and i.bold]
        assert any("Grizzly Bears" in line.text for line in bold)

    def test_pt_is_bold(self):
        bold = [i for i in render_token(_spec()) if isinstance(i, TextLine) and i.bold]
        assert any("2/2" in line.text for line in bold)

    def test_name_before_pt(self):
        instrs = render_token(_spec())
        text_lines = [i for i in instrs if isinstance(i, TextLine) and i.text.strip()]
        name_idx = next(i for i, t in enumerate(text_lines) if "Grizzly Bears" in t.text)
        pt_idx = next(i for i, t in enumerate(text_lines) if "2/2" in t.text)
        assert name_idx < pt_idx

    def test_pt_before_type_line(self):
        instrs = render_token(_spec())
        text_lines = [i for i in instrs if isinstance(i, TextLine) and i.text.strip()]
        pt_idx = next(i for i, t in enumerate(text_lines) if "2/2" in t.text)
        type_idx = next(i for i, t in enumerate(text_lines) if "Creature" in t.text)
        assert pt_idx < type_idx

    def test_type_line_present(self):
        text = " ".join(i.text for i in render_token(_spec()) if isinstance(i, TextLine))
        assert "Creature - Bear" in text

    def test_mana_cost_not_present(self):
        # TokenSpec has no mana cost; token layout omits it
        text = " ".join(i.text for i in render_token(_spec()) if isinstance(i, TextLine))
        assert "{1}{G}" not in text

    def test_expansion_not_present(self):
        text = " ".join(i.text for i in render_token(_spec()) if isinstance(i, TextLine))
        assert "2ED" not in text

    def test_no_art_produces_blank_lines(self):
        instrs = render_token(_spec())
        # When no art, fixed blank lines occupy the art space between name rule and P/T rule
        blank_text = [i for i in instrs if isinstance(i, TextLine) and i.text == ""]
        assert len(blank_text) >= 6  # _TOKEN_ART_LINES + trailing blanks

    def test_no_art_by_default_no_raster(self):
        assert not any(isinstance(i, RasterImage) for i in render_token(_spec()))

    def test_art_replaces_blank_lines(self):
        art = RasterImage(data=bytes(48 * 192), width_bytes=48, height=192)
        instrs_no_art = render_token(_spec())
        instrs_with_art = render_token(_spec(), art)
        assert any(isinstance(i, RasterImage) for i in instrs_with_art)
        # With art, fewer blank TextLine("") between name and P/T
        blank_no_art = sum(1 for i in instrs_no_art if isinstance(i, TextLine) and i.text == "")
        blank_with_art = sum(1 for i in instrs_with_art if isinstance(i, TextLine) and i.text == "")
        assert blank_with_art < blank_no_art

    def test_art_inserted_between_name_and_pt_rules(self):
        art = RasterImage(data=bytes(48 * 192), width_bytes=48, height=192)
        instrs = render_token(_spec(), art)
        art_idx = next(i for i, x in enumerate(instrs) if isinstance(x, RasterImage))
        assert isinstance(instrs[art_idx - 1], Rule) and instrs[art_idx - 1].thick

    def test_no_pt_shows_placeholder(self):
        text = " ".join(i.text for i in render_token(_spec(power="", toughness="")) if isinstance(i, TextLine))
        assert "?/?" in text

    def test_empty_oracle_omits_thin_rules(self):
        instrs_no_oracle = render_token(_spec(oracle_text=""))
        instrs_with_oracle = render_token(_spec(oracle_text="Flying"))
        thin_no_oracle = sum(1 for i in instrs_no_oracle if isinstance(i, Rule) and not i.thick)
        thin_with_oracle = sum(1 for i in instrs_with_oracle if isinstance(i, Rule) and not i.thick)
        assert thin_with_oracle > thin_no_oracle

    def test_has_at_least_three_thick_rules(self):
        assert sum(1 for i in render_token(_spec()) if isinstance(i, Rule) and i.thick) >= 3

    def test_trailing_blank_lines_before_cut(self):
        instrs = render_token(_spec())
        cut_idx = next(i for i, x in enumerate(instrs) if isinstance(x, Cut))
        trailing_blanks = 0
        for i in range(cut_idx - 1, -1, -1):
            if isinstance(instrs[i], TextLine) and instrs[i].text == "":
                trailing_blanks += 1
            else:
                break
        assert trailing_blanks >= 3
