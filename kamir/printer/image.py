import io
import json
import logging
import urllib.request

from PIL import Image

from kamir.domain import Card
from kamir.printer.render import RasterImage

log = logging.getLogger(__name__)

WIDTH_DOTS = 384
HEIGHT_DOTS = 192  # 24mm at 8 dots/mm; art_crop images are wider than tall

_HEADERS = {"User-Agent": "kamir/1.0 (Momir Basic play tool)"}
_TIMEOUT = 10


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
    except Exception as e:
        log.debug("fetch_art failed for %s/%s: %s", card.expansion, card.collector_number, e)
        return None


def _to_raster(img_bytes: bytes) -> RasterImage:
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    img = img.resize((WIDTH_DOTS, HEIGHT_DOTS), Image.LANCZOS)
    img = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    # PIL "1" tobytes: 0=black→0-bit, 1=white→1-bit, packed MSB-first.
    # ESC/POS GS v 0: 1=print (black). Invert all bits.
    data = bytes(b ^ 0xFF for b in img.tobytes())
    return RasterImage(data=data, width_bytes=WIDTH_DOTS // 8, height=HEIGHT_DOTS)
