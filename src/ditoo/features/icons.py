"""Game icon search, download, and Divoom format conversion.

Uses game-icons.net (3600+ free game icons by Lorc, Delapouite, et al).
Downloads white-on-black PNGs and recolors client-side.
"""

import math
import re
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from ditoo.logging_setup import get_logger

logger = get_logger(__name__)

# Sitemap authors
_AUTHORS = [
    "cathelineau", "delapouite", "felbrigg",
    "john-colburn", "lorc", "skoll",
]

INDEX_CACHE = Path("/tmp/ditoo_game_icons_index.txt")

# Color presets: (fg_hex, bg_hex, label)
COLOR_PRESETS = [
    ("50fa7b", "0a0a1a", "Green"),
    ("e94560", "0a0a1a", "Red"),
    ("00d2ff", "0a0a1a", "Cyan"),
    ("ff79c6", "0a0a1a", "Pink"),
    ("ffffff", "000000", "White"),
    ("f1fa8c", "0a0a1a", "Yellow"),
]


def load_or_build_index() -> list[str]:
    """Load icon index from cache or build from sitemaps.

    Returns list of 'author/icon-name' strings.
    """
    if INDEX_CACHE.exists():
        lines = INDEX_CACHE.read_text().strip().split("\n")
        if lines and lines[0]:
            return lines

    logger.info("Building icon index from game-icons.net...")
    icons: list[str] = []
    with httpx.Client(timeout=15.0, follow_redirects=True) as c:
        for author in _AUTHORS:
            url = f"https://game-icons.net/sitemaps/1x1/{author}.xml"
            resp = c.get(url)
            matches = re.findall(
                r"<loc>https://game-icons\.net/1x1/([^/]+)/([^<]+)\.html</loc>",
                resp.text,
            )
            for a, name in matches:
                icons.append(f"{a}/{name}")

    INDEX_CACHE.write_text("\n".join(icons))
    logger.info(f"Indexed {len(icons)} icons")
    return icons


def search_icons(icons: list[str], query: str) -> list[str]:
    """Search icon names by keyword. Returns matching 'author/name' strings."""
    terms = query.lower().split()
    scored: list[tuple[int, str]] = []
    for icon in icons:
        name = icon.split("/")[1]
        if all(t in name for t in terms):
            scored.append((0, icon))
        elif any(t in name for t in terms):
            scored.append((1, icon))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [s[1] for s in scored]


def download_icon(author: str, name: str,
                  fg: str = "50fa7b", bg: str = "0a0a1a") -> Image.Image:
    """Download a game-icons.net icon and recolor.

    Downloads white-on-black PNG, then blends to requested fg/bg colors.
    """
    url = f"https://game-icons.net/icons/ffffff/000000/1x1/{author}/{name}.png"
    logger.info(f"Downloading {author}/{name}")
    with httpx.Client(timeout=10.0, follow_redirects=True) as c:
        resp = c.get(url)
        resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert("RGB")

    fg_rgb = tuple(int(fg[i:i + 2], 16) for i in (0, 2, 4))
    bg_rgb = tuple(int(bg[i:i + 2], 16) for i in (0, 2, 4))

    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pixels[x, y]
            t = (r + g + b) / (3 * 255)
            pixels[x, y] = (
                int(bg_rgb[0] + t * (fg_rgb[0] - bg_rgb[0])),
                int(bg_rgb[1] + t * (fg_rgb[1] - bg_rgb[1])),
                int(bg_rgb[2] + t * (fg_rgb[2] - bg_rgb[2])),
            )
    return img


def image_to_divoom_frame(img: Image.Image, max_colors: int = 64) -> bytes:
    """Convert a PIL Image to a Divoom static frame.

    Returns raw frame bytes starting with 0xAA marker.
    """
    img = img.convert("RGB").resize((16, 16), Image.LANCZOS)

    quantized = img.quantize(
        colors=min(max_colors, 256), method=Image.MEDIANCUT
    )
    palette_data = quantized.getpalette()
    pixels_raw = list(quantized.getdata())

    used_indices = sorted(set(pixels_raw))
    color_map = {old: new for new, old in enumerate(used_indices)}
    palette_bytes = bytearray()
    for old_idx in used_indices:
        palette_bytes.extend([
            palette_data[old_idx * 3],
            palette_data[old_idx * 3 + 1],
            palette_data[old_idx * 3 + 2],
        ])

    num_colors = len(used_indices)
    remapped = [color_map[p] for p in pixels_raw]

    bpp = max(1, math.ceil(math.log2(num_colors))) if num_colors > 1 else 1
    bit_buffer = 0
    bit_count = 0
    pixel_bytes = bytearray()
    for px in remapped:
        bit_buffer |= (px & ((1 << bpp) - 1)) << bit_count
        bit_count += bpp
        while bit_count >= 8:
            pixel_bytes.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bit_count -= 8
    if bit_count > 0:
        pixel_bytes.append(bit_buffer & 0xFF)

    nc_byte = 0 if num_colors == 256 else num_colors
    frame_len = 7 + len(palette_bytes) + len(pixel_bytes)

    return bytes([
        0xAA,
        frame_len & 0xFF, (frame_len >> 8) & 0xFF,
        0x00, 0x00,  # duration (static)
        0x00,        # reset palette
        nc_byte,
    ]) + bytes(palette_bytes) + bytes(pixel_bytes)


def render_ascii_preview(img: Image.Image, width: int = 16) -> list[str]:
    """Render a 16x16 ASCII art preview of the image."""
    small = img.convert("L").resize((width, width), Image.LANCZOS)
    pixels = list(small.getdata())
    chars = " .:-=+*#%@"
    lines = []
    for row in range(width):
        line = ""
        for col in range(width):
            v = pixels[row * width + col]
            idx = min(len(chars) - 1, v * len(chars) // 256)
            line += chars[idx] * 2
        lines.append(line)
    return lines
