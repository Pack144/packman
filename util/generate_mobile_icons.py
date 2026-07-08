"""
One-off generator for placeholder Pack Directory PWA icons.

Run with: uv run python util/generate_mobile_icons.py

Produces simple placeholder artwork in the Campfire Hub palette. Replace the
output files in packman/mobile/static/mobile/icons/ with real pack branding
whenever it's available.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = "#2c2c2c"
CREAM = "#efece6"
BLUE = "#2f6690"

OUT_DIR = Path(__file__).resolve().parent.parent / "packman" / "mobile" / "static" / "mobile" / "icons"


def draw_badge(size, padding_ratio=0.0, background=BLUE, foreground=CREAM):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    padding = int(size * padding_ratio)
    draw.ellipse([padding, padding, size - padding, size - padding], fill=background)

    label = "P"
    font = ImageFont.load_default(size=int(size * 0.5))
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - text_w) / 2 - bbox[0], (size - text_h) / 2 - bbox[1]),
        label,
        font=font,
        fill=foreground,
    )
    return image


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    draw_badge(192).save(OUT_DIR / "icon-192.png")
    draw_badge(512).save(OUT_DIR / "icon-512.png")
    # Maskable icons need generous padding so the badge survives platform cropping.
    draw_badge(512, padding_ratio=0.15).save(OUT_DIR / "icon-maskable-512.png")

    # iOS ignores transparency on apple-touch-icon; flatten onto the cream background.
    apple_icon = Image.new("RGB", (180, 180), CREAM)
    apple_icon.paste(draw_badge(180), (0, 0), draw_badge(180))
    apple_icon.save(OUT_DIR / "apple-touch-icon.png")

    print(f"Wrote icons to {OUT_DIR}")


if __name__ == "__main__":
    main()
