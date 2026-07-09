"""
One-off generator for placeholder Pack Directory PWA icons.

Run with: uv run python util/generate_mobile_icons.py [label]

Draws the Pack 144-style red badge (rounded red square, white numerals) used
by the mobile app's brand. Pass a different label (e.g. your pack number) as
the first argument. Replace the output files in
packman/mobile/static/mobile/icons/ with real pack branding when available.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RED = "#d21e2b"
RED_BORDER = "#f4b6bb"
BG = "#f4f6f9"

OUT_DIR = Path(__file__).resolve().parent.parent / "packman" / "mobile" / "static" / "mobile" / "icons"


def draw_badge(size, label, padding_ratio=0.0):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    padding = int(size * padding_ratio)
    radius = int((size - 2 * padding) * 0.18)
    border = max(2, size // 48)
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=RED,
        outline=RED_BORDER,
        width=border,
    )

    font = ImageFont.load_default(size=int((size - 2 * padding) * (0.52 if len(label) <= 2 else 0.34)))
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - text_w) / 2 - bbox[0], (size - text_h) / 2 - bbox[1]),
        label,
        font=font,
        fill="#ffffff",
    )
    return image


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "144"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    draw_badge(192, label).save(OUT_DIR / "icon-192.png")
    draw_badge(512, label).save(OUT_DIR / "icon-512.png")
    # Maskable icons need generous padding so the badge survives platform cropping.
    draw_badge(512, label, padding_ratio=0.15).save(OUT_DIR / "icon-maskable-512.png")

    # iOS ignores transparency on apple-touch-icon; flatten onto the app background.
    badge = draw_badge(180, label)
    apple_icon = Image.new("RGB", (180, 180), BG)
    apple_icon.paste(badge, (0, 0), badge)
    apple_icon.save(OUT_DIR / "apple-touch-icon.png")

    print(f"Wrote '{label}' icons to {OUT_DIR}")


if __name__ == "__main__":
    main()
