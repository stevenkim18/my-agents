#!/usr/bin/env python3
"""
Gemini API를 사용해 App Store 마케팅 배경 이미지를 생성합니다.
iPhone 스크린 영역은 합성을 위해 라임그린(#00FF00)으로 채워집니다.
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

DEVICE_SIZES = {
    "iphone_67": (1290, 2796),
    "iphone_69": (1320, 2868),
    "ipad_129": (2048, 2732),
}

# 캔버스 비율에 가장 가까운 Gemini 지원 aspect_ratio
DEVICE_ASPECT_RATIO = {
    "iphone_67": "9:19",
    "iphone_69": "9:19",
    "ipad_129": "3:4",
}

MODEL_IDS = {
    "nano":  "gemini-2.5-flash-image",
    "flash": "gemini-3.1-flash-image-preview",
    "pro":   "gemini-3-pro-image-preview",
}


def build_full_prompt(creative_prompt: str, device: str, text_position: str) -> str:
    """
    배경 전용 프롬프트를 생성합니다.
    폰 목업은 포함하지 않습니다 — 목업은 add_device_frame.py가 프로그래밍으로 추가합니다.
    """
    w, h = DEVICE_SIZES.get(device, DEVICE_SIZES["iphone_67"])
    text_zone = "top 35%" if text_position == "top" else "bottom 35%"
    device_zone = "bottom 60%" if text_position == "top" else "top 60%"

    return f"""Create a professional App Store marketing BACKGROUND image.

CANVAS: {w}x{h} pixels (portrait orientation)

DESIGN:
{creative_prompt}

IMPORTANT — BACKGROUND ONLY:
This image is a pure background. Do NOT include any phone, device, mockup, UI elements, screens, or objects.
Only colors, gradients, lighting effects, bokeh, textures, and atmospheric elements.

LAYOUT ZONES:
- {text_zone}: Keep this area clean and simple (text will be overlaid here)
- {device_zone}: This is where the device mockup will be placed in post-processing — keep the background design visible here but avoid busy patterns

QUALITY: Professional, high resolution, suitable for Apple App Store marketing."""


def generate_background(
    creative_prompt: str,
    output_path: str,
    device: str = "iphone_67",
    quality: str = "flash",
    text_position: str = "top",
) -> bool:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    model_id = MODEL_IDS.get(quality, MODEL_IDS["flash"])
    full_prompt = build_full_prompt(creative_prompt, device, text_position)

    print(f"Gemini 모델: {model_id}")
    print(f"프롬프트 길이: {len(full_prompt)} chars")

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
    except Exception as e:
        print(f"ERROR: Gemini API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)

    image_saved = False
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            raw = part.inline_data.data
            # SDK 버전에 따라 bytes 또는 base64 str로 올 수 있음
            image_data = raw if isinstance(raw, bytes) else base64.b64decode(raw)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # 생성된 이미지를 타겟 크기로 리사이즈
            target_w, target_h = DEVICE_SIZES.get(device, DEVICE_SIZES["iphone_67"])
            img = Image.open(io.BytesIO(image_data)).convert("RGBA")

            if img.size != (target_w, target_h):
                print(f"리사이즈: {img.size} -> ({target_w}, {target_h})")
                img = img.resize((target_w, target_h), Image.LANCZOS)

            img.save(output_path, "PNG")
            print(f"배경 저장 완료: {output_path}")
            image_saved = True
            break

    if not image_saved:
        print("ERROR: Gemini 응답에 이미지 없음", file=sys.stderr)
        # 텍스트 응답 출력 (디버그용)
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                print(f"Gemini 텍스트 응답: {part.text[:500]}", file=sys.stderr)
        sys.exit(1)

    return True


def main():
    parser = argparse.ArgumentParser(description="Gemini로 App Store 배경 생성")
    parser.add_argument("--prompt-file", required=True, help="크리에이티브 프롬프트 파일 경로")
    parser.add_argument("--output", required=True, help="출력 PNG 경로")
    parser.add_argument("--device", default="iphone_67", choices=list(DEVICE_SIZES.keys()))
    parser.add_argument("--quality", default="flash", choices=["nano", "flash", "pro"])
    parser.add_argument("--text-position", default="top", choices=["top", "bottom"])
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"ERROR: 프롬프트 파일 없음: {args.prompt_file}", file=sys.stderr)
        sys.exit(1)

    creative_prompt = prompt_path.read_text(encoding="utf-8").strip()
    generate_background(creative_prompt, args.output, args.device, args.quality, args.text_position)


if __name__ == "__main__":
    main()
