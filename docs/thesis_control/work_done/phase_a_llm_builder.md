# Phase A: LLM 빌더 구현 완료 보고서

> 작성일: 2026-03-20
> 브랜치: feat/eod-dashboard-and-improvements
> 커밋: `09b0f8b` (MVP), `6d72432` (Hardening)

---

## 1. 개요

기존 wizard형 가설 빌더(6단계 질의응답)에 **LLM one-shot proposal 모드**를 추가.
사용자가 한 줄 입력("삼성전자 반등")만 넣으면 Gemini 2.5 Flash가 가설 전체를 설계하고, 3턴 만에 등록까지 완료.

```
AS-IS: "AI가 묻고, 사용자가 답한다" (6단계 wizard)
TO-BE: "사용자가 의견을 던지고, AI가 설계하고, 사용자가 승인한다" (3턴 제안형)
```

---

## 2. 구현 범위

### Phase A-MVP (PR-1~3)

#### PR-1: 백엔드 기반 구조 (5개 파일 신규)

| 파일 | 역할 |
|------|------|
| `thesis/services/builder_state.py` | Pydantic 상태 모델: ConversationState, BuilderPhase, CollectedData, PremiseData, IndicatorRecommendation, MONITORING_PRESETS |
| `thesis/services/prompt_builder.py` | 시스템 프롬프트 3블록 (base_instruction + type_guide + indicator_block) + `call_gemini()` Structured Output + INDICATOR_CATALOG 11개 |
| `thesis/services/llm_postprocess.py` | normalize → validate → merge 3단계 파이프라인 |
| `thesis/services/builder_events.py` | `log_event()` + 7개 이벤트 상수 (builder_started ~ thesis_created) |
| `thesis/feature_flags.py` | 10개 플래그 + `get_feature_flags()` |

#### PR-2: 백엔드 로직 (3개 파일 수정)

| 파일 | 변경 |
|------|------|
| `thesis/services/thesis_builder.py` | `start_llm_conversation()`, `process_llm_turn()`, `_handle_proposal()` (Gemini 호출), `_handle_preset()` (3개 프리셋 매핑), `_handle_confirm()` (DB 저장), `_fallback_to_wizard()` |
| `thesis/services/indicator_matcher.py` | `match_indicators_for_llm()` — PK 우선 2단계 매칭 (indicator_db_id → CATALOG, text → keyword rules) |
| `thesis/views/conversation_views.py` | mode 감지 (`_detect_mode`), LLM state 검증 (`_sanitize_llm_state`), feature flag 기반 시작점 분기 |

#### PR-3: 프론트엔드 (4개 수정 + 2개 신규)

| 파일 | 변경 |
|------|------|
| `frontend/lib/thesis/types.ts` | `BuilderPhase`, `LLMIndicatorRecommendation` 타입 + ConversationState/Response LLM 확장 |
| `frontend/lib/thesis/conversation.ts` | BuilderState에 mode/phase/confidence/indicatorRecommendations 추가 + `applyResponse` LLM 분기 |
| `frontend/lib/thesis/mock.ts` | LLM 모드 Mock 6개 (시작/proposal/confirm/complete/fallback/step map) |
| `frontend/app/thesis/new/page.tsx` | phase 기반 UI 분기, PresetSelector/IndicatorCard 렌더링, Mock LLM 분기 |
| `frontend/components/thesis/PresetSelector.tsx` | **신규** — 단기(⚡)/중기(📈)/장기(🔭) 프리셋 카드 |
| `frontend/components/thesis/IndicatorCard.tsx` | **신규** — 지표명 + why + signal_type 뱃지(선행/동행/후행) + auto_matched(✅/⚠️) |

### Phase A-Hardening (PR-4~7)

#### PR-4: normalize/validate 보강

- direction 한국어 별칭 매핑 (상승→bullish, 하락→bearish, 대소문자)
- premise title 공백/특수문자 정리, 빈 title 제거
- indicator_db_id CATALOG 미존재 시 null 교정
- confidence 대소문자 정규화
- direction/message 방향 불일치 감지 (키워드 휴리스틱)
- indicator 0개 premise warning 로그

#### PR-5: fallback 안정화

- `_handle_fallback_choice()`: retry → LLM 재시도, wizard → wizard 시작
- fallback 시 LLM state 유지 (retry 가능하도록)
- turn_count > 20 방어 (무한 루프 방지)
- `process_llm_turn`에 fallback phase 핸들링 추가

#### PR-6: builder_stats management command

```bash
python manage.py builder_stats --days 7
```
- confidence 분류, fallback reason, 등록 완료율 추출
- 비정상 지표 경고 (fallback >15%, 완료율 <50%)

#### PR-7: FE 에러 바운더리

- Gemini 2초 이상 지연 시 "AI가 가설을 설계하고 있어요..." 힌트
- conversation_state 파싱 실패 방어
- proposal phase에서 항상 텍스트 입력 표시

---

## 3. 핵심 흐름

```
User: "삼성전자 반등"
  → Turn 1: Gemini One-shot
       → confidence: medium
       → 전제 3개 자동 생성
       → 지표 4개 PK 매칭 (100%)
       → phase: PROPOSAL → PRESET
  → Turn 2: 프리셋 선택 (⚡단기 / 📈중기 / 🔭장기)
       → timeframe/magnitude/sensitivity 자동 설정
       → phase: PRESET → CONFIRM
  → Turn 3: "등록" 확인
       → Thesis + Premise + Indicator DB 저장
       → HypothesisEvent 기록
       → phase: CONFIRM → COMPLETE
```

---

## 4. Spike 결과 (Gemini Structured Output 검증)

| 항목 | 결과 | 목표 |
|------|------|------|
| 성공률 | 6/6 (100%) | — |
| indicator_db_id 매칭 | 9/9 (100%) | 70%+ |
| 평균 응답 시간 | 2.7초 | 2초 |
| confidence 분류 | 적절 | — |

### 시나리오별

| 입력 | confidence | 결과 |
|------|-----------|------|
| "삼성전자 반등" | medium | 전제 3개, 지표 4/4 매칭 |
| "나스닥 하락" | low | 구체화 질문 (정상) |
| "원화 약세" | medium | 전제 3개, 지표 5/5 매칭 |
| "비만치료제" | low | 구체화 질문 (정상) |
| "금리 인하" | low | 구체화 질문 (정상) |
| "주식" | low | 극도 모호, 가이드 (정상) |

---

## 5. 실 연동 E2E 결과

```
POST /conversation/start/ → LLM 모드 시작 (즉시)
POST /conversation/respond/ "삼성전자 반등" → Gemini (3.7초) → phase: preset
POST /conversation/respond/ "medium" → phase: confirm (즉시)
POST /conversation/respond/ "confirm" → DB 저장 (즉시) → thesis_id: 9fef58dd-...
```

DB 검증:
- Thesis: "삼성전자 실적 개선 및 수급 개선에 따른 주가 반등" (bullish, active)
- Premises: 3개 (반도체 업황, 외국인/기관 순매수, KOSPI 동반)
- Indicators: 4개 (EPS, 외국인 순매수, 기관 순매수, KOSPI — 전부 FMP)
- Event: thesis_created (mode: llm)

---

## 6. 테스트

| 구분 | 수 | 상태 |
|------|-----|------|
| 기존 thesis 단위 테스트 | 39 | ✅ 전부 통과 |
| 신규 LLM 빌더 테스트 (MVP) | 50 | ✅ |
| 신규 Hardening 테스트 | 15 | ✅ |
| **전체** | **104** | ✅ |
| TypeScript 타입 검사 | — | ✅ 에러 없음 |
| 브라우저 Mock 테스트 | — | ✅ 3턴 완료 |
| 브라우저 실 연동 테스트 | — | ✅ DB 저장 확인 |

---

## 7. 파일 목록 (총 22개 변경/생성)

### 신규 생성 (12개)
```
thesis/services/builder_state.py
thesis/services/prompt_builder.py
thesis/services/llm_postprocess.py
thesis/services/builder_events.py
thesis/feature_flags.py
thesis/management/__init__.py
thesis/management/commands/__init__.py
thesis/management/commands/builder_stats.py
frontend/components/thesis/PresetSelector.tsx
frontend/components/thesis/IndicatorCard.tsx
tests/unit/thesis/test_llm_builder.py
```

### 수정 (10개)
```
thesis/services/thesis_builder.py (+419 lines)
thesis/services/indicator_matcher.py (+58 lines)
thesis/views/conversation_views.py (+103 lines)
frontend/lib/thesis/types.ts (+32 lines)
frontend/lib/thesis/conversation.ts (+43 lines)
frontend/lib/thesis/mock.ts (+151 lines)
frontend/app/thesis/new/page.tsx (+60 lines)
```

---

## 8. 다음 단계

- **Phase B**: Keyword Hint Enrichment (KeywordCache + news/eod/chain collectors + 빌더 통합) — 구현 완료
- **Phase C**: 고급 기능 (MiniDashboard, Guided Suggestion, 스트리밍)
