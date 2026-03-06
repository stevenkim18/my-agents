#!/usr/bin/env python3
"""
스크린샷에 iPhone/iPad 디바이스 프레임을 프로그래밍으로 그리고 배경 위에 배치합니다.
템플릿 없이 사용할 때의 목업 생성에 사용합니다.
결과물은 텍스트가 없는 base 이미지입니다.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


DEVICE_CONFIG = {
    "iphone_67": {
        "corner_radius_ratio": 0.088,   # 프레임 너비 대비 코너 반경
        "bezel_ratio": 0.028,            # 프레임 너비 대비 베젤 두께
        "frame_color": (28, 28, 30),     # 티타늄 블랙
        "highlight_color": (72, 72, 76), # 프레임 하이라이트
        "dynamic_island": True,
        "di_width_ratio": 0.30,          # 스크린 너비 대비 다이나믹 아일랜드 너비
        "di_height_ratio": 0.038,        # 스크린 높이 대비 다이나믹 아일랜드 높이
    },
    "iphone_69": {
        "corner_radius_ratio": 0.088,
        "bezel_ratio": 0.026,
        "frame_color": (28, 28, 30),
        "highlight_color": (72, 72, 76),
        "dynamic_island": True,
        "di_width_ratio": 0.28,
        "di_height_ratio": 0.036,
    },
    "ipad_129": {
        "corner_radius_ratio": 0.055,
        "bezel_ratio": 0.030,
        "frame_color": (28, 28, 30),
        "highlight_color": (72, 72, 76),
        "dynamic_island": False,
        "di_width_ratio": 0,
        "di_height_ratio": 0,
    },
}


def crop_screenshot_to_ratio(screenshot: Image.Image, target_ratio: float) -> Image.Image:
    """스크린샷을 target_ratio(height/width)에 맞게 하단 크롭."""
    ss_ratio = screenshot.height / max(screenshot.width, 1)
    if ss_ratio > target_ratio:
        new_h = int(screenshot.width * target_ratio)
        print(f"  하단 크롭: {screenshot.height}px → {new_h}px")
        return screenshot.crop((0, 0, screenshot.width, new_h))
    return screenshot


def draw_device_frame(
    screenshot: Image.Image,
    frame_width: int,
    device: str = "iphone_67",
) -> Image.Image:
    """
    스크린샷 주위에 디바이스 프레임을 그립니다.

    Returns: RGBA 이미지 (배경 투명, 프레임+스크린샷 포함)
    """
    cfg = DEVICE_CONFIG.get(device, DEVICE_CONFIG["iphone_67"])

    bezel = max(12, int(frame_width * cfg["bezel_ratio"]))
    corner_r = max(30, int(frame_width * cfg["corner_radius_ratio"]))
    inner_r = max(corner_r - bezel, 8)

    screen_w = frame_width - bezel * 2

    # 스크린샷 비율 그대로 스크린 높이 결정 (하단 크롭 없이 비율 유지)
    screen_h = int(screen_w * screenshot.height / screenshot.width)
    frame_h = screen_h + bezel * 2

    # 스크린샷을 스크린 영역 크기로 리사이즈
    ss_resized = screenshot.resize((screen_w, screen_h), Image.LANCZOS).convert("RGBA")

    # 프레임 캔버스 (투명 배경)
    frame_img = Image.new("RGBA", (frame_width, frame_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame_img)

    # 1. 그림자 레이어 (별도로 처리)
    # 2. 디바이스 몸체
    body_color = (*cfg["frame_color"], 255)
    draw.rounded_rectangle(
        [(0, 0), (frame_width - 1, frame_h - 1)],
        radius=corner_r,
        fill=body_color,
    )

    # 3. 스크린 영역 마스크 (라운드 코너)
    screen_mask = Image.new("L", (screen_w, screen_h), 0)
    mask_draw = ImageDraw.Draw(screen_mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (screen_w - 1, screen_h - 1)],
        radius=inner_r,
        fill=255,
    )
    frame_img.paste(ss_resized, (bezel, bezel), screen_mask)

    # 4. Dynamic Island
    if cfg["dynamic_island"]:
        di_w = max(50, int(screen_w * cfg["di_width_ratio"]))
        di_h = max(14, int(screen_h * cfg["di_height_ratio"]))
        di_x = bezel + (screen_w - di_w) // 2
        di_y = bezel + max(8, int(screen_h * 0.010))
        draw.rounded_rectangle(
            [(di_x, di_y), (di_x + di_w, di_y + di_h)],
            radius=di_h // 2,
            fill=(0, 0, 0, 255),
        )

    # 5. 프레임 하이라이트 (얇은 테두리로 입체감)
    hl_color = (*cfg["highlight_color"], 160)
    draw.rounded_rectangle(
        [(0, 0), (frame_width - 1, frame_h - 1)],
        radius=corner_r,
        outline=hl_color,
        width=2,
    )

    return frame_img


def place_on_background(
    bg: Image.Image,
    device_img: Image.Image,
    text_position: str = "top",
) -> Image.Image:
    """
    배경 위에 디바이스 프레임을 배치합니다.
    텍스트 영역을 피해 디바이스를 중앙 배치하고 그림자를 추가합니다.
    """
    bg_w, bg_h = bg.size
    text_zone_ratio = 0.35

    # 텍스트 위치에 따라 디바이스 배치 영역 결정
    if text_position == "top":
        device_zone_start = int(bg_h * text_zone_ratio)
        device_zone_h = bg_h - device_zone_start
    else:
        device_zone_start = 0
        device_zone_h = int(bg_h * (1 - text_zone_ratio))

    h_padding = int(bg_w * 0.06)
    max_dev_w = bg_w - h_padding * 2
    max_dev_h = int(device_zone_h * 0.90)

    dev_w, dev_h = device_img.size
    scale = min(max_dev_w / dev_w, max_dev_h / dev_h)
    new_w = int(dev_w * scale)
    new_h = int(dev_h * scale)
    device_scaled = device_img.resize((new_w, new_h), Image.LANCZOS)

    # 배치 좌표: 수평 중앙, 수직은 약간 위쪽 (정중앙보다 10% 위)
    x = (bg_w - new_w) // 2
    y = device_zone_start + int((device_zone_h - new_h) * 0.40)

    # 그림자 생성
    shadow_spread = max(20, int(new_w * 0.04))
    shadow_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)
    shadow_cr = max(20, int(new_w * 0.088))
    shadow_draw.rounded_rectangle(
        [(shadow_spread, shadow_spread), (new_w - shadow_spread - 1, new_h - shadow_spread - 1)],
        radius=shadow_cr,
        fill=(0, 0, 0, 140),
    )
    shadow_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow_spread))

    result = bg.convert("RGBA").copy()
    shadow_offset = int(new_w * 0.015)
    result.paste(shadow_blurred, (x + shadow_offset, y + shadow_offset), shadow_blurred)
    result.paste(device_scaled, (x, y), device_scaled)

    return result.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description="스크린샷 + iPhone 프레임 → 배경에 합성 (base 이미지)")
    parser.add_argument("--screenshot", required=True, help="원본 앱 스크린샷")
    parser.add_argument("--background", required=True, help="Gemini 생성 배경 PNG")
    parser.add_argument("--output", required=True, help="base 이미지 출력 경로")
    parser.add_argument("--device", default="iphone_67", choices=list(DEVICE_CONFIG.keys()))
    parser.add_argument("--text-position", default="top", choices=["top", "bottom"])
    args = parser.parse_args()

    ss_path = Path(args.screenshot)
    bg_path = Path(args.background)
    if not ss_path.exists():
        print(f"ERROR: 스크린샷 없음: {args.screenshot}", file=sys.stderr)
        sys.exit(1)
    if not bg_path.exists():
        print(f"ERROR: 배경 없음: {args.background}", file=sys.stderr)
        sys.exit(1)

    screenshot = Image.open(ss_path).convert("RGBA")
    bg = Image.open(bg_path).convert("RGBA")

    # 프레임 너비: 배경 너비의 62%
    frame_width = int(bg.width * 0.62)
    print(f"디바이스 프레임 생성 중... (프레임 너비: {frame_width}px, 디바이스: {args.device})")
    framed = draw_device_frame(screenshot, frame_width, args.device)

    print("배경에 디바이스 배치 중...")
    result = place_on_background(bg, framed, args.text_position)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, "PNG", optimize=True)
    print(f"base 이미지 저장: {args.output}")


if __name__ == "__main__":
    main()
