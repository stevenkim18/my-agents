#!/usr/bin/env python3
"""
App Store 마케팅 이미지 생성기 (로컬 합성 버전)
iPhone 17 Pro 프레임에 스크린샷을 끼워 넣고 헤드라인 텍스트를 추가합니다.
Gemini 없이 100% Pillow로 실행.

사용법:
  python3 create_mockup_image.py \
    --screenshot path/to/screenshot.png \
    --output path/to/output.png \
    --headline "말씀, 한눈에" \
    --subline "장·절 단위로 차분하게 읽다" \
    --bg-from "#6B4FC8" \
    --bg-to "#A78BF5" \
    --text-position top \
    --device iphone_67
"""

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 캔버스 크기 ──────────────────────────────────────────────────────────────
CANVAS_SIZES = {
    "iphone_67": (1290, 2796),
    "iphone_69": (1320, 2868),
    "ipad_129":  (2048, 2732),
}

# ── iPhone 17 Pro 프레임 파라미터 (스크린 기준 비율) ─────────────────────────
FRAME = {
    "bezel_side":   0.038,   # 스크린 너비 대비 측면 베젤
    "bezel_top":    0.038,   # 스크린 너비 대비 상단 베젤
    "bezel_bottom": 0.042,   # 스크린 너비 대비 하단 베젤
    "corner_r":     0.095,   # 프레임 너비 대비 모서리 반경
    "di_w":         0.310,   # Dynamic Island 너비 (스크린 너비 대비)
    "di_h":         0.022,   # Dynamic Island 높이 (스크린 너비 대비)
    "di_top":       0.015,   # Dynamic Island 상단 여백 (스크린 너비 대비)
}


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_gradient(size: tuple, color_from: str, color_to: str) -> Image.Image:
    """수직 선형 그라디언트 배경 생성"""
    w, h = size
    c1 = hex_to_rgb(color_from)
    c2 = hex_to_rgb(color_to)
    img = Image.new("RGB", (w, h))
    for y in range(h):
        t = y / (h - 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        # 한 줄씩 채우기 (효율적)
        row = Image.new("RGB", (w, 1), (r, g, b))
        img.paste(row, (0, y))
    return img


def draw_iphone_frame(screen: Image.Image, scale: float) -> Image.Image:
    """
    스크린샷을 iPhone 17 Pro 프레임에 합성합니다.
    Returns: RGBA 이미지 (프레임 포함)
    """
    sw, sh = screen.size  # 스케일된 스크린 크기

    bz_s = int(sw * FRAME["bezel_side"])
    bz_t = int(sw * FRAME["bezel_top"])
    bz_b = int(sw * FRAME["bezel_bottom"])

    fw = sw + bz_s * 2
    fh = sh + bz_t + bz_b
    corner_r = int(fw * FRAME["corner_r"])

    # ── 프레임 베이스 (다크 그레이 메탈) ───────────────────────────────────
    frame = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # 외곽 프레임 (메탈 테두리)
    frame_color = (45, 45, 48, 255)
    draw.rounded_rectangle([0, 0, fw - 1, fh - 1], radius=corner_r,
                           fill=frame_color)

    # 내부 스크린 영역 (검정 — 스크린샷으로 덮일 부분)
    inner_r = max(corner_r - bz_s, 4)
    draw.rounded_rectangle(
        [bz_s, bz_t, bz_s + sw - 1, bz_t + sh - 1],
        radius=inner_r,
        fill=(0, 0, 0, 255),
    )

    # ── 스크린샷 합성 ─────────────────────────────────────────────────────
    screen_rgba = screen.convert("RGBA")

    # 스크린 마스크 (둥근 모서리)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, sw - 1, sh - 1], radius=inner_r, fill=255
    )
    frame.paste(screen_rgba, (bz_s, bz_t), mask)

    # ── Dynamic Island ────────────────────────────────────────────────────
    di_w = int(sw * FRAME["di_w"])
    di_h = int(sw * FRAME["di_h"])
    di_top = bz_t + int(sw * FRAME["di_top"])
    di_x = bz_s + (sw - di_w) // 2
    draw.rounded_rectangle(
        [di_x, di_top, di_x + di_w, di_top + di_h],
        radius=di_h // 2,
        fill=(0, 0, 0, 255),
    )

    # ── 하이라이트 (상단 유리 반사) ───────────────────────────────────────
    highlight = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.rounded_rectangle(
        [bz_s // 2, bz_t // 2, fw - bz_s // 2, fh // 3],
        radius=corner_r,
        fill=(255, 255, 255, 18),
    )
    frame = Image.alpha_composite(frame, highlight)

    return frame


def find_font(size: int) -> ImageFont.FreeTypeFont:
    """시스템에서 사용 가능한 폰트를 찾아 반환"""
    candidates = [
        # macOS
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # 공통
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_text_block(
    canvas: Image.Image,
    headline: str,
    subline: str,
    region: tuple,  # (x, y, w, h)
    text_color: str,
    align: str = "center",
):
    """헤드라인 + 서브라인을 region 안에 중앙 배치"""
    rx, ry, rw, rh = region
    draw = ImageDraw.Draw(canvas)
    tc = hex_to_rgb(text_color) + (255,)

    # 헤드라인 크기 자동 조정
    h_size = max(60, rw // 10)
    h_font = find_font(h_size)
    h_bbox = draw.textbbox((0, 0), headline, font=h_font)
    h_w = h_bbox[2] - h_bbox[0]
    while h_w > rw * 0.88 and h_size > 40:
        h_size -= 4
        h_font = find_font(h_size)
        h_bbox = draw.textbbox((0, 0), headline, font=h_font)
        h_w = h_bbox[2] - h_bbox[0]

    # 서브라인 크기
    s_size = max(36, h_size // 2)
    s_font = find_font(s_size)
    s_bbox = draw.textbbox((0, 0), subline, font=s_font)
    s_w = s_bbox[2] - s_bbox[0]
    while s_w > rw * 0.88 and s_size > 24:
        s_size -= 2
        s_font = find_font(s_size)
        s_bbox = draw.textbbox((0, 0), subline, font=s_font)
        s_w = s_bbox[2] - s_bbox[0]

    gap = h_size // 3
    total_h = (h_bbox[3] - h_bbox[1]) + gap + (s_bbox[3] - s_bbox[1])
    start_y = ry + (rh - total_h) // 2

    def x_for(w):
        return rx + (rw - w) // 2 if align == "center" else rx + rw * 0.06

    # 그림자 효과
    shadow_offset = max(2, h_size // 30)
    shadow_color = (0, 0, 0, 120)

    hx = x_for(h_w)
    draw.text((hx + shadow_offset, start_y + shadow_offset), headline,
              font=h_font, fill=shadow_color)
    draw.text((hx, start_y), headline, font=h_font, fill=tc)

    sy_offset = start_y + (h_bbox[3] - h_bbox[1]) + gap
    sx = x_for(s_w)
    # 서브라인: 반투명 처리
    sub_color = hex_to_rgb(text_color) + (200,)
    draw.text((sx + shadow_offset, sy_offset + shadow_offset), subline,
              font=s_font, fill=shadow_color)
    draw.text((sx, sy_offset), subline, font=s_font, fill=sub_color)


def create_marketing_image(
    screenshot_path: str,
    output_path: str,
    headline: str,
    subline: str,
    bg_from: str = "#6B4FC8",
    bg_to: str = "#A78BF5",
    text_color: str = "#FFFFFF",
    text_position: str = "top",   # top | bottom
    device: str = "iphone_67",
    phone_scale: float = 0.72,    # 캔버스 너비 대비 스크린 너비 비율
):
    cw, ch = CANVAS_SIZES[device]

    # ── 배경 ─────────────────────────────────────────────────────────────────
    canvas = make_gradient((cw, ch), bg_from, bg_to).convert("RGBA")

    # ── 스크린샷 로드 & 스케일 ───────────────────────────────────────────────
    screen_orig = Image.open(screenshot_path).convert("RGBA")
    ow, oh = screen_orig.size

    target_sw = int(cw * phone_scale)
    target_sh = int(oh * (target_sw / ow))
    screen_scaled = screen_orig.resize((target_sw, target_sh), Image.LANCZOS)

    # ── iPhone 프레임 합성 ───────────────────────────────────────────────────
    phone_frame = draw_iphone_frame(screen_scaled, scale=target_sw / ow)
    fw, fh = phone_frame.size

    # ── 레이아웃 계산 ────────────────────────────────────────────────────────
    text_area_h = int(ch * 0.165)   # 텍스트 영역 높이
    padding_top = int(ch * 0.045)
    padding_bottom = int(ch * 0.035)

    if text_position == "top":
        text_region = (0, padding_top, cw, text_area_h)
        phone_y = padding_top + text_area_h + int(ch * 0.018)
    else:
        phone_y = padding_top
        text_region = (0, padding_top + fh + int(ch * 0.018), cw, text_area_h)

    phone_x = (cw - fw) // 2

    # 프레임이 캔버스를 벗어나면 축소
    max_phone_h = ch - text_area_h - padding_top - padding_bottom - int(ch * 0.018)
    if fh > max_phone_h:
        ratio = max_phone_h / fh
        new_fw = int(fw * ratio)
        new_fh = int(fh * ratio)
        phone_frame = phone_frame.resize((new_fw, new_fh), Image.LANCZOS)
        fw, fh = new_fw, new_fh
        phone_x = (cw - fw) // 2
        if text_position == "top":
            phone_y = padding_top + text_area_h + int(ch * 0.018)
        else:
            phone_y = padding_top

    # ── 폰 그림자 ────────────────────────────────────────────────────────────
    shadow_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    shadow_ph = Image.new("RGBA", (fw + 60, fh + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_ph).rounded_rectangle(
        [30, 30, fw + 29, fh + 29],
        radius=int(fw * FRAME["corner_r"]),
        fill=(0, 0, 0, 90),
    )
    shadow_ph = shadow_ph.filter(ImageFilter.GaussianBlur(radius=22))
    shadow_layer.paste(shadow_ph, (phone_x - 30, phone_y - 10), shadow_ph)
    canvas = Image.alpha_composite(canvas, shadow_layer)

    # ── 폰 붙이기 ────────────────────────────────────────────────────────────
    canvas.paste(phone_frame, (phone_x, phone_y), phone_frame)

    # ── 텍스트 ───────────────────────────────────────────────────────────────
    draw_text_block(canvas, headline, subline, text_region, text_color)

    # ── 저장 ─────────────────────────────────────────────────────────────────
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(str(out), "PNG", optimize=False)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"저장 완료: {out}  ({fw}×{fh} 목업, {size_mb:.1f} MB)")
    return str(out)


def main():
    parser = argparse.ArgumentParser(description="App Store 마케팅 이미지 생성 (로컬 합성)")
    parser.add_argument("--screenshot", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--headline", required=True)
    parser.add_argument("--subline", default="")
    parser.add_argument("--bg-from", default="#6B4FC8")
    parser.add_argument("--bg-to", default="#A78BF5")
    parser.add_argument("--text-color", default="#FFFFFF")
    parser.add_argument("--text-position", default="top", choices=["top", "bottom"])
    parser.add_argument("--device", default="iphone_67",
                        choices=list(CANVAS_SIZES.keys()))
    parser.add_argument("--phone-scale", type=float, default=0.72)
    args = parser.parse_args()

    create_marketing_image(
        screenshot_path=args.screenshot,
        output_path=args.output,
        headline=args.headline,
        subline=args.subline,
        bg_from=args.bg_from,
        bg_to=args.bg_to,
        text_color=args.text_color,
        text_position=args.text_position,
        device=args.device,
        phone_scale=args.phone_scale,
    )


if __name__ == "__main__":
    main()
