#!/usr/bin/env python3
"""
App Store 마케팅 이미지 규격 검증.
생성된 이미지의 크기, 용량, 포맷을 확인하고 JSON 리포트를 출력합니다.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

DEVICE_SPECS = {
    "iphone_67": {"width": 1290, "height": 2796, "max_mb": 10, "label": "iPhone 6.7\""},
    "iphone_69": {"width": 1320, "height": 2868, "max_mb": 10, "label": "iPhone 6.9\""},
    "ipad_129":  {"width": 2048, "height": 2732, "max_mb": 10, "label": "iPad 12.9\""},
}


def validate_image(path: Path, device: str) -> dict:
    spec = DEVICE_SPECS.get(device, DEVICE_SPECS["iphone_67"])
    result = {
        "file": path.name,
        "path": str(path),
        "passed": True,
        "issues": [],
        "warnings": [],
    }

    if not path.exists():
        result["passed"] = False
        result["issues"].append("파일 없음")
        return result

    # 파일 크기 체크
    file_size_mb = path.stat().st_size / (1024 * 1024)
    result["file_size_mb"] = round(file_size_mb, 2)
    if file_size_mb > spec["max_mb"]:
        result["issues"].append(f"파일 용량 초과: {file_size_mb:.1f}MB (최대 {spec['max_mb']}MB)")
        result["passed"] = False

    # 이미지 크기 및 포맷 체크
    try:
        with Image.open(path) as img:
            result["actual_width"] = img.width
            result["actual_height"] = img.height
            result["format"] = img.format or "PNG"
            result["mode"] = img.mode

            expected_w = spec["width"]
            expected_h = spec["height"]

            if img.width != expected_w or img.height != expected_h:
                result["issues"].append(
                    f"크기 불일치: {img.width}x{img.height} (필요: {expected_w}x{expected_h})"
                )
                result["passed"] = False
            else:
                result["size_ok"] = True

            if img.mode not in ("RGB", "RGBA"):
                result["warnings"].append(f"권장 색상 모드: RGB 또는 RGBA (현재: {img.mode})")

    except Exception as e:
        result["passed"] = False
        result["issues"].append(f"이미지 열기 실패: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="App Store 이미지 규격 검증")
    parser.add_argument("--output-dir", required=True, help="검증할 이미지 폴더")
    parser.add_argument("--device", default="iphone_67", choices=list(DEVICE_SPECS.keys()))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        result = {"error": f"폴더 없음: {args.output_dir}", "overall_passed": False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # temp 폴더 제외하고 PNG 파일 수집
    image_files = sorted([
        p for p in output_dir.glob("*.png")
        if "temp" not in p.stem.lower()
    ])

    if not image_files:
        result = {"error": "PNG 파일 없음", "overall_passed": False, "output_dir": str(output_dir)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    spec = DEVICE_SPECS[args.device]
    report = {
        "device": args.device,
        "device_label": spec["label"],
        "expected_size": f"{spec['width']}x{spec['height']}",
        "results": [],
        "overall_passed": True,
        "total_files": len(image_files),
        "passed_files": 0,
    }

    for img_path in image_files:
        result = validate_image(img_path, args.device)
        report["results"].append(result)
        if result["passed"]:
            report["passed_files"] += 1
        else:
            report["overall_passed"] = False

    # 리포트 출력
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 리포트 파일 저장
    report_path = output_dir / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n검증 리포트 저장: {report_path}", file=sys.stderr)

    sys.exit(0 if report["overall_passed"] else 1)


if __name__ == "__main__":
    main()
