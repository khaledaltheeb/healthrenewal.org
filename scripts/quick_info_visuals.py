#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1280
HEIGHT = 720

INK = "#071d33"
MUTED = "#64727f"
TEAL = "#0f8c88"
TEAL_LIGHT = "#d6e9e8"
SURFACE = "#ffffff"
CANVAS = "#f7fbfb"
LINE = "#dceaea"

REGULAR_FONTS = (
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
)
BOLD_FONTS = (
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates: Iterable[str] = BOLD_FONTS if bold else REGULAR_FONTS
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size, layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                try:
                    return ImageFont.truetype(candidate, size=size)
                except Exception:
                    continue
    return ImageFont.load_default()


def _rtl_kwargs() -> dict[str, str]:
    return {"direction": "rtl", "language": "ar"}


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    try:
        box = draw.textbbox((0, 0), text, font=font, **_rtl_kwargs())
    except Exception:
        box = draw.textbbox((0, 0), text, font=font)
    return float(box[2] - box[0])


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: str,
    anchor: str = "ra",
) -> None:
    try:
        draw.text(xy, text, font=font, fill=fill, anchor=anchor, **_rtl_kwargs())
    except Exception:
        draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str]:
    words = " ".join((text or "").split()).split(" ")
    words = [word for word in words if word]
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _measure(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        consumed = sum(len(line.split()) for line in lines)
        if consumed < len(words):
            last = lines[-1]
            while last and _measure(draw, last + "…", font) > max_width:
                parts = last.split()
                if len(parts) <= 1:
                    break
                last = " ".join(parts[:-1])
            lines[-1] = last.rstrip("،؛. ") + "…"
    return lines


def quick_info_alt(topic: dict | None, category_label: str | None = None) -> str:
    if not topic:
        return "بطاقة الغلاف لقسم معلومات سريعة في منصة روافد"
    title = " ".join(str(topic.get("title", "")).split())
    category = " ".join(str(category_label or "معلومات سريعة").split())
    return f"بطاقة معلومات سريعة من منصة روافد بعنوان «{title}» ضمن تصنيف {category}"


def make_quick_info_image(
    path: Path,
    topic: dict | None = None,
    *,
    category_label: str | None = None,
    format_label: str | None = None,
    summary_text: str | None = None,
) -> None:
    """Generate the approved text-first Quick Info card.

    Deliberately contains no expressive illustration, emoji, moon, heart, phone,
    person, or topic pictogram. Brand geometry is limited to the four-square
    Rawafid mark and is not topic-dependent.
    """
    im = Image.new("RGB", (WIDTH, HEIGHT), CANVAS)
    draw = ImageDraw.Draw(im)

    # Main card.
    draw.rounded_rectangle((28, 28, 1252, 692), radius=34, fill=SURFACE, outline=LINE, width=2)

    # Small Rawafid brand mark: identity only, never a topic illustration.
    square = 22
    gap = 7
    mark_x = 1200
    mark_y = 64
    for row in range(2):
        for col in range(2):
            x0 = mark_x - col * (square + gap)
            y0 = mark_y + row * (square + gap)
            draw.rounded_rectangle((x0 - square, y0, x0, y0 + square), radius=7, fill=TEAL)

    brand_font = _font(38, bold=True)
    subtitle_font = _font(20)
    _draw_text(draw, (1148, 71), "منصة روافد", font=brand_font, fill=INK)
    _draw_text(draw, (1148, 117), "معرفة عربية موثوقة", font=subtitle_font, fill=MUTED)

    badge_font = _font(21, bold=True)
    draw.rounded_rectangle((65, 60, 285, 112), radius=16, fill=SURFACE, outline=TEAL, width=2)
    _draw_text(draw, (260, 87), "معلومات سريعة", font=badge_font, fill=TEAL, anchor="rm")

    if topic:
        category = category_label or "معلومات سريعة"
        category_font = _font(19, bold=True)
        cat_w = min(260, max(155, int(_measure(draw, category, category_font) + 46)))
        draw.rounded_rectangle((65, 126, 65 + cat_w, 174), radius=15, fill="#f8fcfc", outline=TEAL_LIGHT, width=2)
        _draw_text(draw, (65 + cat_w - 22, 150), category, font=category_font, fill=TEAL, anchor="rm")

    draw.line((65, 198, 1215, 198), fill=LINE, width=2)

    if topic:
        title = " ".join(str(topic.get("title", "")).split())
        summary = " ".join(str(summary_text or "").split())
        title_font = _font(54, bold=True)
        title_lines = _wrap(draw, title, title_font, 1080, 2)
        title_line_h = 76
        title_y = 286 if len(title_lines) == 1 else 254
        for i, line in enumerate(title_lines):
            _draw_text(draw, (640, title_y + i * title_line_h), line, font=title_font, fill=INK, anchor="mm")

        if summary:
            summary_font = _font(25)
            summary_lines = _wrap(draw, summary, summary_font, 1010, 3)
            summary_y = title_y + len(title_lines) * title_line_h + 45
            for i, line in enumerate(summary_lines):
                _draw_text(draw, (640, summary_y + i * 40), line, font=summary_font, fill=MUTED, anchor="mm")

        cta_font = _font(25, bold=True)
        _draw_text(draw, (1165, 635), "قراءة الصفحة ←", font=cta_font, fill=TEAL)
    else:
        title_font = _font(68, bold=True)
        _draw_text(draw, (640, 320), "معلومات سريعة", font=title_font, fill=INK, anchor="mm")
        lead_font = _font(27)
        cover_summary = summary_text or "مقارنات واضحة، فحوص تثقيفية، أسباب محتملة وخطوات عملية بلغة عربية موثوقة."
        for i, line in enumerate(_wrap(draw, cover_summary, lead_font, 980, 3)):
            _draw_text(draw, (640, 415 + i * 44), line, font=lead_font, fill=MUTED, anchor="mm")
        cta_font = _font(25, bold=True)
        _draw_text(draw, (1165, 635), "استكشف الصفحات ←", font=cta_font, fill=TEAL)

    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True)
