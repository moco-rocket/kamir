from io import BytesIO
from PIL import Image


def process_image(
    raw_bytes: bytes,
    resize: tuple[int, int],
    crop: tuple[int, int, int, int],
) -> bytes:
    """Decode raw image bytes, convert to grayscale, resize, and crop.

    resize: (width, height) for intermediate resize
    crop: (left, upper, right, lower) applied after resize
    Returns JPEG bytes.
    """
    img = Image.open(BytesIO(raw_bytes)).convert("L")
    img = img.resize(resize, Image.LANCZOS)
    img = img.crop(crop)
    out = BytesIO()
    img.save(out, format="JPEG")
    return out.getvalue()
