# multi-agent

시뮬레이터 스크린샷을 바탕으로 App Store 제출용 마케팅 이미지를 자동 생성하는 멀티에이전트 프로젝트입니다.

현재 포함된 주요 프로젝트는 `app-store-screen-shot/` 입니다.

## 프로젝트 소개

`app-store-screen-shot`은 iOS/iPadOS 앱 스크린샷을 입력받아 다음 작업을 자동으로 수행합니다.

- 스크린샷 분석
- 헤드라인/서브카피 생성
- Gemini 기반 마케팅 이미지 생성
- 결과물 규격 검증

생성 결과물은 한국어/영어 버전으로 만들 수 있으며, App Store Connect 업로드용 이미지 제작 워크플로우를 줄이는 것이 목적입니다.

## 폴더 구조

```text
.
├── README.md
└── app-store-screen-shot/
    ├── .claude/
    ├── screenshots/
    ├── templates/
    ├── output/
    ├── outputs/
    └── CLAUDE.md
```

## 요구 사항

- Python 3.10+
- Gemini API 키

## 빠른 시작

1. 의존성 설치

```bash
pip install -r app-store-screen-shot/.claude/skills/appstore-screenshot/requirements.txt
```

2. 루트 또는 작업 디렉터리에 `.env` 파일 생성

```env
GEMINI_API_KEY=YOUR_API_KEY
```

3. 스크린샷 생성 스크립트 실행

```bash
python app-store-screen-shot/.claude/skills/appstore-screenshot/scripts/generate_full_marketing.py \
  --screenshot "app-store-screen-shot/screenshots/example.png" \
  --headline "말씀을 더 쉽게" \
  --subheadline "앱스토어용 이미지를 자동 생성합니다" \
  --creative-bg "clean gradient background with premium lighting" \
  --output "app-store-screen-shot/outputs/sample/01.png" \
  --style gradient \
  --device iphone_67 \
  --quality flash \
  --image-size 2K \
  --text-position top \
  --lang ko
```

## 출력 결과

생성된 이미지는 주로 아래 경로에 저장됩니다.

- `app-store-screen-shot/output/`
- `app-store-screen-shot/outputs/`

## 참고

- 상세 워크플로우: `app-store-screen-shot/CLAUDE.md:1`
- 스킬 정의: `app-store-screen-shot/.claude/skills/appstore-screenshot/SKILL.md:1`
