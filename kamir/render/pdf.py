import logging
from io import BytesIO
from pathlib import Path

from PIL import Image
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from kamir.filter.cards import wrap_oracle
from kamir.render import layout as L

log = logging.getLogger(__name__)


def _type_font_size(type_line: str) -> float:
    if len(type_line) > L.TYPE_MAX_CHARS:
        return (77.4 / len(type_line)) * mm
    return L.TYPE_FONT_SIZE


def _oracle_font_size(line_count: int) -> float:
    if line_count < L.ORACLE_LINE_THRESHOLD:
        return L.ORACLE_BASE_FONT_SIZE
    return L.ORACLE_BASE_FONT_SIZE - L.ORACLE_FONT_SHRINK_PER_LINE * (line_count - L.ORACLE_LINE_THRESHOLD + 1)


def _oracle_leading(line_count: int) -> float:
    if line_count < L.ORACLE_LINE_THRESHOLD:
        return L.ORACLE_BASE_LEADING
    return L.ORACLE_BASE_LEADING - L.ORACLE_LEADING_SHRINK_PER_LINE * (line_count - L.ORACLE_LINE_THRESHOLD + 1)


def render_card_pdf(card: dict, img_path: Path) -> bytes:
    """Render a single card to PDF bytes."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(L.CARD_W, L.CARD_H))

    # Border
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(L.BORDER_LINE_WIDTH)
    c.rect(L.BORDER_MARGIN, L.BORDER_MARGIN, L.CARD_W - 2 * L.BORDER_MARGIN, L.CARD_H - 2 * L.BORDER_MARGIN)

    # Mana cost
    c.setFont("Courier", L.MANA_FONT_SIZE)
    c.drawRightString(L.MANA_COST_X, L.MANA_COST_Y, card.get("mana_cost") or "")

    # Card name
    c.setFont("Courier", L.NAME_FONT_SIZE)
    c.drawString(L.NAME_X, L.NAME_Y, card["name"])

    # Artwork
    img = Image.open(img_path)
    c.drawInlineImage(img, L.IMG_X, L.IMG_Y, width=L.IMG_W, height=L.IMG_H)

    # Type line
    type_line = card.get("type") or ""
    c.setFont("Courier", _type_font_size(type_line))
    c.drawString(L.TYPE_X, L.TYPE_Y, type_line)

    # Divider
    c.line(L.DIVIDER_X1, L.DIVIDER_Y, L.DIVIDER_X2, L.DIVIDER_Y)

    # Oracle text
    oracle = wrap_oracle(card.get("oracle") or "")
    line_count = oracle.count("\n") + 1 if oracle else 0
    c.setFont("Courier", _oracle_font_size(line_count))
    txt = c.beginText(L.ORACLE_X, L.ORACLE_Y)
    txt.setLeading(_oracle_leading(line_count))
    txt.setCharSpace(L.ORACLE_CHAR_SPACE)
    txt.textLines(oracle)
    c.drawText(txt)

    # Expansion code
    c.setFont("Courier", L.EXPANSION_FONT_SIZE)
    c.drawString(L.EXPANSION_X, L.EXPANSION_Y, card.get("expansion") or "")

    # Attribution
    c.setFont("Courier", L.ATTRIBUTION_FONT_SIZE)
    c.drawString(L.ATTRIBUTION_X, L.ATTRIBUTION_Y, L.ATTRIBUTION_TEXT)

    # Power/Toughness
    power = card.get("power") or ""
    toughness = card.get("toughness") or ""
    c.setFont("Courier-Bold", L.PT_FONT_SIZE)
    c.drawRightString(L.PT_X, L.PT_Y, f"{power}/{toughness}")

    c.save()
    return buf.getvalue()


def write_card_pdf(card: dict, img_path: Path, pdf_dir: Path) -> Path:
    """Render card to PDF and write to disk. Returns the written path."""
    mv = str(card["mana_value"])
    safe_name = card["name"].replace("/", "-")
    dest = pdf_dir / mv / f"{safe_name}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)

    pdf_bytes = render_card_pdf(card, img_path)
    dest.write_bytes(pdf_bytes)
    log.info("Saved PDF: %s", dest)
    return dest
