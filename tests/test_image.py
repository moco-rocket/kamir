import io
import json
import urllib.error
from unittest.mock import MagicMock

import pytest
from PIL import Image

from kamir.domain import Card
from kamir.printer.image import HEIGHT_DOTS, WIDTH_DOTS, _to_raster, fetch_art
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
        assert result.width_bytes == WIDTH_DOTS // 8
        assert result.height == HEIGHT_DOTS

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
    def _mock_resp(self, body: bytes) -> MagicMock:
        m = MagicMock()
        m.read.return_value = body
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        return m

    def test_returns_none_on_network_error(self, mocker):
        mocker.patch("urllib.request.urlopen", side_effect=OSError("network error"))
        assert fetch_art(_card()) is None

    def test_returns_none_when_no_art_url(self, mocker):
        resp = self._mock_resp(json.dumps({"image_uris": {}}).encode())
        mocker.patch("urllib.request.urlopen", return_value=resp)
        assert fetch_art(_card()) is None

    def test_returns_raster_on_success(self, mocker):
        card_resp = self._mock_resp(
            json.dumps({"image_uris": {"art_crop": "https://example.com/art.jpg"}}).encode()
        )
        img_resp = self._mock_resp(_make_jpeg())
        mocker.patch("urllib.request.urlopen", side_effect=[card_resp, img_resp])
        assert isinstance(fetch_art(_card()), RasterImage)

    def test_dfc_uses_card_faces_fallback(self, mocker):
        card_resp = self._mock_resp(json.dumps({
            "card_faces": [
                {"image_uris": {"art_crop": "https://example.com/front.jpg"}},
                {"image_uris": {"art_crop": "https://example.com/back.jpg"}},
            ]
        }).encode())
        img_resp = self._mock_resp(_make_jpeg())
        mocker.patch("urllib.request.urlopen", side_effect=[card_resp, img_resp])
        assert isinstance(fetch_art(_card()), RasterImage)

    def test_falls_back_to_named_lookup_on_http_error(self, mocker):
        # Scryfall returns 400 for the set+number URL (e.g. "40k/1") but the
        # named endpoint succeeds — should still return art.
        http_400 = urllib.error.HTTPError(
            "https://api.scryfall.com/cards/40k/1", 400, "Bad Request", {}, io.BytesIO(b"")
        )
        card_resp = self._mock_resp(
            json.dumps({"image_uris": {"art_crop": "https://example.com/art.jpg"}}).encode()
        )
        img_resp = self._mock_resp(_make_jpeg())
        mocker.patch("urllib.request.urlopen", side_effect=[http_400, card_resp, img_resp])
        assert isinstance(fetch_art(_card(expansion="40K", collector_number="1")), RasterImage)

    def test_returns_none_when_both_lookups_fail(self, mocker):
        http_400 = urllib.error.HTTPError(
            "https://api.scryfall.com/cards/40k/1", 400, "Bad Request", {}, io.BytesIO(b"")
        )
        mocker.patch("urllib.request.urlopen", side_effect=[http_400, OSError("network error")])
        assert fetch_art(_card(expansion="40K", collector_number="1")) is None
