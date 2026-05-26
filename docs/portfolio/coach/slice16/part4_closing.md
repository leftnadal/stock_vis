# Slice 16 Part 4 종결 — E5 코치 화면 (추출 + 시계열 컨텍스트)

> 슬라이스: Slice 16 (E2~E6 화면 복제)
> 단계: Part 4 (E5, 진입 순서 4/5) ⚠ TimeSeriesContext 특수
> 베이스: Part 3 종결 `98d4e89`
> 종결 commit: 본 문서 직전 P4-D 커밋
> Part 4 비용: **$0.0052552** (P4-C 1콜) — 누적 Slice 16 $0.0205488 (cap 2.05%)

---

## 0. 한 줄 결과

§3 게이트 패스(작업 없음). 안 C 폼(토글+4칸+예시 채우기) 정확 구현 + Decimal string 직렬화 + 예시 오인 방지 처리. P4-C 실 round-trip에서 시계열 컨텍스트가 prompt에 반영돼 LLM이 4분기 변화율 +4.55% 인용 — TimeSeriesContext 운영 첫 실증. 회귀 무손실(pytest 759/1·IDENTICAL 31/31·vitest 95→106).

---

## 1. Part 4 KPI 매트릭스 — 5/5 통과

| #  | KPI | 결과 |
|---|---|---|
| P4-K1 | §3 게이트 | E5Output 신규 필드 0건 (사전 실측) → §3 작업 없음 ✅ |
| P4-K2 | E5 데이터레이어 | postE5Coach + useE5Coach + MSW + `E5TimeSeriesContext` helper ✅ |
| P4-K3 | E5 화면 (안 C) | 토글 + 4칸 + 예시 채우기 + 오인 방지 + string 직렬화 ✅ |
| P4-K4 | P4-C 실 round-trip | HTTP 200 + 봉투 정합 + 시계열 prompt 실증 + ledger entry_point="e5" ✅ |
| P4-K5 | 회귀 | pytest 759/1·IDENTICAL 31/31·vitest 95→106·tsc exit 0 ✅ |

---

## 2. §3 게이트 — 패스 (작업 없음)

E5Output 실측 (`commentary_output.py:118~122`):
```python
class E5Output(CommentaryOutputBase):
    action_items: list[ActionItem] = Field(default_factory=list)
    quoted_metrics: dict[str, Any] = Field(default_factory=dict)
```

필드 = `summary` / `key_observations` / `confidence` / `action_items` / `quoted_metrics` — 모두 `CommentaryCardData` base에 존재 (Part 1·2 일반화+완화 효과). 신규 0건. §3 커밋 없음 (Part 3과 동일 형태).

E3에 이어 **두 번째 자동 호환** — base 일반화 1회 + 완화 1회로 E3·E5 두 EP 호환을 추가 작업 없이 흡수.

---

## 3. P4-A — E5 데이터레이어

**파일/변경**:
- `frontend/lib/coach/types.ts` — `E5TimeSeriesContext = NonNullable<E5Request['time_series_context']>` helper
- `frontend/lib/coach/api.ts` — `postE5Coach`
- `frontend/lib/coach/hooks.ts` — `useE5Coach`
- `frontend/__tests__/mocks/handlers.ts` — `defaultE5Response` (quoted_metrics 키: dividend_yield/sector_diversification/beta/expense_ratio — fixture 정합)
- `frontend/__tests__/coach/useE5Coach.test.tsx` (3건: happy + time_series=null + error)

### TimeSeriesContext helper 근거
codegen이 `time_series_context`를 별도 component로 분리하지 않고 inline (Pydantic↔spectacular bridge의 `_inline_pydantic_refs` 효과). 화면이 nested 객체를 직접 참조하려면 `E5Request['time_series_context']` 인덱스 접근이 매번 필요해 부담 — `NonNullable<>` helper로 1회 정리.

### 커밋
`8fd548b` — `feat(s16): E5 데이터레이어 — postE5Coach + useE5Coach + MSW + E5TimeSeriesContext helper (Part 4 P4-A)`

---

## 4. P4-B — E5 화면 (안 C 정확 구현)

**파일**: `frontend/app/coach/e5/page.tsx` (370줄) + `e5-page.test.tsx` (8건)

### extraction_targets 입력
- 콤마 분리 text input + `parseExtractionTargets` 헬퍼
- 라이브 카운트 ("현재 N개 키 입력됨 → ...") + min_length=1 검증
- aria-describedby로 입력 보조 텍스트 연결

### time_series_context 안 C 구현
| 요소 | 구현 |
|------|------|
| 토글 | checkbox + label, default off |
| off 동작 | `time_series_context: null` 전송 → 서버 "(없음)" 분기 |
| on UI | 4칸 grid: current (필수, 빨간 테두리 invalid) + window_1q/4q/12q (optional) |
| 예시 채우기 | `FIXTURE_TS_EXAMPLE` 상수 (3.45/3.40/3.30/3.15) — 프론트 상수 박음, 런타임 fixture 로드 X |
| 오인 방지 | "예시 데이터입니다 — 실제 값으로 교체하세요" (amber-700) |
| Decimal 직렬화 | `toTimeSeriesPayload` — 모든 값 string 전송 (codegen union의 string 분기) |
| delta_4q_pct | UI 입력칸 없음 — 서버 자동 계산 + 안내 텍스트 |
| current 미입력 | submit disabled + inline `role="alert"` 에러 |

### 화면 테스트 8건
| # | 케이스 | 단언 |
|---|---|---|
| 1 | 빈 상태 | empty-state, CommentaryCard 미렌더 |
| 2 | happy | summary + '추천 액션' + '인용 지표' + 'dividend_yield' |
| 3 | error | role=alert + 친화 문구, 원시 미노출 |
| 4 | extraction_targets 빈 | submit disabled + "현재 0개 키 입력됨" |
| 5 | **토글 off → payload null** | server에서 capturedBody 검증, `{time_series_context: null}` matchObject |
| 6 | **토글 on + current 미입력** | submit disabled + role=alert 에러 ("current 값을 입력") |
| 7 | **예시 버튼** | 4칸 fixture 상수 채움 + 오인 방지 텍스트 + 제출 payload 4칸 모두 string 직렬화 검증 |
| 8 | a11y aria-busy | 로딩 시 true → 응답 후 false |

### 커밋
`179b20f` — `feat(s16): E5 화면 — extraction_targets + time_series_context 토글 폼 (Part 4 P4-B 안 C)`

---

## 5. P4-C — 실 백엔드 round-trip 실증 결과

### 입력 (토글 on 경로 — 시계열 컨텍스트 검증)
- 엔드포인트: `POST http://127.0.0.1:8000/api/v1/coach/e5/?provider=haiku`
- 페이로드: portfolio_a2.json E5 패턴 그대로 — AAPL 50% (Tech) + JNJ 50% (Healthcare),
  extraction_targets 4종, time_series_context (3.45/3.40/3.30/3.15 string)
- 인증: dev admin JWT (Part 1 절차 재사용)

### 결과
| 항목 | 값 |
|------|------|
| HTTP status | 200 |
| 응답 시간 | 9.50s |
| `output.summary` | "배당 수익률 3.45%로 12분기 대비 30bp 상승 추세이며..." |
| `output.confidence` | "high" |
| `output.key_observations` | 5건 |
| `output.action_items` | 3건 (priority medium×2 + low×1) |
| `output.quoted_metrics` | 9개 키 — **dividend_yield_delta_4q: "+4.55% (3.30% → 3.45%)"** 포함 |
| `output.risk_flags` | 응답 미포함 (E5Output 스펙) |
| `output.metrics_table` | 응답 미포함 (E5Output 스펙) |
| `llm_metadata.input_tokens` | 1464 (E3 1923보다 적음 — 폼 단순) |
| `llm_metadata.output_tokens` | 1021 |
| `llm_metadata.cost_usd` | **0.0052552** |

### 시계열 컨텍스트 실증 ⭐
응답의 `quoted_metrics`에 시계열 컨텍스트가 LLM에 의해 인용·해석된 것을 확인:
- `dividend_yield_current: "3.45%"` ← UI 입력 current 그대로
- `dividend_yield_window_1q/4q/12q` — 3개 history 인용
- **`dividend_yield_delta_4q: "+4.55% (3.30% → 3.45%)"`** — `delta_4q_pct` property가 서버에서 자동 계산되어 prompt에 포함된 후 LLM이 활용
- `dividend_yield_12q_improvement: "+30bp (3.15% → 3.45%)"` — LLM이 12분기 흐름 종합

`E5PromptBuilder.build_user_prompt`(`prompt_builder.py:285~325`)의 시계열 블록이 운영에서 정상 작동함을 첫 검증.

### 정합 검증
| 항목 | 결과 |
|------|------|
| 봉투 `{output, llm_metadata}` | ✅ |
| output 필드 (summary/confidence/key_observations/action_items/quoted_metrics) | ✅ |
| risk_flags/metrics_table 부재 | ✅ (E5Output 스펙대로) |
| codegen `CoachE5Response` shape 일치 | ✅ |
| **time_series_context string 직렬화 백엔드 수용** | ✅ (HALT 조건 미발동) |
| **#72 EP=E5분 충족** | ✅ |

### ledger 정합 (Step 0-A 일관 4번째 적용)
ledger 29행:
```json
{"timestamp": "2026-05-26T05:58:26.810943+00:00", "slice": "runtime", "entry_point": "e5",
 "provider": "anthropic", "model": "claude-haiku-4-5",
 "input_tokens": 1464, "output_tokens": 1021, "cost_usd": 0.0052552, "fallback_from": null}
```
- E2(26) + E6(27) + E3(28) + E5(29) — 4 EP 모두 동일 정합 패턴

---

## 6. 회귀 매트릭스 (Part 3 종결 대비)

| 트랙 | Part 3 종결 (`98d4e89`) | Part 4 종결 | 변동 |
|------|--------------------------|--------------|------|
| pytest | 759/1 | 759/1 | 0 |
| IDENTICAL | 31/31 | 31/31 | 0 |
| vitest | 21 files / 95 tests | **23 files / 106 tests** | +2 files / +11 tests |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| cost_ledger | 28행 | **29행** | +1 (P4-C 자동) |

---

## 7. 커밋 (Part 4, 3건)

| Commit | 단계 | 의미 |
|---|---|---|
| `8fd548b` | P4-A | feat: E5 데이터레이어 + E5TimeSeriesContext helper |
| `179b20f` | P4-B | feat: E5 화면 (안 C 토글+4칸+예시 채우기) + 8 테스트 |
| (본 커밋) | P4-D | docs: Part 4 closing + ledger 자동 append |

§3 작업 없어 §3 커밋 부재 — Part 3과 동일 형태.

---

## 8. 부채 변동 (Part 4)

- close: 0건
- 신규: 0건
- #72 EP별 close 진행:
  - E1 ✅ (Slice 15) / E2 ✅ (Part 1) / E6 ✅ (Part 2) / E3 ✅ (Part 3) / **E5 ✅** (본 종결)
  - **E4만 잔여 — 5/6**

---

## 9. HALT 발동 이력 (Part 4)

| 시점 | 유형 | 결과 |
|------|------|------|
| 0-3 §3 게이트 | 사전 실측 결과 신규 필드 0건 — 작업 없이 통과 |
| (그 외) | 다른 게이트 미발동 | 회귀/IDENTICAL/봉투 정합/Decimal 직렬화/시계열 운영 모두 정상 |

---

## 10. Part 5 진입 메모 — E4 ⚠ 대화형 (마지막 진입점)

지시서 §부록 순서: E2 ✅ → E6 ✅ → E3 ✅ → E5 ✅ → **E4 (Part 5, 마지막)**.

### ⚠ E4 특수성 — 폼 UX가 근본적으로 다름
- E4Request 필드 (실측 `commentary_input.py:145~155`):
  - `user_question: str` (min_length=1, max_length=2000) — **현재 사용자 질문**
  - `conversation_history: list[dict[str, Any]]` (default_factory=list) — 이전 대화 turn (role/content)
- E4Output 필드 (실측 `commentary_output.py:114~115`):
  - **base만 사용** (`summary`/`key_observations`/`confidence`) — action_items/risk_flags/quoted_metrics 모두 없음
  - §3 게이트: 신규 필드 0건 예상 ✅

### Part 5 결정 필요 사항 (지시서 별도 작성 예정)
- **대화형 UI 패턴** — 단발 폼이 아닌 채팅 인터페이스 (history 표시 + 새 질문 입력 + send)
- **conversation_history 관리** — 클라이언트 상태로 turn 누적, 제출마다 history 갱신
- **CommentaryCard 적용 방식** — output이 base만이라 표시 영역이 단조로움. 채팅 답변으로 stream/대화 turn 형태 vs CommentaryCard로 표시 — 선택 필요
- **post-Part 5 작업**: Slice 16 closing — #72 일괄 close + "Part 5 후 C 리팩터링 재검토" 후속 후보 정리

### 누적 비용 (Slice 16)
| Part | EP | cost |
|------|----|------|
| Part 1 | E2 | $0.0025416 |
| Part 2 | E6 | $0.0032456 |
| Part 3 | E3 | $0.0095064 |
| Part 4 | E5 | $0.0052552 |
| **누적** | | **$0.0205488** |
| 잔여 (E4 예상) | | $0.005-0.02 |
| 슬라이스 총합 (예상) | | $0.025-0.04 |
| cap $1.00 대비 | | 2.05% |
