#!/usr/bin/env python3
"""
원본 스크린샷을 목업 배경에 합성합니다.
라임그린(#00FF00) 스크린 영역을 감지하고 perspective transform으로 원본 스크린샷을 정확히 합성합니다.

핵심 규칙:
- 원본 스크린샷은 절대 변경/왜곡하지 않습니다
- 스크린 영역 비율에 맞게 스크린샷 하단을 크롭합니다 (가로 폭 기준 fit, 하단 크롭)
- 텍스트 오버레이 없이 base 이미지만 출력합니다 (텍스트는 add_text.py가 담당)
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


# ─── 스크린 영역 감지 ───────────────────────────────────────────────

def create_green_mask(img_rgb: np.ndarray) -> np.ndarray:
    """라임그린(#00FF00) 영역의 바이너리 마스크 생성."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    lower = np.array([40, 180, 180])
    upper = np.array([80, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def order_points(pts: np.ndarray) -> np.ndarray:
    """4개 점을 [좌상, 우상, 우하, 좌하] 순서로 정렬."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1).ravel()
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def find_screen_corners(bg_rgb: np.ndarray) -> np.ndarray:
    """배경 이미지에서 라임그린 스크린 플레이스홀더의 4개 꼭짓점 감지."""
    mask = create_green_mask(bg_rgb)

    green_pixels = cv2.countNonZero(mask)
    total_pixels = mask.shape[0] * mask.shape[1]
    print(f"그린 픽셀: {green_pixels} / {total_pixels} ({green_pixels/total_pixels*100:.1f}%)")

    if green_pixels < 1000:
        raise ValueError(
            "라임그린 스크린 영역을 찾을 수 없습니다. "
            "Gemini가 #00FF00 플레이스홀더를 생성했는지 확인하세요."
        )

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest = max(contours, key=cv2.contourArea)
    print(f"가장 큰 그린 영역 넓이: {cv2.contourArea(largest):.0f}px²")

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    if len(approx) == 4:
        corners = approx.reshape(4, 2).astype(np.float32)
    else:
        print(f"다각형 꼭짓점 수: {len(approx)}, 최소 사각형으로 대체합니다.")
        rect = cv2.minAreaRect(largest)
        corners = cv2.boxPoints(rect).astype(np.float32)

    return order_points(corners)


# ─── 비율 크롭 ─────────────────────────────────────────────────────

def crop_to_screen_ratio(screenshot: Image.Image, dst_corners: np.ndarray) -> Image.Image:
    """
    스크린 영역 비율에 맞게 스크린샷 하단을 크롭합니다.

    스크린샷이 스크린 영역보다 세로로 길면 하단을 잘라냅니다.
    가로 폭은 항상 원본 전체를 사용합니다 (fit-to-width, crop bottom).
    이렇게 해야 스크린샷이 목업 안에 자연스럽게 들어갑니다.
    """
    tl, tr, br, bl = dst_corners

    # 스크린 영역의 평균 가로/세로 비율 계산
    top_w = float(np.linalg.norm(tr - tl))
    left_h = float(np.linalg.norm(bl - tl))
    right_h = float(np.linalg.norm(br - tr))
    dst_ratio = (left_h + right_h) / 2.0 / max(top_w, 1)  # height/width

    ss_ratio = screenshot.height / max(screenshot.width, 1)

    if ss_ratio > dst_ratio:
        target_h = int(screenshot.width * dst_ratio)
        print(f"하단 크롭: {screenshot.width}x{screenshot.height} → {screenshot.width}x{target_h} (스크린 비율: {dst_ratio:.3f})")
        return screenshot.crop((0, 0, screenshot.width, target_h))

    return screenshot


# ─── 합성 ──────────────────────────────────────────────────────────

def composite_screenshot_onto_mockup(
    bg: Image.Image,
    screenshot: Image.Image,
    dst_corners: np.ndarray,
) -> Image.Image:
    """
    perspective transform으로 스크린샷을 목업 스크린 위치에 합성.
    스크린샷은 미리 crop_to_screen_ratio로 비율을 맞춘 상태여야 합니다.
    """
    # 크롭된 스크린샷을 스크린 영역에 맞게 변환
    cropped = crop_to_screen_ratio(screenshot, dst_corners)
    sw, sh = cropped.size
    src_pts = np.array([[0, 0], [sw, 0], [sw, sh], [0, sh]], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src_pts, dst_corners)

    bg_rgba = np.array(bg.convert("RGBA"))
    ss_rgba = np.array(cropped.convert("RGBA"))

    warped = cv2.warpPerspective(
        ss_rgba, M, (bg.width, bg.height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )

    green_mask = create_green_mask(bg_rgba[:, :, :3])

    # 그린 마스크를 약간 팽창(dilate)시켜 가장자리 잔여 제거
    kernel = np.ones((9, 9), np.uint8)
    green_mask_dilated = cv2.dilate(green_mask, kernel, iterations=2)

    warped_valid = warped[:, :, 3] > 10

    result = bg_rgba.copy()
    # 팽창된 그린 영역 + warped 유효 픽셀 모두 교체
    replace_mask = (green_mask_dilated > 0) | warped_valid
    result[replace_mask] = warped[replace_mask]

    # warped가 완전 투명한 그린 잔여는 검정으로 채움
    fully_transparent = warped[:, :, 3] == 0
    result[fully_transparent & (green_mask_dilated > 0)] = [0, 0, 0, 255]

    return Image.fromarray(result, "RGBA")


# ─── 메인 ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="스크린샷 + 배경 합성 (base 이미지 출력, 텍스트 없음)")
    parser.add_argument("--background", required=True, help="Gemini 생성 배경 PNG")
    parser.add_argument("--screenshot", required=True, help="원본 앱 스크린샷")
    parser.add_argument("--output", required=True, help="base 이미지 출력 경로 (텍스트 없음)")
    args = parser.parse_args()

    bg_path = Path(args.background)
    ss_path = Path(args.screenshot)

    if not bg_path.exists():
        print(f"ERROR: 배경 파일 없음: {args.background}", file=sys.stderr)
        sys.exit(1)
    if not ss_path.exists():
        print(f"ERROR: 스크린샷 파일 없음: {args.screenshot}", file=sys.stderr)
        sys.exit(1)

    print(f"배경 로드: {args.background}")
    bg = Image.open(bg_path).convert("RGBA")
    print(f"스크린샷 로드: {args.screenshot}")
    screenshot = Image.open(ss_path).convert("RGBA")

    bg_array = np.array(bg)[:, :, :3]

    print("라임그린 스크린 영역 감지 중...")
    try:
        corners = find_screen_corners(bg_array)
        print(f"스크린 꼭짓점: {corners}")
        result = composite_screenshot_onto_mockup(bg, screenshot, corners)
    except ValueError as e:
        print(f"WARNING: {e}", file=sys.stderr)
        print("폴백: 스크린샷을 중앙에 배치합니다.", file=sys.stderr)
        result = bg.convert("RGBA").copy()
        bg_w, bg_h = bg.size
        # 폴백도 하단 크롭 적용 (세로 70% 영역에 fit-to-width)
        avail_h = int(bg_h * 0.68)
        scale = min(bg_w * 0.62 / screenshot.width, avail_h / screenshot.height)
        new_w = int(screenshot.width * scale)
        new_h = int(screenshot.height * scale)
        ss_resized = screenshot.resize((new_w, new_h), Image.LANCZOS)
        x_offset = (bg_w - new_w) // 2
        y_offset = int(bg_h * 0.22)
        result.paste(ss_resized, (x_offset, y_offset), ss_resized)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(args.output, "PNG", optimize=True)
    print(f"base 이미지 저장: {args.output}")


if __name__ == "__main__":
    main()
