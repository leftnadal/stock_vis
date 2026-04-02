# THESIS_CONTROL 가설 빌더 재설계 — 요약서 v4

> 작성일: 2026-03-19 | 상세 설계: 00-design-v4.md | Phase별 PR: 01~04

---

## 한 줄 요약

**사용자가 한 줄 의견을 던지면, AI가 가설 전체를 설계하고, 사용자는 승인만 한다.**

---

## 파일 구조

```
thesis-builder-v4/
├── 00-design-v4.md          ← 전체 설계 (아키텍처, 모델, 원칙)
├── 01-phase-a-mvp.md        ← Spike + PR-1~3 (core flow)
├── 02-phase-a-hardening.md  ← PR-4~7 (안정화)
├── 03-phase-b-keywords.md   ← PR-8~12 (keyword enrichment + monitoring)
├── 04-phase-c-advanced.md   ← C-1~8+ (고급 기능)
└── 05-summary.md            ← 이 파일
```

---

## Phase 로드맵

```
Spike (1일)
  └─ Gemini Playground 검증

Phase A-MVP (2-3일) ← PR-1, PR-2, PR-3
  └─ One-shot proposal → 프리셋 → 등록 (3턴, Gemini 1회)

Phase A-Hardening (2-3일) ← PR-4, PR-5, PR-6, PR-7
  └─ normalize 보강, fallback 안정화, 로그 지표

Phase B (3-5일) ← PR-8, PR-9, PR-10, PR-11, PR-12
  └─ KeywordCache + collector 3개 + hint 빌더 통합 + monitoring

Phase C (이후) ← C-1~8+
  └─ Health Report, keyword 고도화, 멀티턴, 스트리밍
```

---

## PR 목록

| PR    | Phase  | 내용                                                    | 예상 |
| ----- | ------ | ------------------------------------------------------- | ---- |
| —     | Spike  | Gemini Structured Output 검증                           | 1일  |
| PR-1  | A-MVP  | 백엔드 기반 (State, Prompt, Postprocess, Events, Flags) | 4h   |
| PR-2  | A-MVP  | 백엔드 로직 (Engine, Matching, Views)                   | 4h   |
| PR-3  | A-MVP  | 프론트엔드 (Types, Components, Mock)                    | 5h   |
| PR-4  | A-Hard | normalize/validate 보강 (실 로그 기반)                  | 3h   |
| PR-5  | A-Hard | fallback 안정화                                         | 2h   |
| PR-6  | A-Hard | 로그 지표 추출 스크립트                                 | 2h   |
| PR-7  | A-Hard | FE 에러 바운더리                                        | 2h   |
| PR-8  | B      | KeywordCache 모델 + Admin + Cache Ops                   | 3h   |
| PR-9  | B      | News Keyword Collector                                  | 2h   |
| PR-10 | B      | EOD + Chain Collectors                                  | 3h   |
| PR-11 | B      | Keyword Hint 빌더 통합                                  | 3h   |
| PR-12 | B      | 멀티턴 수정 대화 (선택)                                 | 4h   |

---

## 핵심 설계 결정

1. **One-shot Proposal** — Gemini 1회로 가설 전체 생성
2. **normalize → validate → merge** — LLM 출력 신뢰하지 않음
3. **Keyword Hint Enrichment** — source별 구조화 블록 대신 ContextKeyword 단일 인터페이스
4. **KeywordCache + freshness TTL** — DB를 진실의 원천, stale data 코드 레벨 차단
5. **replace-all cache 정책** — 누적 오염 방지
6. **Edit = "다시 만들어줘"** — MVP에서 상태 폭발 방지
7. **source별 경고 기준 차등** — news 0개는 정상, eod 0개는 경고

---

## 모니터링 3계층

```
Layer A. 존재 확인 — keyword_extracted / keyword_extraction_failed
Layer B. 신선도 — source별 TTL cutoff + keyword_stale_or_missing
Layer C. 주입 확인 — proposal_generated에 keywords_injected/by_source/by_role
```

운영 도구: `check_keywords` command + Django Admin

---

## 위험 Top 5

| #   | 위험                | 대응                        |
| --- | ------------------- | --------------------------- |
| 1   | LLM 출력 흔들림     | normalize/validate          |
| 2   | State 직렬화 왕복   | Pydantic model_validate     |
| 3   | Edit Flow 상태 폭발 | "다시 만들어줘" 제한        |
| 4   | Keyword 과해석      | role 그룹핑 + 프롬프트 계약 |
| 5   | Keyword stale/오염  | TTL + replace-all           |
