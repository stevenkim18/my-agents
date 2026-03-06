#!/usr/bin/env python3
"""
스크린샷을 이미지 입력으로 Gemini에게 전달하여
배경 + iPhone 목업 + 스크린샷 + 헤드라인 텍스트를 한 번에 생성합니다.
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# ─── API 호출 추적 ────────────────────────────────────────────────
_CALL_LOG_PATH = Path("outputs/.api_call_log.json")

def _log_api_call(model: str, success: bool, output_path: str) -> None:
    """Gemini API 호출을 로그 파일에 기록합니다."""
    _CALL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if _CALL_LOG_PATH.exists():
        try:
            log = json.loads(_CALL_LOG_PATH.read_text())
        except Exception:
            log = []
    log.append({
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "success": success,
        "output": output_path,
    })
    _CALL_LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2))

def print_api_summary() -> None:
    """현재까지의 API 호출 요약을 출력합니다."""
    if not _CALL_LOG_PATH.exists():
        print("API 호출 기록 없음")
        return
    log = json.loads(_CALL_LOG_PATH.read_text())
    from collections import Counter
    model_counts = Counter(e["model"] for e in log)
    success_count = sum(1 for e in log if e["success"])
    print(f"\n{'='*50}")
    print(f"Gemini API 호출 요약")
    print(f"{'='*50}")
    print(f"총 호출 횟수: {len(log)}회 (성공: {success_count}, 실패: {len(log)-success_count})")
    for model, count in model_counts.items():
        print(f"  - {model}: {count}회")
    print(f"{'='*50}\n")

DEVICE_SIZES = {
    "iphone_67": (1290, 2796),
    "iphone_69": (1320, 2868),
    "ipad_129":  (2048, 2732),
}

MODEL_IDS = {
    "nano":  "gemini-2.5-flash-image",
    "flash": "gemini-3.1-flash-image-preview",
    "pro":   "gemini-3-pro-image-preview",
}

DEVICE_LABEL = {
    "iphone_67": "iPhone 16 Pro Max",
    "iphone_69": "iPhone 17 Pro Max",
    "ipad_129":  "iPad Pro 12.9-inch M4",
}


def build_prompt(
    headline: str,
    subheadline: str,
    style: str,
    creative_bg: str,
    device: str,
    text_position: str,
    lang: str,
) -> str:
    w, h = DEVICE_SIZES.get(device, DEVICE_SIZES["iphone_67"])
    device_name = DEVICE_LABEL.get(device, "iPhone 16 Pro Max")
    text_zone   = "top 30%" if text_position == "top" else "bottom 30%"
    lang_label  = "Korean" if lang == "ko" else "English"

    return f"""Create a professional App Store marketing image. Canvas: {w}x{h} pixels (portrait).

BACKGROUND DESIGN ({style} style):
{creative_bg}

DEVICE MOCKUP (CRITICAL SIZE REQUIREMENT):
- Place the attached app screenshot inside a {device_name} mockup
- The phone must be LARGE — its width should fill at least 85% of the canvas width
- The phone should be centered horizontally and positioned so the bottom of the phone extends BEYOND or right to the bottom edge of the canvas (cropping the bottom of the phone is intentional and expected)
- The top of the phone should sit just below the headline text area
- Keep the phone perfectly upright (0-5 degrees tilt maximum)
- Realistic drop shadow behind the device
- CRITICAL: The marketing background design applies ONLY to the area OUTSIDE the phone frame. The phone screen displays the screenshot exactly — do NOT apply the background color, gradient, or any design element inside the phone screen

SCREENSHOT INTEGRITY (NON-NEGOTIABLE):
- The attached screenshot content must appear EXACTLY as provided — pixel-perfect reproduction
- DO NOT alter, redraw, simplify, translate, or modify ANY part of the screenshot
- DO NOT change colors, text, icons, layout, or any visual element of the screenshot
- The screenshot is the actual app UI — it must look identical to the input image
- Only place it inside the phone frame; do not touch its content
- The background color/gradient of the screenshot (e.g. white, black) must be preserved exactly as-is inside the phone screen
- CRITICAL: If the screenshot contains a keyboard or any UI element at the bottom, render it ONLY inside the phone screen. Do NOT redraw or duplicate any keyboard, UI overlay, or element from the screenshot outside the phone frame

HEADLINE TEXT (in the {text_zone}, at least 100px from the top edge):
- Main headline ({lang_label}, large bold): "{headline}"
- Subtitle ({lang_label}, smaller regular weight): "{subheadline}"
- Center-align horizontally; keep all text fully within the canvas bounds
- Use white or light-colored text that contrasts well with the background

QUALITY: Ultra high resolution, professional Apple App Store marketing material."""


def generate(
    screenshot_path: str,
    headline: str,
    subheadline: str,
    creative_bg: str,
    output_path: str,
    style: str = "gradient",
    device: str = "iphone_67",
    quality: str = "flash",
    image_size: str = "2K",
    text_position: str = "top",
    lang: str = "ko",
) -> None:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY 없음", file=sys.stderr)
        sys.exit(1)

    # 스크린샷 로드
    ss_path = Path(screenshot_path)
    if not ss_path.exists():
        print(f"ERROR: 스크린샷 없음: {screenshot_path}", file=sys.stderr)
        sys.exit(1)

    screenshot = Image.open(ss_path).convert("RGB")
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    ss_bytes = buf.getvalue()

    prompt = build_prompt(headline, subheadline, style, creative_bg, device, text_position, lang)
    print(f"모델: {MODEL_IDS[quality]} | 해상도: {image_size} | 언어: {lang.upper()} | 프롬프트: {len(prompt)}자")

    client = genai.Client(api_key=api_key)

    model_id = MODEL_IDS[quality]
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=[
                types.Part.from_bytes(data=ss_bytes, mime_type="image/png"),
                types.Part.from_text(text=prompt),
            ],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    image_size=image_size,
                ),
            ),
        )
    except Exception as e:
        _log_api_call(model_id, success=False, output_path=output_path)
        print(f"ERROR: Gemini API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)

    image_saved = False
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            raw = part.inline_data.data
            image_data = raw if isinstance(raw, bytes) else bytes(raw)

            target_w, target_h = DEVICE_SIZES.get(device, DEVICE_SIZES["iphone_67"])
            img = Image.open(io.BytesIO(image_data)).convert("RGB")

            if img.size != (target_w, target_h):
                print(f"  리사이즈: {img.size} → ({target_w}, {target_h})")
                img = img.resize((target_w, target_h), Image.LANCZOS)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG", optimize=True)
            print(f"  저장 완료: {output_path}")
            _log_api_call(model_id, success=True, output_path=output_path)
            image_saved = True
            break

    if not image_saved:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                print(f"  Gemini 텍스트: {part.text[:300]}", file=sys.stderr)
        _log_api_call(model_id, success=False, output_path=output_path)
        print("ERROR: Gemini 응답에 이미지 없음", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Gemini로 App Store 마케팅 이미지 완성본 생성")
    parser.add_argument("--screenshot",    required=True)
    parser.add_argument("--headline",      required=True, help="헤드라인 텍스트")
    parser.add_argument("--subheadline",   default="",    help="서브헤드라인 텍스트")
    parser.add_argument("--creative-bg",   required=True, help="배경 디자인 설명 (영어)")
    parser.add_argument("--output",        required=True)
    parser.add_argument("--style",         default="gradient")
    parser.add_argument("--device",        default="iphone_67", choices=list(DEVICE_SIZES))
    parser.add_argument("--quality",       default="flash",     choices=["nano", "flash", "pro"])
    parser.add_argument("--image-size",    default="2K",        choices=["512px", "1K", "2K", "4K"])
    parser.add_argument("--text-position", default="top",       choices=["top", "bottom"])
    parser.add_argument("--lang",          default="ko",        choices=["ko", "en"])
    args = parser.parse_args()

    generate(
        screenshot_path=args.screenshot,
        headline=args.headline,
        subheadline=args.subheadline,
        creative_bg=args.creative_bg,
        output_path=args.output,
        style=args.style,
        device=args.device,
        quality=args.quality,
        image_size=args.image_size,
        text_position=args.text_position,
        lang=args.lang,
    )
    print_api_summary()


if __name__ == "__main__":
    main()
