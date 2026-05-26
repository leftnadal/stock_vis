# Slice 16 Part 2 종결 — E6 코치 화면 (비교 분석)

> 슬라이스: Slice 16 (E2~E6 화면 복제)
> 단계: Part 2 (E6, 진입 순서 2/5)
> 베이스: Part 1 종결 `8e6f596`
> 종결 commit: 본 문서 직전 P2-D 커밋
> Part 2 비용: **$0.0032456** (P2-C 1콜) — 누적 Slice 16 $0.0057872 (cap 0.58%)

---

## 0. 한 줄 결과

§3 게이트(CommentaryCardData.metrics_table 호환성)를 base 완화 한 줄로 해소 후, E2 패턴을 E6로 복제 + analysis_results 입력 폼 + P3-C 실 round-trip. E6Output 봉투 정합 ✅, ledger 정합 ✅, 회귀 무손실(pytest 759/1·IDENTICAL 31/31·vitest 81→88).

---

## 1. Part 2 KPI 매트릭스 — 5/5 통과

| #  | KPI | 결과 |
|---|---|---|
| P2-K1 | §3 게이트 | base 완화 1줄(`metrics_table?` optional). 신규 필드 없음. E1/E2 회귀 무손 ✅ |
| P2-K2 | E6 데이터레이어 | postE6Coach + useE6Coach + MSW(봉투 부합 baseline) 추가 ✅ |
| P2-K3 | E6 화면 | analysis_results 폼(ticker/weight/sector/score/signal/notes) + 자동 도출 + 3-상태 ✅ |
| P2-K4 | P2-C 실 round-trip | HTTP 200 + 봉투 정합 ✅, ledger slice="runtime" entry_point="e6" ✅ |
| P2-K5 | 회귀 | pytest 759/1·IDENTICAL 31/31·vitest 81→88·tsc exit 0 ✅ |

---

## 2. §3 게이트 — base 완화 (`metrics_table` optional)

### 실측 매트릭스 (`portfolio/schemas/commentary_output.py`)
| Field | E1 | E2 | E3 | E4 | E5 | E6 |
|-------|----|----|----|----|----|----|
| summary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| key_observations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| confidence | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| action_items | ✅ | — | ✅ | — | ✅ | — |
| risk_flags | ✅ | — | ✅ | — | — | ✅ |
| quoted_metrics | — | ✅ | — | — | ✅ | ✅ |
| metrics_table | ✅ | ✅ | — | — | — | — |

### 판정
E6Output에 base에 없는 신규 필드 없음 (모두 합집합 안). 단, **base의 필수 필드 `metrics_table`이 E6에 없음** → TypeScript에서 `E6Response['output']`을 `CommentaryCardData` prop으로 전달 시 필수 누락 거부.

해결: **단순 한 줄 완화** — `CommentaryCardData.metrics_table: string` → `metrics_table?: string`.
- 어차피 deprecated (#21).
- E1/E2는 default ""로 채워 보내므로 optional이어도 무손 (structural compatibility).
- 6 EP 모두 prop 호환 — Part 3~5 E3/E4/E5 동일 케이스도 자동 해소.

### 커밋
`ebb2b1c` — `refactor(s16): CommentaryCardData.metrics_table을 optional로 완화 (Part 2 §3 게이트)`

---

## 3. P2-A — E6 데이터레이어

**파일/변경**:
- `frontend/lib/coach/api.ts` — `postE6Coach` 추가
- `frontend/lib/coach/hooks.ts` — `useE6Coach` 추가
- `frontend/__tests__/mocks/handlers.ts` — `defaultE6Response` + `mockE6Success/ValidationError/ServerError`
- `frontend/__tests__/coach/useE6Coach.test.tsx` — happy + error 2건

### 봉투 baseline (E6Output 특수성)
- E1과 달리 `action_items` 없음
- E2와 달리 `risk_flags` 있음
- E2와 같이 `quoted_metrics` 있음
- `metrics_table` 없음 (§3 게이트 트리거)

### 커밋
`d9cc212` — `feat(s16): E6 데이터레이어 — postE6Coach + useE6Coach + MSW 핸들러 (Part 2 P2-A)`

---

## 4. P2-B — E6 화면

**파일**: `frontend/app/coach/e6/page.tsx` (288줄) + `e6-page.test.tsx` (5건)

### 폼 (E2와 다른 점)
- 보유 종목 동적 행: ticker / weight / sector / **score (number)** / **signal (select: bull/neutral/bear)** / **notes (text)**
- `analysis_results` 자동 도출 (`deriveAnalysisResults`):
  ```ts
  {
    AAPL: { signal: "bull", score: 0.78, notes: "PEG 1.3" },
    NVDA: { signal: "bear", score: 0.42, notes: "단기 과열" }
  }
  ```
  빈 score/notes는 entry에서 제외 (Pydantic free-form dict 호환).

### 패턴 일관 (E1/E2와 동일)
- `'use client'` + AuthGuard + named export E6CoachContent
- 3-상태 (aria-live=polite + role=alert + aria-busy)
- `fetched_at` 제출 핸들러 내부 호출 (#24)
- holdings의 asset_class/name=null
- API path `/coach/e6/` (#19)
- CommentaryCard 재사용 — §3 base 완화 덕에 metrics_table 없는 E6Output 직접 prop 전달, risk_flags + quoted_metrics 섹션 자동 렌더

### 테스트 5건
| # | 케이스 | 단언 |
|---|---|---|
| 1 | 빈 상태 | empty-state, CommentaryCard 미렌더 |
| 2 | happy | '리스크' + 'NVDA 변동성 ↑', '인용 지표' + 'avg_score' |
| 3 | error | role=alert + 친화 문구, 원시 500/AxiosError 미노출 |
| 4 | a11y | error-state role="alert" |
| 5 | 폼 검증 | portfolio_id 비우면 submit disabled |

### 커밋
`e790ce6` — `feat(s16): E6 화면 — app/coach/e6/page.tsx + 화면 테스트 5건 (Part 2 P2-B)`

---

## 5. P2-C — 실 백엔드 round-trip 실증 결과

### 입력
- 엔드포인트: `POST http://127.0.0.1:8000/api/v1/coach/e6/?provider=haiku`
- 페이로드: AAPL (score 0.78, bull) + NVDA (score 0.42, bear)
- 인증: dev admin JWT (Part 1 절차 재사용)

### 결과
| 항목 | 값 |
|------|------|
| HTTP status | 200 |
| 응답 시간 | 6.03s |
| `output.summary` | "애플의 견조한 펀더멘털(PEG 1.3)이 포트폴리오 안정성을 제공하지만, 엔비디아의 과열 신호(RSI 78)로 인한 하방 리스크가 상존하는..." |
| `output.confidence` | "medium" |
| `output.key_observations` | 5건 |
| `output.risk_flags` | 3건 (NVDA 과열, 섹터 집중, 비중 관리) |
| `output.quoted_metrics` | `{AAPL: "score 0.78, PEG 1.3...", NVDA: "score 0.42, RSI 78..."}` |
| `output.metrics_table` | **응답 미포함** (E6Output 스펙 그대로 — §3 게이트 완화 효과 확인) |
| `llm_metadata.input_tokens` | 902 |
| `llm_metadata.output_tokens` | 631 |
| `llm_metadata.cost_usd` | **0.0032456** |
| `gate_tier` / `preset_id` / `scores` | 응답 미포함 (optional 정상) |

### 정합 검증
| 항목 | 결과 |
|------|------|
| 봉투 `{output, llm_metadata}` | ✅ |
| output 필드 (summary/confidence/key_observations/risk_flags/quoted_metrics) | ✅ 모두 일치 |
| metrics_table 부재 | ✅ (E6Output 스펙대로) |
| codegen `CoachE6Response` shape 일치 | ✅ |
| **#72 EP=E6분 충족** | ✅ |

### ledger 정합 (Step 0-A 효과 재확인)
ledger 27행:
```json
{"timestamp": "2026-05-26T05:08:51.264834+00:00", "slice": "runtime", "entry_point": "e6",
 "provider": "anthropic", "model": "claude-haiku-4-5",
 "input_tokens": 902, "output_tokens": 631, "cost_usd": 0.0032456, "fallback_from": null}
```
- `slice: "runtime"` ✅ (Part 1 E2 호출과 동일 패턴)
- `entry_point: "e6"` ✅
- E2 ledger (26행)와 E6 ledger (27행) 모두 정합 — Step 0-A의 #68 close가 6 EP 전체에 일관 적용됨을 확인.

### 인증 (Part 1 절차 재사용 — 정착 확인)
- dev admin JWT 발급(`/api/v1/users/jwt/login/`) + Bearer 헤더
- 401 회피, IsAuthenticated 통과
- Part 3~5에서도 동일 절차로 P3-C(E3/E5/E4) 진행 가능

---

## 6. 회귀 매트릭스 (Part 1 종결 대비)

| 트랙 | Part 1 종결 (`8e6f596`) | Part 2 종결 | 변동 |
|------|--------------------------|--------------|------|
| pytest | 759/1 | 759/1 | 0 |
| IDENTICAL | 31/31 | 31/31 | 0 |
| vitest | 17 files / 81 tests | **19 files / 88 tests** | +2 files / +7 tests |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| cost_ledger | 26행 | **27행** | +1 (P2-C 자동) |

---

## 7. 커밋 (Part 2, 4건)

| Commit | 단계 | 의미 |
|---|---|---|
| `ebb2b1c` | §3 게이트 | refactor: CommentaryCardData.metrics_table optional 완화 |
| `d9cc212` | P2-A | feat: E6 데이터레이어 |
| `e790ce6` | P2-B | feat: E6 화면 + 5 테스트 |
| (본 커밋) | P2-D | docs: Part 2 closing + ledger 자동 append 보존 |

---

## 8. 부채 변동 (Part 2)

- close: 0건
- 신규: 0건
- #72 EP별 close 진행:
  - E1 ✅ (Slice 15 P3-C)
  - E2 ✅ (Slice 16 Part 1 P1-C)
  - **E6 ✅** (본 종결)
  - E3 / E4 / E5 — Part 3~5에서

---

## 9. HALT 발동 이력 (Part 2)

| 시점 | 유형 | 결과 |
|------|------|------|
| 0-2 점검 | §3 게이트 (metrics_table 호환성) | 신규 필드 없음 + 단순 base 완화로 해소 → 별도 커밋(`ebb2b1c`) 후 진행 |
| (그 외) | 다른 게이트 미발동 | tsc/회귀/IDENTICAL/봉투 정합 모두 정상 |

---

## 10. Part 3 진입 메모 — E3

지시서 §부록 진입 순서: E2 ✅ → E6 ✅ → **E3 (Part 3)** → E5 → E4.

### 본작업
1. api.ts에 `postE3Coach`, hooks.ts에 `useE3Coach`
2. handlers.ts에 defaultE3Response + 3 핸들러
3. `frontend/app/coach/e3/page.tsx` — E3 화면 (E2 패턴 복제)
4. `__tests__/coach/{useE3Coach,e3-page}.test.tsx` ~7건
5. P3-C: E3 실 round-trip (~$0.005)

### E3 사실관계 점검 사항
- E3 codegen 타입 (`CoachE3RequestRequest` / `CoachE3Response`) 확인
- E3 Pydantic schema 실측 (E3 = 집중도 분석, `concentration_metrics` 입력)
- E3Output 필드: `summary` / `key_observations` / `confidence` / `action_items` / `risk_flags` (metrics_table 없음, quoted_metrics 없음)
  → **§3 게이트: 신규 필드 0건 예상, base 완화 1회로 끝 → §3 작업 없음 예상**
- e3_service.py `entry_point="e3"` 확인 (Step 0-A에서 추가)

### 누적 비용 진행 (Slice 16)
| Part | EP | cost |
|------|----|------|
| Part 1 | E2 | $0.0025416 |
| Part 2 | E6 | $0.0032456 |
| **누적** | | **$0.0057872** |
| 잔여 (예상) | E3+E5+E4 | $0.015–0.06 |
| 슬라이스 총합 (예상) | | $0.02–0.07 |
| cap $1.00 대비 | | 2~7% |
