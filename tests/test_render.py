from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from kamir.render.layout import (
    ORACLE_LINE_THRESHOLD,
    ORACLE_BASE_FONT_SIZE,
    ORACLE_FONT_SHRINK_PER_LINE,
)
from kamir.render import pdf as pdf_mod


def _oracle_font_size_fn(n):
    return pdf_mod._oracle_font_size(n)


def _oracle_leading_fn(n):
    return pdf_mod._oracle_leading(n)


def _type_font_size_fn(s):
    return pdf_mod._type_font_size(s)


class TestOracleFontSize:
    def test_below_threshold_returns_base(self):
        size = _oracle_font_size_fn(ORACLE_LINE_THRESHOLD - 1)
        assert size == pytest.approx(ORACLE_BASE_FONT_SIZE)

    def test_at_threshold_already_shrinks(self):
        # At exactly the threshold line count, shrinking begins (matches original behaviour)
        size = _oracle_font_size_fn(ORACLE_LINE_THRESHOLD)
        assert size < ORACLE_BASE_FONT_SIZE

    def test_above_threshold_shrinks(self):
        size = _oracle_font_size_fn(ORACLE_LINE_THRESHOLD + 2)
        assert size < ORACLE_BASE_FONT_SIZE

    def test_shrink_is_linear(self):
        s1 = _oracle_font_size_fn(ORACLE_LINE_THRESHOLD + 1)
        s2 = _oracle_font_size_fn(ORACLE_LINE_THRESHOLD + 2)
        assert pytest.approx(s1 - s2) == ORACLE_FONT_SHRINK_PER_LINE


class TestTypeFontSize:
    def test_short_type_returns_default(self):
        from kamir.render.layout import TYPE_FONT_SIZE, TYPE_MAX_CHARS
        size = _type_font_size_fn("Creature - Bear")
        assert size == pytest.approx(TYPE_FONT_SIZE)

    def test_long_type_returns_smaller(self):
        from kamir.render.layout import TYPE_FONT_SIZE
        long_type = "Legendary Creature - Human Advisor Wizard Cleric"
        size = _type_font_size_fn(long_type)
        assert size < TYPE_FONT_SIZE


class TestRenderCardPdf:
    @pytest.fixture
    def tmp_img(self, tmp_path) -> Path:
        img = Image.new("L", (171, 100), color=128)
        path = tmp_path / "test.jpg"
        img.save(path, format="JPEG")
        return path

    @pytest.fixture
    def sample_card(self):
        return {
            "name": "Grizzly Bears",
            "mana_value": 2,
            "mana_cost": "{1}{G}",
            "type": "Creature - Bear",
            "oracle": "No abilities.",
            "expansion": "2ED",
            "power": "2",
            "toughness": "2",
            "layout": "normal",
            "number": "178",
            "release_date": "1993-01-01",
        }

    def test_returns_bytes(self, sample_card, tmp_img):
        result = pdf_mod.render_card_pdf(sample_card, tmp_img)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_output_is_pdf(self, sample_card, tmp_img):
        result = pdf_mod.render_card_pdf(sample_card, tmp_img)
        assert result[:4] == b"%PDF"

    def test_write_creates_file(self, sample_card, tmp_img, tmp_path):
        pdf_dir = tmp_path / "pdf"
        dest = pdf_mod.write_card_pdf(sample_card, tmp_img, pdf_dir)
        assert dest.exists()
        assert dest.stat().st_size > 0

    def test_write_path_structure(self, sample_card, tmp_img, tmp_path):
        pdf_dir = tmp_path / "pdf"
        dest = pdf_mod.write_card_pdf(sample_card, tmp_img, pdf_dir)
        assert dest == pdf_dir / "2" / "Grizzly Bears.pdf"

    def test_empty_oracle_does_not_crash(self, sample_card, tmp_img):
        sample_card["oracle"] = ""
        result = pdf_mod.render_card_pdf(sample_card, tmp_img)
        assert result[:4] == b"%PDF"

    def test_long_oracle_does_not_crash(self, sample_card, tmp_img):
        sample_card["oracle"] = ("This is a very long oracle text. " * 10).strip()
        result = pdf_mod.render_card_pdf(sample_card, tmp_img)
        assert result[:4] == b"%PDF"
