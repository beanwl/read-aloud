#!/usr/bin/env python3
"""Generate Chrome Web Store listing assets for Speak Selection."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent / "listing-assets"
ICON_PATH = ASSETS_DIR / "store-icon-128.png"

# Brand colors (sampled from existing assets)
PURPLE_SOLID = (88, 40, 140)
PURPLE_DARK = (40, 20, 70)
PURPLE_LIGHT = (84, 20, 139)
WHITE = (255, 255, 255)
GRAY_SUBTITLE = (180, 185, 195)
CHROME_BAR = (32, 33, 36)
PAGE_BG = (245, 247, 250)
TEXT_DARK = (20, 30, 40)
TEXT_MUTED = (90, 97, 105)
HIGHLIGHT_BG = (180, 210, 255)
HIGHLIGHT_TEXT = (20, 40, 80)
BTN_SPEAK = (31, 111, 235)
BTN_STOP_BG = (235, 237, 240)
BTN_STOP_TEXT = (60, 70, 80)
PANEL_BORDER = (203, 207, 211)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


def gradient_bg(width: int, height: int, left: tuple, right: tuple) -> Image.Image:
    img = Image.new("RGB", (width, height))
    px = img.load()
    for x in range(width):
        t = x / max(width - 1, 1)
        color = tuple(int(left[i] + (right[i] - left[i]) * t) for i in range(3))
        for y in range(height):
            px[x, y] = color
    return img


def solid_bg(width: int, height: int, color: tuple) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def load_icon(size: int) -> Image.Image:
    icon = Image.open(ICON_PATH).convert("RGB")
    return icon.resize((size, size), Image.Resampling.LANCZOS)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    width: int,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple,
) -> int:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (width - tw) // 2
    draw.text((x, y), text, font=fnt, fill=fill)
    return th


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple,
    outline: tuple | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def generate_small_promo() -> Path:
    w, h = 440, 280
    img = solid_bg(w, h, PURPLE_SOLID)
    icon = load_icon(90)
    img.paste(icon, ((w - 90) // 2, 30))
    draw = ImageDraw.Draw(img)
    title_y = 140
    draw_centered_text(draw, "Speak Selection", title_y, w, font(32, bold=True), WHITE)
    draw_centered_text(
        draw, "Right-click text to hear it", title_y + 48, w, font(18), WHITE
    )
    out = ASSETS_DIR / "small-promo-440x280.png"
    img.save(out, "PNG")
    return out


def generate_marquee() -> Path:
    w, h = 1400, 560
    img = gradient_bg(w, h, PURPLE_DARK, PURPLE_LIGHT)
    icon = load_icon(200)
    img.paste(icon, (80, (h - 200) // 2))
    draw = ImageDraw.Draw(img)
    x = 320
    draw.text((x, 150), "Speak Selection", font=font(72, bold=True), fill=WHITE)
    draw.text(
        (x, 250),
        "Highlight text → right-click → hear it spoken",
        font=font(32, bold=True),
        fill=WHITE,
    )
    draw.text(
        (x, 320),
        "Voice • Speed • Pitch • Volume",
        font=font(28),
        fill=GRAY_SUBTITLE,
    )
    out = ASSETS_DIR / "marquee-1400x560.png"
    img.save(out, "PNG")
    return out


def generate_screenshot(width: int, height: int, filename: str) -> Path:
    scale = width / 1280
    img = Image.new("RGB", (width, height), PAGE_BG)
    draw = ImageDraw.Draw(img)

    bar_h = int(36 * scale)
    draw.rectangle((0, 0, width, bar_h), fill=CHROME_BAR)
    draw.text(
        (int(16 * scale), int(8 * scale)),
        "apnews.com — sample article",
        font=font(max(int(14 * scale), 9)),
        fill=(200, 205, 210),
    )

    margin = int(80 * scale)
    title_size = max(int(42 * scale), 18)
    body_size = max(int(20 * scale), 10)
    panel_w = int(280 * scale)
    panel_h = int(340 * scale)
    panel_x = width - panel_w - int(60 * scale)
    panel_y = int(100 * scale)
    radius = max(int(12 * scale), 4)

    draw.text(
        (margin, int(90 * scale)),
        "Speak Selection demo",
        font=font(title_size, bold=True),
        fill=TEXT_DARK,
    )

    lines = [
        "Highlight any paragraph on a webpage, right-click, and choose Speak Selection.",
        "A small side panel lets you pick voice, speed, pitch, and volume.",
        "Works in Chrome and Edge using built-in browser speech.",
    ]
    y = int(170 * scale)
    line_h = int(34 * scale)
    for line in lines:
        draw.text((margin, y), line, font=font(body_size), fill=TEXT_MUTED)
        y += line_h

    hl_y = int(290 * scale)
    hl_h = int(44 * scale)
    hl_text = "Selected text is spoken aloud..."
    hl_font = font(body_size, bold=True)
    hl_bbox = draw.textbbox((0, 0), hl_text, font=hl_font)
    hl_tw = hl_bbox[2] - hl_bbox[0]
    hl_pad = int(10 * scale)
    draw.rounded_rectangle(
        (margin - hl_pad, hl_y - int(4 * scale), margin + hl_tw + hl_pad, hl_y + hl_h),
        radius=max(int(6 * scale), 2),
        fill=HIGHLIGHT_BG,
    )
    draw.text((margin, hl_y), hl_text, font=hl_font, fill=HIGHLIGHT_TEXT)

    rounded_rect(
        draw,
        (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h),
        radius,
        WHITE,
        PANEL_BORDER,
        max(int(2 * scale), 1),
    )

    px = panel_x + int(20 * scale)
    py = panel_y + int(20 * scale)
    panel_title_size = max(int(22 * scale), 11)
    setting_size = max(int(18 * scale), 9)
    draw.text((px, py), "Speak Selection", font=font(panel_title_size, bold=True), fill=TEXT_DARK)
    py += int(40 * scale)
    for setting in [
        "Voice: English (US)",
        "Speed: 1.5x",
        "Pitch: 1x",
        "Volume: 1x",
    ]:
        draw.text((px, py), setting, font=font(setting_size), fill=TEXT_MUTED)
        py += int(32 * scale)

    btn_h = int(36 * scale)
    btn_w = int(110 * scale)
    btn_y = panel_y + panel_h - btn_h - int(24 * scale)
    btn_radius = max(int(8 * scale), 3)
    speak_x = px
    stop_x = speak_x + btn_w + int(12 * scale)
    draw.rounded_rectangle(
        (speak_x, btn_y, speak_x + btn_w, btn_y + btn_h),
        radius=btn_radius,
        fill=BTN_SPEAK,
    )
    draw.text(
        (speak_x + int(28 * scale), btn_y + int(8 * scale)),
        "Speak",
        font=font(setting_size, bold=True),
        fill=WHITE,
    )
    draw.rounded_rectangle(
        (stop_x, btn_y, stop_x + btn_w, btn_y + btn_h),
        radius=btn_radius,
        fill=BTN_STOP_BG,
        outline=PANEL_BORDER,
        width=max(int(1 * scale), 1),
    )
    draw.text(
        (stop_x + int(32 * scale), btn_y + int(8 * scale)),
        "Stop",
        font=font(setting_size, bold=True),
        fill=BTN_STOP_TEXT,
    )

    out = ASSETS_DIR / filename
    img.save(out, "PNG")
    return out


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        generate_small_promo(),
        generate_marquee(),
        generate_screenshot(1280, 800, "screenshot-1280x800.png"),
        generate_screenshot(640, 400, "screenshot-640x400.png"),
    ]
    for path in outputs:
        img = Image.open(path)
        assert img.mode == "RGB", f"{path.name} must be RGB (no alpha)"
        print(f"Wrote {path} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
