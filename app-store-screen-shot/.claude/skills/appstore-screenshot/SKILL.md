---
name: appstore-screenshot
description: 앱 스크린샷을 입력받아 App Store Connect 규격의 마케팅 이미지를 자동 생성합니다. iOS/iPadOS 앱에 사용 가능합니다.
disable-model-invocation: true
argument-hint: "[선택사항: 스크린샷 경로들]"
---

# App Store 마케팅 이미지 자동 생성기

## 실행 지침

입력: $ARGUMENTS

아래 순서대로 실행하세요.

---

### STEP 0: 인터랙티브 설정 수집

사용자에게 아래 질문을 **한 번에 하나씩** 순서대로 물어보세요. 각 답변을 받은 후 다음 질문으로 넘어가세요.

**Q0. 스크린샷 경로**

$ARGUMENTS에 경로가 이미 포함되어 있으면 이 질문은 건너뜁니다. 없으면 질문합니다:

> 스크린샷 파일 또는 폴더 경로를 알려주세요.
> (예: `screenshots/` 또는 개별 파일 경로)

---

**Q1. 앱 이름**

> 앱 이름이 무엇인가요?

---

**Q2. 헤드라인 / 서브라인 문구**

> 각 스크린샷에 들어갈 헤드라인·서브라인 문구를 직접 제공하시나요?
>
> 1. 네, 직접 입력할게요 → 입력받기
> 2. 아니요, AI가 자동 생성해주세요

---

**Q3. 기기 종류**

> 어떤 기기용 이미지를 만들까요?
>
> 1. iPhone 6.7인치 (iPhone 15/16/17 Pro Max) — 1290×2796
> 2. iPhone 6.9인치 (iPhone 16/17 Pro Max) — 1320×2868
> 3. iPad 12.9인치 — 2048×2732

---

**Q4. Gemini 모델**

> 이미지 생성에 사용할 모델을 선택하세요:
>
> 1. 나노바나나 Pro — 최고 품질, 느림 (gemini-3-pro-image-preview)
> 2. 나노바나나 2 — 빠름, 실용적 (gemini-3.1-flash-image-preview)
> 3. 나노바나나 1 — 가장 빠름 (gemini-2.5-flash-image)

---

**Q5. 이미지 해상도**

> 생성할 이미지 해상도를 선택하세요:
>
> 1. 4K — 최고 화질 (App Store 제출 권장)
> 2. 2K — 고화질, 균형적 (기본값)
> 3. 1K — 표준
> 4. 512px — 빠른 테스트용 (나노바나나 2 전용)

---

**Q6. 배경 스타일**

> 배경 스타일을 선택하세요:
>
> 1. 그라디언트 — 부드러운 색상 그라디언트
> 2. 미니멀 화이트 — 깔끔한 흰색 계열
> 3. 다크 — 어두운 배경으로 고급스러운 느낌
> 4. 기타 — 직접 설명해주세요

---

**Q7. 출력 언어**

> 어떤 언어로 이미지를 생성할까요?
>
> 1. 한국어만
> 2. 영어만
> 3. 한국어 + 영어 둘 다

---

**설정 요약 및 확인**

모든 답변을 받은 후, 아래 형식으로 요약하고 확인을 받으세요:

```
설정 요약:
- 스크린샷: {경로 목록}
- 앱 이름: {app_name}
- 헤드라인 문구: {직접 입력 / AI 자동 생성}
- 기기: {device} ({canvas_size})
- 모델: {model_name}
- 이미지 해상도: {image_size}
- 배경 스타일: {style}
- 출력 언어: {languages}

이 설정으로 시작할까요?
```

확인을 받으면 STEP 1부터 진행합니다.

---

### STEP 0.5: 환경 확인

**의존성 설치 확인:**

```bash
pip install -q -r ${CLAUDE_SKILL_DIR}/requirements.txt
```

**`.env` 파일 확인:**

프로젝트 루트에 `.env` 파일이 없으면 아래 내용으로 생성하도록 안내하세요:

```
GEMINI_API_KEY=여기에_Gemini_API_키_입력
```

Gemini API 키는 https://aistudio.google.com/apikey 에서 발급받을 수 있습니다.

---

**파싱 결과 내부 변수:**
- `screenshot_paths`: Q0 답변 또는 $ARGUMENTS에서 추출한 경로 목록
- `app_name`: Q1 답변
- `headline_ko` / `headline_en`: Q2 답변 (자동 생성이면 null)
- `device`: Q3 → 1=iphone_67, 2=iphone_69, 3=ipad_129
- `quality` / `model`: Q4 → 1=pro (gemini-3-pro-image-preview), 2=flash (gemini-3.1-flash-image-preview), 3=nano (gemini-2.5-flash-image)
- `image_size`: Q5 → 1=4K, 2=2K, 3=1K, 4=512px (※ 512px는 nano/flash 전용)
- `style`: Q6 → 1=gradient, 2=minimal, 3=dark, 4=기타(사용자 설명)
- `languages`: Q7 → ko / en / both
- `output_dir`: `outputs/YYYYMMDD-HHMMSS` (파이프라인 시작 시각 기준)

캔버스 크기:
- iphone_67 → 1290×2796
- iphone_69 → 1320×2868
- ipad_129  → 2048×2732

---

### STEP 1: 분석 에이전트 실행

`analysis-agent` 서브에이전트를 실행합니다.

에이전트에 전달할 내용:
```
다음 앱 스크린샷들을 분석해주세요.

스크린샷 경로:
{screenshot_paths를 한 줄씩 나열}

{app_name이 있으면: "앱 이름: {app_name}"}

각 스크린샷을 Read 도구로 읽어서 앱의 색상, 분위기, 기능을 분석하고
지정된 JSON 형식으로 결과를 출력해주세요.
```

분석 결과(JSON)를 저장합니다.

---

### STEP 2: 콘텐츠 에이전트 실행

`content-agent` 서브에이전트를 실행합니다.

에이전트에 전달할 내용:
```
다음 분석 결과를 바탕으로 App Store 마케팅 콘텐츠를 생성해주세요.

## 앱 분석 결과
{STEP 1의 JSON 전체}

## 설정
- 배경 스타일: {style}
- 기기: {device}
- 캔버스 크기: {width}x{height}
{headline_ko가 있으면: "- 사용자 지정 한국어 헤드라인: {headline_ko}"}
{headline_en이 있으면: "- 사용자 지정 영어 헤드라인: {headline_en}"}

## 스크린샷 목록 (인덱스 순서 유지)
{index: 0, path: "경로1"},
{index: 1, path: "경로2"},
...

각 스크린샷에 대해 headline_ko, headline_en, text_position, text_color, gemini_creative_prompt를
지정된 JSON 형식으로 출력해주세요. JSON만 출력하세요.
```

콘텐츠 플랜(JSON)을 저장합니다.

---

### STEP 3: 이미지 생성 에이전트 실행

`image-generation-agent` 서브에이전트를 실행합니다.

에이전트에 전달할 내용:
```
다음 콘텐츠 플랜을 바탕으로 App Store 마케팅 이미지를 생성해주세요.

## 핵심 방식
generate_full_marketing.py를 사용합니다.
Gemini가 스크린샷을 이미지 입력으로 받아 배경+목업+텍스트를 한 번에 생성합니다.

## 콘텐츠 플랜
{STEP 2의 JSON 전체}

## 설정
- device: {device}
- model: {model} (pro=gemini-3-pro-image-preview, flash=gemini-3.1-flash-image-preview, nano=gemini-2.5-flash-image)
- image_size: {image_size} (4K / 2K / 1K / 512px)
- output_dir: {출력 디렉토리 경로}
- 출력 언어: {languages} (ko만/en만/둘 다에 따라 해당 언어만 생성)

## 스크립트 경로
- scripts_dir: ${CLAUDE_SKILL_DIR}/scripts

프로젝트 루트 디렉토리에서 python3로 실행하세요.

## 출력 구조
{languages가 ko 또는 both: output_dir}/ko/ - 한국어 버전}
{languages가 en 또는 both: output_dir}/en/ - 영어 버전}
```

생성된 이미지 경로 목록을 저장합니다.

---

### STEP 4: 검증 에이전트 실행

`validation-agent` 서브에이전트를 실행합니다.

에이전트에 전달할 내용:
```
다음 출력 폴더의 이미지를 검증해주세요.

- output_dir: {출력 디렉토리 경로}
- device: {device}
- scripts_dir: ${CLAUDE_SKILL_DIR}/scripts

Python 스크립트로 규격을 검증하고, Read 도구로 각 이미지를 직접 확인하세요.
```

---

### STEP 5: 최종 결과 보고

사용자에게 다음을 보고합니다:

```
## App Store 마케팅 이미지 생성 완료

생성된 이미지: {N}장
출력 경로: {output_dir}/

| # | 파일 | 헤드라인 | 검증 |
|---|------|----------|------|
| 1 | 01_final.png | {headline_ko} | PASS |
...

검증 결과: {전체 결과}
```

오류가 발생한 경우 원인과 해결 방법을 제안하세요.
