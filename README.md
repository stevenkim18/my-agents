# multi-agent

여러 작업을 멀티 에이전트 방식으로 자동화하는 실험용 저장소입니다.

현재 두 개의 프로젝트가 들어 있습니다.

- `app-store-screen-shot/` — 앱 스크린샷을 App Store용 마케팅 이미지로 변환
- `idea-to-docs/` — 서비스 아이디어를 인터뷰하고 기획 문서 세트로 확장

## 폴더별 설명

### `app-store-screen-shot/`

iOS/iPadOS 앱 스크린샷을 분석해서 App Store 제출용 마케팅 이미지를 만드는 프로젝트입니다.

주요 에이전트:

- `analysis-agent` — 스크린샷을 보고 앱 성격, 색감, 핵심 기능 분석
- `content-agent` — 한국어/영어 헤드라인과 배경 프롬프트 작성
- `image-generation-agent` — Gemini로 최종 마케팅 이미지 생성
- `validation-agent` — 결과 이미지 규격과 품질 검토

주요 출력:

- `app-store-screen-shot/output/`
- `app-store-screen-shot/outputs/`

실행에 필요한 항목:

- Python 3.10+
- `GEMINI_API_KEY`

예시 실행:

```bash
pip install -r app-store-screen-shot/.claude/skills/appstore-screenshot/requirements.txt

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

### `idea-to-docs/`

하나의 아이디어를 입력받아 인터뷰, 분석, 설계, QA 문서까지 순차적으로 만드는 프로젝트입니다.

주요 에이전트:

- `business` — 시장성, 경쟁 환경, 수익화 가능성 분석
- `risk` — 기술·운영·법적 리스크 점검
- `mvp` — MVP 범위와 우선순위 정리
- `prd` — 제품 목표, 타겟 사용자, 핵심 기능 정의
- `user-story` — 사용자 시나리오와 엣지 케이스 정리
- `wireframe` — 화면 흐름과 구조 설계
- `tech-spec` — 아키텍처, API, 데이터 구조 정리
- `qa` — 테스트 시나리오와 검증 항목 작성

주요 출력:

- `idea-to-docs/outputs/{timestamp}/`

이 프로젝트는 `/idea-to-docs` 커맨드를 중심으로 동작하도록 설계돼 있습니다.

## 폴더 구조

```text
.
├── README.md
├── app-store-screen-shot/
└── idea-to-docs/
```

## 참고

- `app-store-screen-shot/CLAUDE.md:1`
- `app-store-screen-shot/.claude/skills/appstore-screenshot/SKILL.md:1`
- `idea-to-docs/CLAUDE.md:1`
- `idea-to-docs/.claude/skills/idea-to-docs/SKILL.md:1`
