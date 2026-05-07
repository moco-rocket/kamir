import io
import json
import urllib.request

from PIL import Image

from kamir.domain import Card
from kamir.printer.render import RasterImage

_WIDTH_DOTS = 384
_HEIGHT_DOTS = 192  # 24mm at 8 dots/mm; art_crop images are wider than tall

_HEADERS = {"User-Agent": "kamir/1.0 (Momir Basic play tool)"}
_TIMEOUT = 8


def fetch_art(card: Card) -> RasterImage | None:
    """Fetch card art from Scryfall and return an ESC/POS RasterImage, or None on any failure."""
    try:
        url = f"https://api.scryfall.com/cards/{card.expansion.lower()}/{card.collector_number}"
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            card_data = json.loads(resp.read())

        # DFCs store image_uris per face; use front face as fallback
        image_uris = card_data.get("image_uris") or (
            card_data.get("card_faces", [{}])[0].get("image_uris", {})
        )
        art_url = image_uris.get("art_crop")
        if not art_url:
            return None

        req2 = urllib.request.Request(art_url, headers=_HEADERS)
        with urllib.request.urlopen(req2, timeout=_TIMEOUT) as resp2:
            img_bytes = resp2.read()

        return _to_raster(img_bytes)
    except Exception:
        return None


def _to_raster(img_bytes: bytes) -> RasterImage:
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    img = img.resize((_WIDTH_DOTS, _HEIGHT_DOTS), Image.LANCZOS)

    pixels = img.tobytes()  # one byte per pixel (grayscale "L" mode), row-major
    width_bytes = _WIDTH_DOTS // 8
    buf = bytearray()
    for y in range(_HEIGHT_DOTS):
        for x_byte in range(width_bytes):
            byte_val = 0
            for bit in range(8):
                x = x_byte * 8 + bit
                # Dark pixel (< 128) → print dot; ESC/POS: 1 = print
                if pixels[y * _WIDTH_DOTS + x] < 128:
                    byte_val |= 0x80 >> bit
            buf.append(byte_val)

    return RasterImage(data=bytes(buf), width_bytes=width_bytes, height=_HEIGHT_DOTS)
