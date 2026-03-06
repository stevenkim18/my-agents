#!/usr/bin/env python3
"""
base 이미지에 언어별 텍스트를 오버레이합니다.
동일한 base 이미지에서 KO/EN 버전을 생성할 때 사용합니다.
KO와 EN은 반드시 동일한 base에서 생성되어야 합니다.
"""

import argparse
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_PATHS_KO = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/NanumGothicBold.ttf",
]

FONT_PATHS_EN = [
    "/System/Library/Fonts/SFNSDisplay.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Arial.ttf",
]


def load_font(size: int, korean: bool = True) -> ImageFont.FreeTypeFont:
    paths = FONT_PATHS_KO if korean else FONT_PATHS_EN
    for path in paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    if korean:
        return load_font(size, korean=False)
    return ImageFont.load_default()


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: tuple,
    font: ImageFont.FreeTypeFont,
    fill_color: tuple,
    shadow_offset: int = 3,
    shadow_alpha: int = 100,
):
    x, y = pos
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, shadow_alpha))
    draw.text((x, y), text, font=font, fill=fill_color)


def add_text_overlay(
    image: Image.Image,
    headline: str | None,
    subheadline: str | None,
    text_position: str,
    text_color: str,
    lang: str = "ko",
) -> Image.Image:
    """
    이미지에 텍스트를 오버레이합니다.
    - headline: 큰 텍스트 (한 줄 또는 두 줄)
    - subheadline: 작은 텍스트 (설명)
    - text_position: 'top' 또는 'bottom'
    - lang: 'ko' (한국어) 또는 'en' (영어)
    """
    img = image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img.size
    fill = hex_to_rgba(text_color)
    is_korean = (lang == "ko")

    # 폰트 크기: 캔버스 너비 기준
    headline_size = max(60, int(w * 0.065))    # ~84px for 1290w
    sub_size = max(36, int(w * 0.038))          # ~49px

    headline_font = load_font(headline_size, korean=is_korean)
    sub_font = load_font(sub_size, korean=is_korean)

    # 텍스트 시작 Y 위치
    if text_position == "top":
        y_cursor = int(h * 0.055)
    else:
        y_cursor = int(h * 0.78)

    line_gap_h = int(headline_size * 1.35)
    line_gap_s = int(sub_size * 1.4)
    section_gap = int(sub_size * 0.7)

    # 헤드라인
    if headline:
        # 픽셀 기반으로 최대 너비 계산 (더 정확한 줄바꿈)
        max_line_px = int(w * 0.82)
        words = headline.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=headline_font)
            if bbox[2] - bbox[0] <= max_line_px:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=headline_font)
            tw = bbox[2] - bbox[0]
            x = (w - tw) // 2
            draw_text_with_shadow(draw, line, (x, y_cursor), headline_font, fill)
            y_cursor += line_gap_h
        y_cursor += section_gap

    # 서브헤드라인
    if subheadline:
        max_line_px_s = int(w * 0.78)
        words_s = subheadline.split()
        lines = []
        current = ""
        for word in words_s:
            test = (current + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=sub_font)
            if bbox[2] - bbox[0] <= max_line_px_s:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=sub_font)
            tw = bbox[2] - bbox[0]
            x = (w - tw) // 2
            draw_text_with_shadow(draw, line, (x, y_cursor), sub_font, fill, shadow_offset=2, shadow_alpha=80)
            y_cursor += line_gap_s

    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description="base 이미지에 언어별 텍스트 오버레이")
    parser.add_argument("--base", required=True, help="텍스트 없는 base 이미지 경로")
    parser.add_argument("--output", required=True, help="출력 경로")
    parser.add_argument("--lang", required=True, choices=["ko", "en"], help="언어")
    parser.add_argument("--headline", default=None, help="헤드라인 텍스트")
    parser.add_argument("--subheadline", default=None, help="서브헤드라인 텍스트")
    parser.add_argument("--text-position", default="top", choices=["top", "bottom"])
    parser.add_argument("--text-color", default="#FFFFFF", help="텍스트 색상 HEX")
    args = parser.parse_args()

    base_path = Path(args.base)
    if not base_path.exists():
        print(f"ERROR: base 이미지 없음: {args.base}", file=sys.stderr)
        sys.exit(1)

    if not args.headline and not args.subheadline:
        print("ERROR: --headline 또는 --subheadline 중 하나는 필요합니다", file=sys.stderr)
        sys.exit(1)

    print(f"base 로드: {args.base}")
    base = Image.open(base_path)

    print(f"텍스트 오버레이 [{args.lang.upper()}]: '{args.headline}' / '{args.subheadline}'")
    result = add_text_overlay(
        base,
        headline=args.headline,
        subheadline=args.subheadline,
        text_position=args.text_position,
        text_color=args.text_color,
        lang=args.lang,
    )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, "PNG", optimize=True)
    print(f"저장 완료: {args.output}")


if __name__ == "__main__":
    main()
