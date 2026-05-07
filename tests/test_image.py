import io

import pytest
from PIL import Image

from kamir.domain import Card
from kamir.printer.image import _HEIGHT_DOTS, _WIDTH_DOTS, _to_raster, fetch_art
from kamir.printer.render import RasterImage


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


def _make_jpeg(width: int = 100, height: int = 60) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestToRaster:
    def test_returns_raster_image(self):
        result = _to_raster(_make_jpeg())
        assert isinstance(result, RasterImage)

    def test_output_dimensions(self):
        result = _to_raster(_make_jpeg())
        assert result.width_bytes == _WIDTH_DOTS // 8
        assert result.height == _HEIGHT_DOTS

    def test_data_length_matches_dimensions(self):
        result = _to_raster(_make_jpeg())
        assert len(result.data) == result.width_bytes * result.height

    def test_dark_image_produces_mostly_set_bits(self):
        img = Image.new("L", (100, 60), color=0)  # all black
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        result = _to_raster(buf.getvalue())
        set_bits = sum(bin(b).count("1") for b in result.data)
        total_bits = len(result.data) * 8
        assert set_bits / total_bits > 0.9

    def test_light_image_produces_mostly_clear_bits(self):
        img = Image.new("L", (100, 60), color=255)  # all white
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        result = _to_raster(buf.getvalue())
        set_bits = sum(bin(b).count("1") for b in result.data)
        total_bits = len(result.data) * 8
        assert set_bits / total_bits < 0.1


class TestFetchArt:
    def test_returns_none_on_network_error(self, mocker):
        mocker.patch("urllib.request.urlopen", side_effect=OSError("network error"))
        assert fetch_art(_card()) is None

    def test_returns_none_when_no_art_url(self, mocker):
        import json
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"image_uris": {}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mocker.patch("urllib.request.urlopen", return_value=mock_resp)
        assert fetch_art(_card()) is None

    def test_returns_raster_on_success(self, mocker):
        import json
        from unittest.mock import MagicMock

        card_resp = MagicMock()
        card_resp.read.return_value = json.dumps(
            {"image_uris": {"art_crop": "https://example.com/art.jpg"}}
        ).encode()
        card_resp.__enter__ = lambda s: s
        card_resp.__exit__ = MagicMock(return_value=False)

        img_resp = MagicMock()
        img_resp.read.return_value = _make_jpeg()
        img_resp.__enter__ = lambda s: s
        img_resp.__exit__ = MagicMock(return_value=False)

        mocker.patch("urllib.request.urlopen", side_effect=[card_resp, img_resp])
        result = fetch_art(_card())
        assert isinstance(result, RasterImage)
