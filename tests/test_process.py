from io import BytesIO

import pytest
from PIL import Image

from kamir.images.process import process_image


def _make_jpeg(w: int = 400, h: int = 560, color: int = 128) -> bytes:
    img = Image.new("L", (w, h), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_rgb_jpeg(w: int = 400, h: int = 560) -> bytes:
    img = Image.new("RGB", (w, h), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestProcessImage:
    def test_output_is_jpeg_bytes(self):
        raw = _make_jpeg()
        result = process_image(raw, resize=(223, 310), crop=(26, 47, 197, 147))
        assert isinstance(result, bytes)
        assert result[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_output_dimensions_match_crop(self):
        raw = _make_jpeg()
        crop = (26, 47, 197, 147)
        result = process_image(raw, resize=(223, 310), crop=crop)
        img = Image.open(BytesIO(result))
        expected_w = crop[2] - crop[0]
        expected_h = crop[3] - crop[1]
        assert img.size == (expected_w, expected_h)

    def test_rgb_input_converted_to_grayscale(self):
        raw = _make_rgb_jpeg()
        result = process_image(raw, resize=(223, 310), crop=(26, 47, 197, 147))
        img = Image.open(BytesIO(result))
        assert img.mode == "L"

    def test_grayscale_input_stays_grayscale(self):
        raw = _make_jpeg()
        result = process_image(raw, resize=(223, 310), crop=(26, 47, 197, 147))
        img = Image.open(BytesIO(result))
        assert img.mode == "L"

    def test_different_crop_box(self):
        raw = _make_jpeg(500, 700)
        crop = (0, 0, 100, 100)
        result = process_image(raw, resize=(500, 700), crop=crop)
        img = Image.open(BytesIO(result))
        assert img.size == (100, 100)
