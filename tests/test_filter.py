import pytest
from kamir.domain import Card
from kamir.filter.cards import (
    is_creature,
    is_allowed_set,
    has_valid_collector_number,
    is_front_face,
    is_within_base_set,
    is_funny,
    is_reprint,
    has_supported_layout,
    canonical_name,
    normalize_oracle,
    wrap_oracle,
    filter_cards,
    SUPPORTED_LAYOUTS,
)


class TestIsCreature:
    def test_creature(self, make_card):
        assert is_creature(make_card(types="Creature")) is True

    def test_artifact_creature(self, make_card):
        assert is_creature(make_card(types="Artifact Creature")) is True

    def test_instant(self, make_card):
        assert is_creature(make_card(types="Instant")) is False

    def test_missing_types(self, make_card):
        assert is_creature(make_card(types=None)) is False


class TestIsAllowedSet:
    def test_in_list(self, make_card):
        assert is_allowed_set(make_card(setCode="2ED"), {"2ED", "LEA"}) is True

    def test_not_in_list(self, make_card):
        assert is_allowed_set(make_card(setCode="XXX"), {"2ED", "LEA"}) is False

    def test_empty_allowed(self, make_card):
        assert is_allowed_set(make_card(setCode="2ED"), set()) is False


class TestHasValidCollectorNumber:
    def test_numeric(self, make_card):
        assert has_valid_collector_number(make_card(number="178")) is True

    def test_alpha_suffix(self, make_card):
        assert has_valid_collector_number(make_card(number="15a")) is False

    def test_star(self, make_card):
        assert has_valid_collector_number(make_card(number="★1")) is False


class TestIsFrontFace:
    def test_no_side(self, make_card):
        assert is_front_face(make_card(side=None)) is True

    def test_side_a(self, make_card):
        assert is_front_face(make_card(side="a")) is True

    def test_side_b(self, make_card):
        assert is_front_face(make_card(side="b")) is False


class TestIsWithinBaseSet:
    def test_within(self, make_card):
        assert is_within_base_set(make_card(number="178", baseSetSize=302)) is True

    def test_equal(self, make_card):
        assert is_within_base_set(make_card(number="302", baseSetSize=302)) is True

    def test_beyond(self, make_card):
        assert is_within_base_set(make_card(number="303", baseSetSize=302)) is False


class TestFlags:
    def test_is_funny_true(self, make_card):
        assert is_funny(make_card(isFunny=1)) is True

    def test_is_funny_false(self, make_card):
        assert is_funny(make_card(isFunny=0)) is False

    def test_is_reprint_true(self, make_card):
        assert is_reprint(make_card(isReprint=1)) is True


class TestHasSupportedLayout:
    @pytest.mark.parametrize("layout", SUPPORTED_LAYOUTS)
    def test_supported(self, make_card, layout):
        assert has_supported_layout(make_card(layout=layout)) is True

    def test_split_unsupported(self, make_card):
        assert has_supported_layout(make_card(layout="split")) is False


class TestCanonicalName:
    def test_prefers_ascii_name(self, make_card):
        c = make_card(asciiName="Aetherling", faceName="Ætherling", name="Ætherling")
        assert canonical_name(c) == "Aetherling"

    def test_falls_back_to_face_name(self, make_card):
        c = make_card(asciiName=None, faceName="Front Face", name="Full Name")
        assert canonical_name(c) == "Front Face"

    def test_falls_back_to_name(self, make_card):
        c = make_card(asciiName=None, faceName=None, name="Grizzly Bears")
        assert canonical_name(c) == "Grizzly Bears"


class TestNormalizeOracle:
    def test_strips_accent(self):
        assert normalize_oracle("Ûlrich") == "Ulrich"

    def test_empty(self):
        assert normalize_oracle("") == ""

    def test_none(self):
        assert normalize_oracle(None) == ""

    def test_plain_text_unchanged(self):
        assert normalize_oracle("Deal 2 damage.") == "Deal 2 damage."


class TestWrapOracle:
    def test_short_line_unchanged(self):
        assert wrap_oracle("Flying") == "Flying"

    def test_long_line_wraps(self):
        result = wrap_oracle("A" * 40, width=39)
        assert len(result.split("\n")) == 2

    def test_double_space_becomes_paragraph_break(self):
        assert "\n" in wrap_oracle("Flying  Haste")

    def test_literal_backslash_n_becomes_paragraph_break(self):
        result = wrap_oracle("Flying\\nHaste")
        assert result == "Flying\nHaste"

    def test_empty(self):
        assert wrap_oracle("") == ""

    def test_none(self):
        assert wrap_oracle(None) == ""


class TestFilterCards:
    def test_basic_creature_passes(self, make_card):
        result = filter_cards([make_card()], {"2ED"})
        assert len(result) == 1
        assert result[0].name == "Grizzly Bears"

    def test_returns_card_objects(self, make_card):
        result = filter_cards([make_card()], {"2ED"})
        assert isinstance(result[0], Card)
        assert result[0].mana_value == 2
        assert result[0].collector_number == "178"

    def test_non_creature_excluded(self, make_card):
        assert filter_cards([make_card(types="Instant")], {"2ED"}) == []

    def test_disallowed_set_excluded(self, make_card):
        assert filter_cards([make_card(setCode="XXX")], {"2ED"}) == []

    def test_funny_excluded(self, make_card):
        assert filter_cards([make_card(isFunny=1)], {"2ED"}) == []

    def test_reprint_excluded(self, make_card):
        assert filter_cards([make_card(isReprint=1)], {"2ED"}) == []

    def test_alpha_collector_number_excluded(self, make_card):
        assert filter_cards([make_card(number="15a")], {"2ED"}) == []

    def test_side_b_excluded(self, make_card):
        assert filter_cards([make_card(side="b")], {"2ED"}) == []

    def test_deduplication(self, make_card):
        cards = [make_card(), make_card(setCode="LEA")]
        result = filter_cards(cards, {"2ED", "LEA"})
        assert len(result) == 1

    def test_oracle_normalized(self, make_card):
        result = filter_cards([make_card(text="Ûlrich deals damage.")], {"2ED"})
        assert "Û" not in result[0].oracle_text

    def test_type_line_mapped(self, make_card):
        result = filter_cards([make_card(type="Creature - Bear")], {"2ED"})
        assert result[0].type_line == "Creature - Bear"
