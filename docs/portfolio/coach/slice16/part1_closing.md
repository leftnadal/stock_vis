# Slice 16 Part 1 종결 — E2 코치 화면 (E1 패턴 복제)

> 슬라이스: Slice 16 (E2~E6 화면 복제)
> 단계: Part 1 (E2)
> 베이스: Step 0 종결 `b6f3e51`
> 종결 commit: 본 문서 직전 P1-D 커밋
> Part 1 비용: **$0.0025416** (P1-C 1콜) — 누적 cap $1.00 대비 0.25%

---

## 0. 한 줄 결과

§3 게이트(CommentaryCard 호환성)를 사용자 안 A로 해소(공통 base 일반화) 후, E1 패턴을 E2로 기계적 복제 + P3-C 실 round-trip 1회 실증. 회귀 무손실(pytest 759/1·IDENTICAL 31/31·vitest 74→81). Step 0-A의 ledger 정합(slice="runtime", entry_point="e2") 첫 운영 실증 — #68 close 효과 확인.

---

## 1. Part 1 KPI 매트릭스 — 5/5 통과

| #  | KPI | 기준 | 결과 |
|---|---|---|---|
| P1-K1 | §3 게이트 해소 | CommentaryCard E2 수용 + E1 회귀 무손 | A안 채택, CommentaryCardData 공통 base 신설, vitest 15/74 유지 ✅ |
| P1-K2 | E2 데이터레이어 | postE2Coach + useE2Coach + MSW 핸들러 (봉투 부합) | 4 파일 +173 / -6, useE2Coach 2건 PASS ✅ |
| P1-K3 | E2 화면 | 라우트 + 폼 + CommentaryCard 재사용 + 3-상태 | page.tsx 257줄, 5건 PASS (빈/happy/error + a11y/form) ✅ |
| P1-K4 | P1-C 실 round-trip | HTTP 200 + 봉투 정합 + ledger 정합 (#68 close 실증) | $0.0025416, ledger entry slice="runtime"+entry_point="e2" ✅ |
| P1-K5 | 회귀 | pytest 759/1·IDENTICAL 31/31·vitest 74→81·tsc exit 0 | 모두 PASS ✅ |

---

## 2. §3 게이트 — CommentaryCard 공통 base 일반화 (사용자 안 A)

### 발견
P1 0-2 사실관계 점검에서 `CommentaryCard` prop 타입이 `E1Response['output']`로 lock돼 E2 output을 받지 못함을 발견. E1Output에는 `action_items`/`risk_flags`, E2Output에는 `quoted_metrics`로 분기.

### 해소 (사용자 안 A 확정)
- `frontend/lib/coach/types.ts`에 `CommentaryCardData` interface 신설 (6 진입점 output 필드 합집합).
- enum 타입 `CommentaryConfidence`/`CommentaryActionPriority`/`CommentaryActionCategory` + `CommentaryActionItem` interface 신설.
- `CommentaryCard.tsx` prop 타입을 `CommentaryCardData`로 변경.
- `quoted_metrics` 섹션 신규 추가 (BarChart3 + `<dl>` key-value 표) — graceful 미렌더 (빈 dict면 섹션 자체 미렌더).
- E1 회귀: structural compatibility로 기존 데이터 그대로 작동, vitest 15/74 무손실.

### 후속 검토
**Slice 16 closing 등록 후보**: Part 5 후 C 리팩터링 재검토 — BaseCard + EP별 Section 컴포넌트 분리 (현재 단일 컴포넌트가 ~150줄, 6 EP 추가 후 성장 시 재평가).

### 커밋
`64acaf0` — `refactor(s16): CommentaryCard prop을 공통 base CommentaryCardData로 일반화 (Part 1 §3 게이트 A안)`

---

## 3. P1-A — E2 데이터레이어

**파일/변경**:
- `frontend/lib/coach/api.ts` — `postE2Coach` 추가 (+11줄)
- `frontend/lib/coach/hooks.ts` — `useE2Coach` 추가 (+11줄)
- `frontend/__tests__/mocks/handlers.ts` — `defaultE2Response`/`mockE2Success`/`mockE2ValidationError`/`mockE2ServerError` (+65줄)
- `frontend/__tests__/coach/useE2Coach.test.tsx` — happy + error 2건

### 핵심
- E1 패턴 정확 복제 (useMutation, 봉투 응답, AxiosError narrowing)
- `defaultE2Response`는 codegen `E2Response` 봉투 형태 부합 (quoted_metrics 포함, TS strict 통과로 mock 충실성 자동 보장)

### 커밋
`90e20c1` — `feat(s16): E2 데이터레이어 — postE2Coach + useE2Coach + MSW 핸들러 (Part 1 P1-A)`

---

## 4. P1-B — E2 화면

**파일**:
- `frontend/app/coach/e2/page.tsx` (257줄) — `E2CoachPage` (default, AuthGuard) + `E2CoachContent` (named export, 테스트 진입)
- `frontend/__tests__/coach/e2-page.test.tsx` (5건)

### 폼 입력
- 상단: portfolio_id (text) / preset (select 5) / **portfolio_return_1y (number, %)** — E1과 다른 1줄
- 보유 종목 동적 행: ticker / weight / **sector** (E1의 EPS growth/PE/PEG와 다름)
- **sector_allocation은 자동 도출** — holdings(sector, weight)에서 합산, 비어있으면 "Unknown" 버킷, 폼 하단에 라이브 미리보기

### E1 패턴 정확 복제
- `'use client'` + AuthGuard + named export E2CoachContent
- 3-상태 (aria-live=polite + role=alert + aria-busy)
- `fetched_at`은 제출 핸들러 내부에서 `new Date().toISOString()` (#24 회피)
- holdings의 asset_class/name=null 자동 채움
- API path `/coach/e2/` (#19 회피)
- CommentaryCard 재사용 — §3 일반화 덕분에 `data.output` (E2Output) 직접 prop 전달 → quoted_metrics 섹션 자동 렌더

### 화면 테스트 5건
| # | 케이스 | 검증 |
|---|---|---|
| 1 | 빈 상태 | empty-state 노출, CommentaryCard 미렌더 |
| 2 | happy-path | summary + 인용 지표 헤더 + tech_weight 키 표시 |
| 3 | error-path | role=alert + 친화적 문구, 원시 500/AxiosError 미노출 |
| 4 | a11y | error-state에 role="alert" |
| 5 | 폼 검증 | portfolio_id 비우면 submit disabled, mutate 미트리거 |

### 커밋
`ba596f7` — `feat(s16): E2 화면 — app/coach/e2/page.tsx + 화면 테스트 5건 (Part 1 P1-B)`

---

## 5. P1-C — 실 백엔드 round-trip 실증 결과

### 입력
- 엔드포인트: `POST http://127.0.0.1:8000/api/v1/coach/e2/?provider=haiku`
- 페이로드: AAPL 50% (Tech) + JNJ 50% (Healthcare), portfolio_return_1y=12.5%
- 인증: **dev admin JWT (Bearer)** — `/api/v1/users/jwt/login/` 발급. #70 close로 인증 필수 — 첫 운영 실증.

### 결과
| 항목 | 값 |
|------|------|
| HTTP status | 200 |
| 응답 시간 | 4.95s |
| `output.summary` | "GARP 프리셋의 AAPL·JNJ 균형 포트폴리오가 1년간 12.50% 수익률을 달성하며..." |
| `output.confidence` | "high" |
| `output.key_observations` | 5건 (섹터 균형, 1년 수익률, 집중 위험 등) |
| `output.quoted_metrics` | `{return_1y:"12.50%", top_sector_1:"Tech 50%", top_sector_2:"Healthcare 50%", holding_count:"2", concentration_risk:"Very High"}` |
| `output.metrics_table` | "" |
| `llm_metadata.provider` | "anthropic" |
| `llm_metadata.model` | "claude-haiku-4-5" |
| `llm_metadata.input_tokens` | 852 |
| `llm_metadata.output_tokens` | 465 |
| `llm_metadata.cost_usd` | **0.0025416** |
| `gate_tier` / `preset_id` / `scores` | 응답 미포함 (optional 정상) |

### 정합 검증
| 항목 | 결과 |
|------|------|
| 봉투 형태 `{output, llm_metadata}` | ✅ |
| output 필드 (summary/confidence/key_observations/quoted_metrics/metrics_table) | ✅ 모두 일치 |
| llm_metadata free-form object | ✅ |
| codegen `CoachE2Response` shape 일치 | ✅ (TS 타입 정의 그대로) |
| optional 필드 미포함 시 정합 | ✅ |
| **#72 EP=E2분 충족** | ✅ (closing 일괄 close는 Slice 16 closing에서) |

### **#68 close 첫 운영 실증** ⭐
ledger 행:
```json
{"timestamp": "2026-05-26T04:07:58.196401+00:00", "slice": "runtime", "entry_point": "e2",
 "provider": "anthropic", "model": "claude-haiku-4-5",
 "input_tokens": 852, "output_tokens": 465, "cost_usd": 0.0025416, "fallback_from": null}
```
- `slice: "runtime"` — Step 0-A의 default_factory 채택 (기존 "default" 부정합 차단) ✅
- `entry_point: "e2"` — Step 0-A의 caller 명시 전달 (기존 null 부정합 차단) ✅
- source 컬럼 없음 — 자동 append 행임을 의미 (Slice 15 P3-C의 manual_backfill과 구분)

### 인증 (#70 close 첫 운영 실증)
- dev admin (pk=1, is_superuser=True) JWT 발급 — `/api/v1/users/jwt/login/`
- Authorization: Bearer 헤더로 401 회피, IsAuthenticated 통과
- 절차 (Part 2~5 재사용 가능):
  ```bash
  curl -X POST http://127.0.0.1:8000/api/v1/users/jwt/login/ \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"stock_vis123"}'  # → access token
  curl -X POST "http://127.0.0.1:8000/api/v1/coach/eN/?provider=haiku" \
    -H "Authorization: Bearer <ACCESS>" \
    -H "Content-Type: application/json" \
    --data @payload.json
  ```

---

## 6. 회귀 매트릭스 (Step 0 종결 대비)

| 트랙 | Step 0 종결 (`b6f3e51`) | Part 1 종결 | 변동 |
|------|--------------------------|--------------|------|
| pytest | 759/1 | 759/1 | 0 |
| IDENTICAL | 31/31 | 31/31 | 0 |
| vitest | 15 files / 74 tests | **17 files / 81 tests** | +2 files / +7 tests |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| cost_ledger | 25행 | **26행** | +1 (P3-C 자동 append) |

---

## 7. 커밋 (Part 1, 4건)

| Commit | 단계 | 의미 |
|---|---|---|
| `64acaf0` | §3 게이트 A | refactor: CommentaryCardData 공통 base 일반화 |
| `90e20c1` | P1-A | feat: E2 데이터레이어 |
| `ba596f7` | P1-B | feat: E2 화면 + 5 테스트 |
| (본 커밋) | P1-D | docs+chore: part1_closing + ledger 자동 append 보존 |

---

## 8. 부채 변동 (Part 1)

- close: 0건 (Step 0에서 #68/#70 동시 close됨, Part 1은 그 close 효과를 실증)
- 신규: 0건
- 후속 검토 등록: **Part 5 후 C 리팩터링 재검토** (CommentaryCard BaseCard + Section 분리)

#72 EP별 close 진행 상황:
- E1 (Slice 15 P3-C): ✅
- **E2 (Part 1 P1-C): ✅** (본 종결)
- E3/E4/E5/E6: Part 2~5에서

---

## 9. HALT 발동 이력 (Part 1)

| 시점 | 유형 | 결과 |
|------|------|------|
| 0-2 점검 | §3 게이트 (CommentaryCard 호환성) | 사용자 안 A 확정 → CommentaryCardData 일반화 별도 커밋(`64acaf0`)으로 분리 후 진행 |
| (그 외) | 다른 게이트 미발동 | tsc/회귀/IDENTICAL/봉투 정합 모두 정상 |

---

## 10. Part 2 진입 메모 — E6

지시서 §부록 진입 순서: **E2 → E6 → E3 → E5 → E4**.

### 본작업
1. `frontend/lib/coach/api.ts` — `postE6Coach` 추가
2. `frontend/lib/coach/hooks.ts` — `useE6Coach` 추가
3. `frontend/__tests__/mocks/handlers.ts` — defaultE6Response + 3 핸들러
4. `frontend/app/coach/e6/page.tsx` — E6 화면 (E2 패턴 복제 — E6Request shape: `analysis_results`)
5. `frontend/__tests__/coach/{useE6Coach,e6-page}.test.tsx` — 데이터/화면 테스트
6. P3-C: E6 실 round-trip 1회 — #72 EP=E6분 close

### E6 사실관계 점검 사항 (지시서 0-2 패턴)
- E6 codegen 타입 존재 확인 (`CoachE6RequestRequest` / `CoachE6Response` 봉투)
- E6 Pydantic input/output schema 실측 (`portfolio/schemas/commentary_input.py` E6, `commentary_output.py` E6Output)
- `e6_service.py`의 `entry_point="e6"` 확인 (Step 0-A에서 추가됨)
- CommentaryCard 수용 가능성 — Part 1 §3 일반화로 자동 수용 예상, 단 E6Output 필드 합집합에 새 필드 있으면 본 게이트 재발동 → CommentaryCardData 확장 후 진행

### 누적 비용 (Slice 16)
- Part 1까지: **$0.0025416** (cap $1.00 대비 0.25%)
- Part 2~5 예상: 각 $0.005-0.02 × 4 ≈ $0.02-0.08
- 슬라이스 총합 예상: $0.025-0.10 (cap 내 충분)
