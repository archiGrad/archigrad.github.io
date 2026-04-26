import re
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

ENGLISH_FONT_INDEX = {
    "1": "BitcountGridDouble-Regular.ttf",
    "2": "VT323-Regular.ttf",
    "3": "DMMono-Regular.ttf",
    "4": "Lacquer-Regular.ttf",
    "5": "NotoSans-Regular.ttf",
    "6": "UbuntuMono-Regular.ttf",
}

DEFAULT_FONT = "PixelifySans-Regular.ttf"

_TAG_SPLIT_RE = re.compile(r"(?<!')(\[\d+\])(?!')")
_TAG_MATCH_RE = re.compile(r'^\[(\d+)\]$')
_TAG_UNESCAPE_RE = re.compile(r"'(\[\d+\])'")
_WORD_RE = re.compile(r'\S+|\s+')


@lru_cache(maxsize=128)
def get_font(f_name, size):
    if not f_name:
        return load_custom_font(size)
    p = Path(f"fonts/{f_name}")
    if p.exists():
        try:
            return ImageFont.truetype(str(p), int(size))
        except IOError:
            print(f"Warning: Found {p} but could not load it.")
            return load_custom_font(size)
    print(f"Warning: Font '{f_name}' not found, using fallback.")
    return load_custom_font(size)


def load_custom_font(size):
    fallbacks = ['UbuntuMono-Regular.ttf', 'DejaVuSansMono.ttf', 'Consolas.ttf', 'arial.ttf']
    for f in fallbacks:
        try:
            return ImageFont.truetype(f, int(size))
        except IOError:
            continue
    try:
        return ImageFont.load_default(size=int(size))
    except TypeError:
        return ImageFont.load_default()


def get_special_alphabet_font(char):
    c = ord(char)
    if 0x0600 <= c <= 0x06FF: return 'NotoSansArabic-Regular.ttf'
    if 0x0E00 <= c <= 0x0E7F: return 'NotoSansThai-Regular.ttf'
    if 0x0B80 <= c <= 0x0BFF: return 'NotoSansTamil-Regular.ttf'
    if 0x0980 <= c <= 0x09FF: return 'NotoSansBengali-Regular.ttf'
    if 0xAC00 <= c <= 0xD7AF or 0x1100 <= c <= 0x11FF or 0x3130 <= c <= 0x318F:
        return 'NotoSansKR-Regular.ttf'
    return None


def _measure(font, text):
    try:
        left, top, right, bottom = font.getbbox(text)
        return right - left, bottom - top
    except AttributeError:
        return font.getsize(text)


def draw_wrapped_line(text, y, sz, draw, color, max_width, padding_left):
    if not text:
        return 0
    cx, cy = padding_left, y
    mx_h_in_line = 0
    line_spacing = int(sz * 0.15)
    parts = _TAG_SPLIT_RE.split(text)
    active_english_f = DEFAULT_FONT
    for part in parts:
        tag_match = _TAG_MATCH_RE.match(part)
        if tag_match:
            active_english_f = ENGLISH_FONT_INDEX.get(tag_match.group(1), active_english_f)
            continue
        if not part:
            continue
        part = _TAG_UNESCAPE_RE.sub(r"\1", part)
        words = _WORD_RE.findall(part)
        for word in words:
            stripped = word.strip()
            special_f = get_special_alphabet_font(stripped[0]) if stripped else None
            f_file = special_f if special_f else active_english_f
            font = get_font(f_file, sz)
            w, h = _measure(font, word)
            if cx + w > max_width and stripped:
                cx = padding_left
                cy += mx_h_in_line + line_spacing
                mx_h_in_line = 0
            draw.text((cx, cy), word, fill=color, font=font)
            cx += w
            mx_h_in_line = max(mx_h_in_line, h)
    return (cy + mx_h_in_line) - y


def create_label_image(title, body_lines, color, output_path, img_resolution, font_size):
    try:
        img = Image.new('RGBA', (img_resolution, img_resolution), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        padding_top = 1
        padding_left = 1
        max_w = img_resolution - padding_left
        title_body_gap = int(2 * (img_resolution / 64.0)) if (title and body_lines) else 0
        cur_y = padding_top
        if title:
            h = draw_wrapped_line(title, cur_y, int(font_size * 1.5), draw, color, max_w, padding_left)
            cur_y += h + title_body_gap
        for line in body_lines:
            h = draw_wrapped_line(line, cur_y, int(font_size), draw, color, max_w, padding_left)
            cur_y += h
        img.save(output_path)
        return True
    except Exception as e:
        print(f"Error creating label {output_path}: {e}")
        return False


def is_label_image(filename):
    return (filename.startswith('ZZ_') and filename.endswith('_top.png')) or \
           (filename.startswith('AA_') and filename.endswith('_bottom.png'))