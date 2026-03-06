# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 프로젝트 목적

시뮬레이터 스크린샷을 입력받아 App Store용 마케팅 이미지를 자동 생성하는 범용 멀티에이전트 파이프라인입니다. 어떤 iOS/iPadOS 앱에도 적용 가능합니다.

클로드 코드에서 `/appstore-screenshot` 스킬로 만들어서 호출을 하려고 합니다.

## 아키텍처

### 에이전트 파이프라인 (`.claude/agents/`)
1. **analysis-agent** (Sonnet) — 스크린샷 시각 분석: 앱 이름, 색상, 분위기, 기능 추출
2. **content-agent** (Sonnet) — KO/EN 헤드라인 + 배경 디자인 프롬프트 생성
3. **image-generation-agent** (Sonnet) — `generate_full_marketing.py` 실행: Gemini가 스크린샷을 이미지 입력으로 받아 배경+목업+텍스트 한 번에 생성
4. **validation-agent** (Sonnet) — `validate_output.py` 실행 + 시각적 품질 검토

### 핵심 스크립트 (`.claude/skills/appstore-screenshot/scripts/`)
- `generate_full_marketing.py` — **메인 생성 스크립트**: 스크린샷 + 프롬프트 → Gemini → 완성된 마케팅 이미지
- `validate_output.py` — App Store 규격 검증 (크기, 용량)
- `composite_screenshot.py` — 템플릿 있을 때 그린스크린 합성용 (현재 미사용)
- `add_device_frame.py` — Python 프레임 추가 (현재 미사용)
- `add_text.py` — 텍스트 오버레이 (현재 미사용)

### 의존성 (`.claude/skills/appstore-screenshot/requirements.txt`)

### 출력 구조
```
outputs/YYYYMMDD-HHMMSS/
  ko/  — 한국어 버전
  en/  — 영어 버전
```

## gemini 모델
- 나노 바나나1: gemini-2.5-flash-image
- 나노 바나나2: gemini-3.1-flash-image-preview
- 나노 바나나 pro: gemini-3-pro-image-preview


## 핵심 설계 결정
- **캔버스 크기** (px):
  - `iphone_67`: 1290×2796 (기본값, iPhone 15/16 Pro Max)
  - `iphone_69`: 1320×2868 (iPhone 16/17 Pro Max)
  - `ipad_129`: 2048×2732

## 참고 문서

- 서브에이전트: https://code.claude.com/docs/en/sub-agents
- 스킬: https://code.claude.com/docs/en/skills
- 나노 바나나2: https://ai.google.dev/gemini-api/docs/image-generation?hl=ko

## Gemini API
- .env파일에 키가 있음.