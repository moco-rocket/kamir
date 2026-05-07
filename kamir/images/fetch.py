import logging
import time

import requests

log = logging.getLogger(__name__)

_DFC_LAYOUTS = {"transform", "meld", "modal_dfc"}


def _get_json(url: str, session: requests.Session) -> dict:
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_card_image_bytes(
    card: dict,
    base_url: str,
    session: requests.Session,
    request_delay: float = 1.0,
) -> bytes:
    """Fetch raw image bytes for a card from Scryfall.

    For DFC layouts, selects the front face matching card['name'].
    Raises requests.HTTPError or KeyError on unexpected API shape.
    """
    set_code = card["expansion"].lower()
    number = card["number"]
    name = card["name"]
    layout = card["layout"]

    api_url = f"{base_url}/cards/{set_code}/{number}"
    time.sleep(request_delay)

    data = _get_json(api_url, session)

    if layout in _DFC_LAYOUTS:
        faces = data.get("card_faces", [])
        matching = [f for f in faces if f.get("name") == name]
        if not matching:
            raise KeyError(f"No face named '{name}' in card_faces for {api_url}")
        image_url = matching[0]["image_uris"]["large"]
    else:
        image_url = data["image_uris"]["large"]

    log.debug("Fetching image: %s", image_url)
    img_resp = session.get(image_url, timeout=30)
    img_resp.raise_for_status()
    return img_resp.content
