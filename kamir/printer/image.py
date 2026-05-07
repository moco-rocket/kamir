import io
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

from kamir.domain import Card
from kamir.printer.render import RasterImage

log = logging.getLogger(__name__)

WIDTH_DOTS = 192  # ESC * nH must be 0 on MJ-5890K; 192 = 0xC0 fits in single byte
HEIGHT_DOTS = 192  # 24mm × 24mm at 8 dots/mm

_HEADERS = {
    "User-Agent": "kamir/1.0 (Momir Basic play tool)",
    "Accept": "application/json",
}
_TIMEOUT = 10
_SCRYFALL_DELAY = 0.1  # seconds between Scryfall API requests


def fetch_art(card: Card) -> RasterImage | None:
    """Fetch card art from Scryfall and return an ESC/POS RasterImage, or None on any failure."""
    try:
        card_data = _fetch_card_data(card)
        if card_data is None:
            return None
        art_url = _extract_art_crop_url(card_data)
        if not art_url:
            return None
        return fetch_art_from_url(art_url)
    except Exception as e:
        log.debug("fetch_art failed for %s/%s: %s", card.expansion, card.collector_number, e)
        return None


def fetch_art_from_url(url: str) -> RasterImage | None:
    """Download image from CDN URL and convert to ESC/POS raster, or None on failure."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return _to_raster(resp.read())
    except Exception as e:
        log.debug("fetch_art_from_url failed for %s: %s", url, e)
        return None


def batch_fetch_art_crop_urls(cards: list[Card]) -> dict[str, str]:
    """Batch-fetch art_crop URLs using POST /cards/collection (75 cards/batch).

    Falls back to individual named search for cards Scryfall can't resolve by set/number.
    Returns dict[card_name -> art_crop_url].
    """
    result: dict[str, str] = {}

    for i in range(0, len(cards), 75):
        batch = cards[i:i + 75]
        by_key = {(c.expansion.lower(), c.collector_number): c for c in batch}
        identifiers = [
            {"set": c.expansion.lower(), "collector_number": c.collector_number}
            for c in batch
        ]

        try:
            body = json.dumps({"identifiers": identifiers}).encode()
            req = urllib.request.Request(
                "https://api.scryfall.com/cards/collection",
                data=body,
                headers={**_HEADERS, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                resp = json.loads(r.read())
        except Exception as e:
            log.debug("batch collection request failed (batch %d): %s", i // 75, e)
            time.sleep(_SCRYFALL_DELAY)
            continue

        for card_data in resp.get("data", []):
            url = _extract_art_crop_url(card_data)
            if url:
                result[card_data["name"]] = url

        for nf in resp.get("not_found", []):
            key = (nf.get("set", ""), nf.get("collector_number", ""))
            card = by_key.get(key)
            if card is None:
                continue
            cd = _fetch_card_data(card)
            if cd:
                url = _extract_art_crop_url(cd)
                if url:
                    result[card.name] = url
            time.sleep(_SCRYFALL_DELAY)

        time.sleep(_SCRYFALL_DELAY)

    return result


def _extract_art_crop_url(card_data: dict) -> str | None:
    # DFCs store image_uris per face; use front face as fallback
    image_uris = card_data.get("image_uris") or (
        card_data.get("card_faces", [{}])[0].get("image_uris", {})
    )
    return image_uris.get("art_crop")


def _fetch_card_data(card: Card) -> dict | None:
    """Fetch card JSON from Scryfall.

    Tries set+collector-number first; falls back to exact-name search when
    Scryfall returns an HTTP error (e.g. 400 for non-standard set codes like '40k').
    """
    def _get(url: str) -> dict:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return json.loads(r.read())

    try:
        return _get(
            f"https://api.scryfall.com/cards/{card.expansion.lower()}/{card.collector_number}"
        )
    except urllib.error.HTTPError:
        log.debug(
            "set+number lookup failed (%s/%s), retrying by name",
            card.expansion, card.collector_number,
        )

    try:
        return _get(
            "https://api.scryfall.com/cards/named?"
            + urllib.parse.urlencode({"exact": card.name})
        )
    except Exception:
        return None


def _to_raster(img_bytes: bytes) -> RasterImage:
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    img = img.resize((WIDTH_DOTS, HEIGHT_DOTS), Image.LANCZOS)
    img = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    # PIL "1" tobytes: 0=black→0-bit, 1=white→1-bit, packed MSB-first.
    # ESC/POS GS v 0: 1=print (black). Invert all bits.
    data = bytes(b ^ 0xFF for b in img.tobytes("raw", "1"))
    return RasterImage(data=data, width_bytes=WIDTH_DOTS // 8, height=HEIGHT_DOTS)
