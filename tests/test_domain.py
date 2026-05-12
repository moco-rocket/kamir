from kamir.domain import Card, TokenSpec, card_to_token_spec


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


class TestTokenSpec:
    def test_required_fields(self):
        spec = TokenSpec(name="Goblin", type_line="Token Creature — Goblin", power="1", toughness="1")
        assert spec.name == "Goblin"
        assert spec.power == "1"
        assert spec.toughness == "1"

    def test_oracle_text_defaults_empty(self):
        spec = TokenSpec(name="X", type_line="T", power="1", toughness="1")
        assert spec.oracle_text == ""

    def test_frozen(self):
        spec = TokenSpec(name="X", type_line="T", power="1", toughness="1")
        try:
            spec.name = "Y"  # type: ignore[misc]
            assert False, "should have raised"
        except Exception:
            pass


class TestCardToTokenSpec:
    def test_copies_name(self):
        assert card_to_token_spec(_card()).name == "Grizzly Bears"

    def test_copies_type_line(self):
        assert card_to_token_spec(_card()).type_line == "Creature - Bear"

    def test_copies_power(self):
        assert card_to_token_spec(_card()).power == "2"

    def test_copies_toughness(self):
        assert card_to_token_spec(_card()).toughness == "2"

    def test_copies_oracle_text(self):
        card = _card(oracle_text="Flying")
        assert card_to_token_spec(card).oracle_text == "Flying"

    def test_drops_expansion(self):
        spec = card_to_token_spec(_card())
        assert not hasattr(spec, "expansion")

    def test_drops_mana_cost(self):
        spec = card_to_token_spec(_card())
        assert not hasattr(spec, "mana_cost")

    def test_returns_token_spec_type(self):
        assert isinstance(card_to_token_spec(_card()), TokenSpec)
