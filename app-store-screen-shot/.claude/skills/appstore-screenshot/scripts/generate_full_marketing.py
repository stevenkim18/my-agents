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


def build_greenscreen_prompt(
    headline: str,
    subheadline: str,
    style: str,
    creative_bg: str,
    device: str,
    text_position: str,
    lang: str,
) -> str:
    """그린스크린 모드: 스크린 영역을 #00FF00으로 채운 기기 프레임 + 배경 + 텍스트 생성."""
    w, h = DEVICE_SIZES.get(device, DEVICE_SIZES["iphone_67"])
    device_name = DEVICE_LABEL.get(device, "iPhone 16 Pro Max")
    text_zone   = "top 30%" if text_position == "top" else "bottom 30%"
    lang_label  = "Korean" if lang == "ko" else "English"

    return f"""Create a professional App Store marketing image. Canvas: {w}x{h} pixels (portrait).

BACKGROUND DESIGN ({style} style — applies ONLY outside the device frame):
{creative_bg}

DEVICE MOCKUP:
- Place the {device_name} device frame prominently
- The device must be LARGE — width fills at least 85% of the canvas width
- Center the device horizontally; bottom of device extends to or beyond the canvas bottom edge (intentional crop)
- Top of device sits just below the headline text area
- Keep device perfectly upright (0-5 degree tilt maximum)
- Realistic drop shadow behind the device

SCREEN PLACEHOLDER (ABSOLUTE REQUIREMENT):
- Fill the ENTIRE device screen area with PURE LIME GREEN: RGB(0, 255, 0) / HEX #00FF00
- Solid flat color only — NO gradients, NO transparency, NO texture, NO blending
- The green must cover every pixel of the screen, corner to corner
- Do NOT place any UI elements, text, or images inside the screen area

HEADLINE TEXT (in the {text_zone}, at least 100px from the top edge):
- Main headline ({lang_label}, large bold): "{headline}"
- Subtitle ({lang_label}, smaller regular weight): "{subheadline}"
- Center-align horizontally; keep all text fully within the canvas bounds
- Use white or light-colored text that contrasts well with the background

QUALITY: Ultra high resolution, professional Apple App Store marketing material."""


def build_prompt(
    headline: str,
    subheadline: str,
    style: str,
    creative_bg: str,
    device: str,
    text_position: str,
    lang: str,
    screenshot_type: str = "app_ui",
) -> str:
    w, h = DEVICE_SIZES.get(device, DEVICE_SIZES["iphone_67"])
    device_name = DEVICE_LABEL.get(device, "iPhone 16 Pro Max")
    text_zone   = "top 30%" if text_position == "top" else "bottom 30%"
    lang_label  = "Korean" if lang == "ko" else "English"

    system_ui_warning = ""
    if screenshot_type == "system_ui":
        system_ui_warning = """
SYSTEM UI SCREENSHOT WARNING:
- The attached screenshot shows iOS system UI (e.g. Spotlight search, widgets, lock screen, share sheet)
- This is NOT app content you can redraw — it is a real OS screenshot captured on device
- Reproduce it with extreme accuracy: every search result row, icon, text, color, and background must match exactly
- The iOS wallpaper/background visible in the screenshot must remain unchanged
- Do NOT invent, add, or remove any search result, app suggestion, or system element
"""

    return f"""Create a professional App Store marketing image. Canvas: {w}x{h} pixels (portrait).

BACKGROUND DESIGN ({style} style — applies ONLY outside the device frame):
{creative_bg}

DEVICE MOCKUP:
- Place the attached screenshot inside a {device_name} device frame
- The device must be LARGE — width fills at least 85% of the canvas width
- Center the device horizontally; bottom of device extends to or beyond the canvas bottom edge (intentional crop)
- Top of device sits just below the headline text area
- Keep device perfectly upright (0-5 degree tilt maximum)
- Realistic drop shadow behind the device
- The marketing background applies ONLY outside the device frame — do NOT bleed any gradient or color into the screen area
{system_ui_warning}
SCREENSHOT INTEGRITY (ABSOLUTE REQUIREMENT — NO EXCEPTIONS):
- Treat the attached screenshot as a photograph: reproduce every pixel exactly
- DO NOT zoom in, crop, or enlarge any part of the screenshot — the FULL screenshot must be visible from top to bottom inside the device screen
- DO NOT redraw, simplify, reinterpret, or hallucinate any UI element, text, icon, color, or layout
- DO NOT change the background color of the screenshot (white stays white, dark stays dark, blur stays blur)
- If the screenshot contains a keyboard, Spotlight UI, system dialogs, or any OS-level element, reproduce them with exact fidelity — do not invent variations
- The screenshot is placed as-is inside the device screen; nothing about its content changes

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
    screenshot_type: str = "app_ui",
    greenscreen: bool = False,
) -> None:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY 없음", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    model_id = MODEL_IDS[quality]

    if greenscreen:
        # 그린스크린 모드: 스크린샷 없이 기기 프레임 + 배경 + 텍스트만 생성
        prompt = build_greenscreen_prompt(headline, subheadline, style, creative_bg, device, text_position, lang)
        print(f"[그린스크린] 모델: {model_id} | 해상도: {image_size} | 언어: {lang.upper()}")
        contents = [types.Part.from_text(text=prompt)]
    else:
        # 기본 모드: 스크린샷을 이미지 입력으로 전달
        ss_path = Path(screenshot_path)
        if not ss_path.exists():
            print(f"ERROR: 스크린샷 없음: {screenshot_path}", file=sys.stderr)
            sys.exit(1)

        screenshot = Image.open(ss_path).convert("RGB")
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        ss_bytes = buf.getvalue()

        prompt = build_prompt(headline, subheadline, style, creative_bg, device, text_position, lang, screenshot_type)
        print(f"모델: {model_id} | 해상도: {image_size} | 언어: {lang.upper()} | 프롬프트: {len(prompt)}자")
        contents = [
            types.Part.from_bytes(data=ss_bytes, mime_type="image/png"),
            types.Part.from_text(text=prompt),
        ]

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
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
    parser.add_argument("--screenshot",    required=False, default="")
    parser.add_argument("--headline",      required=True, help="헤드라인 텍스트")
    parser.add_argument("--subheadline",   default="",    help="서브헤드라인 텍스트")
    parser.add_argument("--creative-bg",   required=True, help="배경 디자인 설명 (영어)")
    parser.add_argument("--output",        required=True)
    parser.add_argument("--style",         default="gradient")
    parser.add_argument("--device",        default="iphone_67", choices=list(DEVICE_SIZES))
    parser.add_argument("--quality",       default="flash",     choices=["nano", "flash", "pro"])
    parser.add_argument("--image-size",    default="2K",        choices=["512px", "1K", "2K", "4K"])
    parser.add_argument("--text-position",    default="top",      choices=["top", "bottom"])
    parser.add_argument("--lang",             default="ko",       choices=["ko", "en"])
    parser.add_argument("--screenshot-type",  default="app_ui",   choices=["app_ui", "system_ui"],
                        help="app_ui=일반 앱 화면, system_ui=Spotlight/위젯/잠금화면 등 iOS 시스템 UI")
    parser.add_argument("--greenscreen", action="store_true",
                        help="그린스크린 모드: 스크린 영역을 #00FF00으로 채운 기기 프레임 생성 (스크린샷 불필요)")
    args = parser.parse_args()

    if not args.greenscreen and not args.screenshot:
        parser.error("--screenshot 또는 --greenscreen 중 하나가 필요합니다")

    generate(
        screenshot_path=args.screenshot or "",
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
        screenshot_type=args.screenshot_type,
        greenscreen=args.greenscreen,
    )
    print_api_summary()


if __name__ == "__main__":
    main()
