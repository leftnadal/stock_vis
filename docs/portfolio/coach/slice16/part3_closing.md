# Slice 16 Part 3 종결 — E3 코치 화면 (집중도 분석)

> 슬라이스: Slice 16 (E2~E6 화면 복제)
> 단계: Part 3 (E3, 진입 순서 3/5)
> 베이스: Part 2 종결 `6dd178b`
> 종결 commit: 본 문서 직전 P3-D 커밋
> Part 3 비용: **$0.0095064** (P3-C 1콜) — 누적 Slice 16 $0.0152936 (cap 1.53%)

---

## 0. 한 줄 결과

§3 게이트 통과 (Part 2 base 완화로 E3 신규 필드 0건). E2/E6 패턴을 E3로 복제 + concentration_metrics 자동 도출(HHI/top3/sector_concentration/holding_count) + P3-C 실 round-trip. E3Output 봉투 정합 ✅, ledger 정합 ✅, 회귀 무손실(pytest 759/1·IDENTICAL 31/31·vitest 88→95).

---

## 1. Part 3 KPI 매트릭스 — 5/5 통과

| #  | KPI | 결과 |
|---|---|---|
| P3-K1 | §3 게이트 | E3Output 신규 필드 0건 (commentary_output.py 실측) → §3 작업 없음 ✅ |
| P3-K2 | E3 데이터레이어 | postE3Coach + useE3Coach + MSW(봉투 부합 baseline) 추가 ✅ |
| P3-K3 | E3 화면 | concentration_metrics 자동 도출(HHI/top3/sector_concentration) + 3-상태 ✅ |
| P3-K4 | P3-C 실 round-trip | HTTP 200 + 봉투 정합 ✅, ledger slice="runtime" entry_point="e3" ✅ |
| P3-K5 | 회귀 | pytest 759/1·IDENTICAL 31/31·vitest 88→95·tsc exit 0 ✅ |

---

## 2. §3 게이트 — 패스 (작업 없음)

### 실측 (`commentary_output.py:107-111`)
```python
class E3Output(CommentaryOutputBase):
    """E3 집중도 분석 output."""
    action_items: list[ActionItem] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
```

E3Output 필드 = `summary` / `key_observations` / `confidence` / `action_items` / `risk_flags`. **모두 `CommentaryCardData` base에 존재 (`metrics_table?`는 Part 2에서 optional 완화)**. 신규 필드 0건.

### 결과
- §3 작업 없음 — CommentaryCard 그대로 재사용
- Part 2 base 완화 효과 첫 누락 EP 적용 확인 (E3 = 5번째 EP, 가장 직접적 호환 수혜)

---

## 3. P3-A — E3 데이터레이어

**파일/변경**:
- `frontend/lib/coach/api.ts` — `postE3Coach` 추가
- `frontend/lib/coach/hooks.ts` — `useE3Coach` 추가
- `frontend/__tests__/mocks/handlers.ts` — `defaultE3Response` + `mockE3Success/ValidationError/ServerError`
- `frontend/__tests__/coach/useE3Coach.test.tsx` — happy + error 2건

### 봉투 baseline 충실성
- E3Output 필드만 반환 (metrics_table/quoted_metrics 없음)
- defaultE3Response가 codegen `E3Response` 봉투 형태 부합 → TS strict 자동 보장

### 커밋
`83bf67b` — `feat(s16): E3 데이터레이어 — postE3Coach + useE3Coach + MSW 핸들러 (Part 3 P3-A)`

---

## 4. P3-B — E3 화면

**파일**: `frontend/app/coach/e3/page.tsx` (293줄) + `e3-page.test.tsx` (5건)

### 폼 (E2와 다른 점: concentration_metrics 자동 도출)
- 상단: portfolio_id / preset
- 보유 종목 행: ticker / weight / sector (E2와 동일)
- **자동 도출 (deriveConcentrationMetrics)**:
  ```ts
  hhi = Σ(weight²)                     // Herfindahl-Hirschman Index
  top3_weight = top 3 비중 합
  sector_concentration = max(sector_weight)
  holding_count = ticker 행 수
  ```
- 라이브 미리보기 그리드 (data-testid="concentration-preview") — HHI · Top3 · 섹터 최대 · 종목 수
- E2의 sector_allocation 자동 도출과 동일 패턴

### TS strict 처리
- `ConcentrationMetrics` interface는 index signature 없음 → codegen `Record<string, unknown>`과 직접 호환 안 됨
- `concentration_metrics: { ...concentrationMetrics }` spread로 plain object literal로 변환 → 호환 (1줄)

### 패턴 일관 (E1/E2/E6과 동일)
- `'use client'` + AuthGuard + named export E3CoachContent
- 3-상태 (aria-live=polite + role=alert + aria-busy)
- `fetched_at` 제출 핸들러 내부 호출 (#24)
- holdings의 asset_class/name=null
- API path `/coach/e3/` (#19)
- CommentaryCard 재사용 — E3Output (action_items + risk_flags) 직접 prop 전달

### 테스트 5건
| # | 케이스 | 단언 |
|---|---|---|
| 1 | 빈 상태 | empty-state + concentration-preview (default rows) 동시 |
| 2 | happy | '추천 액션' + 'AAPL 비중 축소' / '리스크' + '단일 종목 집중도 60%' |
| 3 | error | role=alert + 친화 문구, 원시 500/AxiosError 미노출 |
| 4 | a11y | error-state role="alert" |
| 5 | 폼 검증 | portfolio_id 비우면 submit disabled |

### 커밋
`645aa73` — `feat(s16): E3 화면 — app/coach/e3/page.tsx + 화면 테스트 5건 (Part 3 P3-B)`

---

## 5. P3-C — 실 백엔드 round-trip 실증 결과

### 입력
- 엔드포인트: `POST http://127.0.0.1:8000/api/v1/coach/e3/?provider=haiku`
- 페이로드: AAPL 60% + MSFT 25% + NVDA 15% (모두 Tech), concentration_metrics 수동 명시
- 인증: dev admin JWT (Part 1 절차 재사용)

### 결과
| 항목 | 값 |
|------|------|
| HTTP status | 200 |
| 응답 시간 | **17.50s** (E3는 가장 큰 응답 — input/output 1900+ 토큰 양쪽) |
| `output.summary` | "포트폴리오가 극도로 집중된 상태(HHI 0.445, Top3 100%, 섹터 100% Tech)로 Apple 단일 종목 60% 초과 편중이 핵심 위험..." |
| `output.confidence` | "high" |
| `output.key_observations` | 5건 |
| `output.action_items` | 4건 (AAPL 비중 축소·섹터 다각화·종목 확대·역상관성, priority high×3 + medium×1) |
| `output.risk_flags` | 5건 (단일 종목 집중·섹터 편중·HHI 초과·미흡한 구성·경기 위험) |
| `llm_metadata.input_tokens` | 1923 |
| `llm_metadata.output_tokens` | 1992 |
| `llm_metadata.cost_usd` | **0.0095064** |
| `gate_tier` / `preset_id` / `scores` | 응답 미포함 (optional 정상) |
| `metrics_table` / `quoted_metrics` | 응답 미포함 (E3Output 스펙대로) |

### 정합 검증
| 항목 | 결과 |
|------|------|
| 봉투 `{output, llm_metadata}` | ✅ |
| output 필드 (summary/confidence/key_observations/action_items/risk_flags) | ✅ 모두 일치 |
| metrics_table/quoted_metrics 부재 | ✅ (E3Output 스펙대로) |
| codegen `CoachE3Response` shape 일치 | ✅ |
| **#72 EP=E3분 충족** | ✅ |

### ledger 정합 (Step 0-A 효과 일관 적용 확인)
ledger 28행:
```json
{"timestamp": "2026-05-26T05:25:36.722908+00:00", "slice": "runtime", "entry_point": "e3",
 "provider": "anthropic", "model": "claude-haiku-4-5",
 "input_tokens": 1923, "output_tokens": 1992, "cost_usd": 0.0095064, "fallback_from": null}
```
- `slice: "runtime"` ✅
- `entry_point: "e3"` ✅
- E2(26) + E6(27) + E3(28) 모두 동일 정합 패턴 — Step 0-A 일관 적용 3번째 EP 확인

---

## 6. 회귀 매트릭스 (Part 2 종결 대비)

| 트랙 | Part 2 종결 (`6dd178b`) | Part 3 종결 | 변동 |
|------|--------------------------|--------------|------|
| pytest | 759/1 | 759/1 | 0 |
| IDENTICAL | 31/31 | 31/31 | 0 |
| vitest | 19 files / 88 tests | **21 files / 95 tests** | +2 files / +7 tests |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| cost_ledger | 27행 | **28행** | +1 (P3-C 자동) |

---

## 7. 커밋 (Part 3, 3건)

| Commit | 단계 | 의미 |
|---|---|---|
| `83bf67b` | P3-A | feat: E3 데이터레이어 |
| `645aa73` | P3-B | feat: E3 화면 + 5 테스트 (concentration_metrics 자동 도출) |
| (본 커밋) | P3-D | docs: Part 3 closing + ledger 자동 append |

§3 게이트 통과 (작업 없음)이라 §3 커밋 없음 — Part 1/2와 다른 형태.

---

## 8. 부채 변동 (Part 3)

- close: 0건
- 신규: 0건
- #72 EP별 close 진행:
  - E1 ✅ (Slice 15)
  - E2 ✅ (Part 1)
  - E6 ✅ (Part 2)
  - **E3 ✅** (본 종결)
  - E5 / E4 — Part 4~5에서 (4/6 진행)

---

## 9. HALT 발동 이력 (Part 3)

| 시점 | 유형 | 결과 |
|------|------|------|
| 0-2 §3 점검 | §3 게이트 | 신규 필드 0건 → 작업 없이 통과 |
| P3-B tsc | TS strict 호환 | `ConcentrationMetrics` interface ↔ `Record<string, unknown>` 부적합 → spread 1줄로 해소 (HALT 미발동, 즉시 수정) |
| (그 외) | 다른 게이트 미발동 | 회귀/IDENTICAL/봉투 정합 모두 정상 |

---

## 10. Part 4 진입 메모 — E5 ⚠ 특수 케이스

지시서 §부록 진입 순서: E2 ✅ → E6 ✅ → E3 ✅ → **E5 (Part 4)** → E4.

### 본작업
1. api.ts에 `postE5Coach`, hooks.ts에 `useE5Coach`
2. handlers.ts에 defaultE5Response + 3 핸들러
3. `frontend/app/coach/e5/page.tsx` — E5 화면
4. `__tests__/coach/{useE5Coach,e5-page}.test.tsx` ~7건
5. P3-C: E5 실 round-trip (~$0.005-0.02)

### ⚠ E5 특수성 — 사실관계 점검 강화 필수
- **`TimeSeriesContext`** 를 쓰는 유일한 진입점 — input shape이 다른 EP와 크게 다름
- E5Request 필드 (실측 확인):
  - `extraction_targets: list[str]` — 추출 대상 키 list
  - `time_series_context: TimeSeriesContext | None` — 시계열 흐름 (optional)
- E5Output 필드 (실측 commentary_output.py:118):
  - `action_items` ✅ (base 호환)
  - `quoted_metrics` ✅ (base 호환)
  - **§3 게이트 판정: 신규 필드 0건 예상 — Part 2 base 완화 효과 그대로 적용**

### 화면 폼 설계 후보
- 보유 종목 동적 행 (다른 EP와 동일)
- **extraction_targets**: 사용자가 추출 대상 키를 list로 입력 (text input + 콤마 분리 또는 tag 입력)
- **time_series_context (optional)**: 시계열 데이터 입력 UI — Part 4에서 결정

### 누적 비용 진행
| Part | EP | cost |
|------|----|------|
| Part 1 | E2 | $0.0025416 |
| Part 2 | E6 | $0.0032456 |
| Part 3 | E3 | $0.0095064 |
| **누적** | | **$0.0152936** |
| 잔여 (예상) | E5+E4 | $0.010-0.04 |
| 슬라이스 총합 (예상) | | $0.025-0.06 |
| cap $1.00 대비 | | 2.5~6% |
