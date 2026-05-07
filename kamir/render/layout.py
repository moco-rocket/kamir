from reportlab.lib.units import mm

# Page size
CARD_W = 48 * mm
CARD_H = 67 * mm

# Border
BORDER_MARGIN = 0.5 * mm
BORDER_LINE_WIDTH = 0.5

# Mana cost (top-right)
MANA_COST_X = 47.5 * mm
MANA_COST_Y = 64.3 * mm
MANA_FONT_SIZE = 2.5 * mm

# Card name (top-left)
NAME_X = 0.8 * mm
NAME_Y = 61.8 * mm
NAME_FONT_SIZE = 2.5 * mm

# Artwork image
IMG_X = 1 * mm
IMG_Y = 34 * mm
IMG_W = 46 * mm
IMG_PIXEL_W = 171
IMG_PIXEL_H = 100
IMG_H = IMG_W * IMG_PIXEL_H / IMG_PIXEL_W  # preserves aspect ratio

# Type line
TYPE_X = 0.8 * mm
TYPE_Y = 32 * mm
TYPE_FONT_SIZE = 2.15 * mm
TYPE_MAX_CHARS = 37

# Divider line
DIVIDER_X1 = 1 * mm
DIVIDER_X2 = 47 * mm
DIVIDER_Y = 30.75 * mm

# Oracle text
ORACLE_X = 1 * mm
ORACLE_Y = 29 * mm
ORACLE_BASE_FONT_SIZE = 2.025 * mm
ORACLE_BASE_LEADING = 2 * mm
ORACLE_LINE_THRESHOLD = 14  # lines before font/leading start shrinking
ORACLE_FONT_SHRINK_PER_LINE = 0.035 * mm
ORACLE_LEADING_SHRINK_PER_LINE = 0.09 * mm
ORACLE_CHAR_SPACE = -0.03 * mm

# Expansion code (bottom-left)
EXPANSION_X = 1 * mm
EXPANSION_Y = 1 * mm
EXPANSION_FONT_SIZE = 2 * mm

# Attribution (bottom-left, slightly indented)
ATTRIBUTION_X = 6 * mm
ATTRIBUTION_Y = 1 * mm
ATTRIBUTION_FONT_SIZE = 1.8 * mm
ATTRIBUTION_TEXT = "#ProjectKamir"

# Power/Toughness (bottom-right)
PT_X = 46.5 * mm
PT_Y = 2 * mm
PT_FONT_SIZE = 2.5 * mm
