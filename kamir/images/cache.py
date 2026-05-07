import logging
import shutil
from pathlib import Path

import requests

from kamir.images.fetch import fetch_card_image_bytes
from kamir.images.process import process_image

log = logging.getLogger(__name__)


def image_path(img_dir: Path, card: dict) -> Path:
    mv = str(card["mana_value"])
    safe_name = card["name"].replace("/", "-")
    return img_dir / mv / f"{safe_name}.jpg"


def is_cached(img_dir: Path, card: dict) -> bool:
    return image_path(img_dir, card).exists()


def fetch_and_cache(
    card: dict,
    img_dir: Path,
    placeholder: Path,
    base_url: str,
    session: requests.Session,
    resize: tuple[int, int],
    crop: tuple[int, int, int, int],
    request_delay: float = 1.0,
) -> Path:
    """Fetch, process, and save a card image. Returns the saved path.

    Falls back to copying placeholder on any fetch/process error.
    """
    dest = image_path(img_dir, card)
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        raw = fetch_card_image_bytes(card, base_url, session, request_delay)
        processed = process_image(raw, resize, crop)
        dest.write_bytes(processed)
        log.info("Saved image: %s", dest)
    except Exception as exc:
        log.warning("Failed to fetch image for '%s': %s — using placeholder", card["name"], exc)
        shutil.copy2(placeholder, dest)

    return dest
