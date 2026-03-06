# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 프로젝트 개요

**idea-to-docs**: `/idea-to-docs` 슬래시 커맨드 하나로 아이디어 인터뷰부터 전체 문서 생성까지 자동화하는 멀티 에이전트 파이프라인.

## 실행 방법

```
/idea-to-docs
```

## 전체 플로우

```
/idea-to-docs
       │
       ▼
 [Phase 1: 아이디어 인터뷰]
  Claude가 자유롭게 질문하며 아이디어 구체화
  → 구조화된 브리프 작성 후 사용자 확인
       │
       ▼
 [Phase 2: 문서 생성]
  outputs/{timestamp}/ 폴더 생성
       │
       ├── 병렬: 1.비즈니스 분석 + 2.리스크 분석
       │              │  (각자 파일 저장)
       │         3. MVP 스코핑 (파일 저장)
       │              │
       │          4. PRD 작성 (파일 저장)
       │              │
       │    병렬: 5.유저 스토리 + 6.와이어프레임
       │              │  (각자 파일 저장)
       │          7. 기술 스펙 (파일 저장)
       │              │
       │          8. QA 시나리오 (파일 저장)
       │
       ▼
  완료 시 생성된 파일 목록 출력
```

## 파일 구조

```
.claude/
├── skills/
│   └── idea-to-docs/
│       └── SKILL.md        # 인터뷰 + 오케스트레이션 로직
└── agents/
    ├── business.md         # 시장 규모, 경쟁사, 수익화 모델
    ├── risk.md             # 기술적/법적/시장 리스크 & 대응
    ├── mvp.md              # Must Have / Should Have / Nice to Have
    ├── prd.md              # 제품 목표, 타겟 유저, 핵심 기능
    ├── user-story.md       # 페르소나, 유저 스토리, 엣지케이스
    ├── wireframe.md        # 화면 목록, 플로우, Mermaid 다이어그램
    ├── tech-spec.md        # 아키텍처, API, DB 스키마, 기술 스택
    └── qa.md               # 주요 기능별 테스트 케이스
outputs/                    # 실행마다 {timestamp}/ 하위 폴더 생성
```

## 에이전트 설계 원칙

- **저장 방식 (방법 B)**: 각 에이전트가 실행 완료 즉시 자신의 결과를 직접 저장. 중간 실패 시 앞 단계 결과 보존됨.
- 오케스트레이터가 실행 시작 시 `outputs/{timestamp}/` 경로를 생성하고 각 에이전트에 전달
- 각 에이전트는 브리프 + 선행 에이전트 결과 + 출력 경로를 컨텍스트로 받음
- 병렬 실행 가능한 쌍: (1+2), (5+6)
- 사용 도구: WebSearch, Read, Write, Bash
- 모든 출력은 한국어

## 참고 문서

- 서브에이전트: https://code.claude.com/docs/en/sub-agents
- 스킬: https://code.claude.com/docs/en/skills
