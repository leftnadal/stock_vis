# Slice 16 종결 보고서 — 6 코치 화면(E1~E6) 전건 완성

> 슬라이스: Slice 16 (E2~E6 화면 복제 — Slice 15 E1 패턴 위에)
> 베이스: slice15 closing `cf37855`
> 종결 commit: 본 문서 직전 P5-D 커밋
> 누적 LLM 지출: **$0.0254128** (cap $1.00 대비 2.54%)
> 누적 commit: **20** (Step 0 3건 + Part 1 4건 + Part 2 4건 + Part 3 3건 + Part 4 3건 + Part 5 3건)

---

## 1줄 요약

E1 화면 파일럿(Slice 15) 위에 E2~E6 5 화면을 복제 + E4 대화형 안 C(dialog bubble) 신규 정립으로 **6 코치 화면 전건 완성**. CommentaryCardData base 일반화 1회 + 완화 1회로 E3·E5·E4 3 EP §3 작업을 모두 흡수. E5(TimeSeriesContext) / E4(멀티턴 맥락) 운영 첫 실증. 부채 5→2 순감, 회귀 무손실(pytest 3172/52, vitest 25 files / 115 tests, tsc exit 0).

---

## 핵심 수치

| 항목 | 값 |
|------|-----|
| 누적 commit | 20 |
| 누적 LLM 비용 | $0.0254128 (cap 2.54%) |
| 회귀 시작 (Step 0 진입 전) | pytest 742, vitest 15 files / 74 tests |
| 회귀 종결 (Part 5) | pytest 3172 / 52 skipped, vitest **25 files / 115 tests** |
| pytest 증분 (슬라이스 신규) | +17 (Step 0에서만, Part 1~5는 frontend 위주) |
| vitest 증분 | +10 files / +41 tests |
| tsc --noEmit | exit 0 (전 구간 유지) |
| IDENTICAL 회귀 | 31/31 (전 구간 유지) |
| cost_ledger entry | +6 (E2/E6/E3/E5/E4 1턴/E4 2턴) |

---

## 단계별 매트릭스

| 단계 | 커밋 수 | LLM 비용 | 회귀 변동 | 핵심 |
|------|--------|---------|----------|------|
| Step 0 (부채 정리 + KPI) | 3 | $0 | pytest 742→759 (+17), vitest 74 무손실 | #68 ledger 정합 + #70 AllowAny→IsAuth + ledger 1행 backfill |
| Part 1 (E2 + §3 일반화) | 4 | $0.0025416 | vitest 74→85 (+11), pytest 759 | §3 안 A — CommentaryCardData 일반화 + E2 화면 + 5 테스트 |
| Part 2 (E6 + §3 완화) | 4 | $0.0032456 | vitest 85→90 (+5), pytest 759 | §3 metrics_table optional 완화 (#21 후속) + E6 화면 |
| Part 3 (E3) | 3 | $0.0095064 | vitest 90→95 (+5), pytest 759 | §3 자동 호환 1번째 — concentration_metrics 자동 도출 |
| Part 4 (E5) | 3 | $0.0052552 | vitest 95→106 (+11), pytest 759 | TimeSeriesContext 운영 첫 실증, 안 C(토글+예시) |
| Part 5 (E4) | 3 | $0.0048640 | vitest 106→115 (+9), pytest 3172 | E4Turn 계약 신규 + 멀티턴 맥락 실증 ⭐ |

---

## 6 코치 화면 매트릭스 (Slice 16 완성)

| EP | 화면 위치 | 데이터레이어 | 화면 UX | 특수 처리 | 테스트 |
|----|-----------|-------------|---------|----------|--------|
| E1 | (Slice 15 파일럿) | (기존) | CommentaryCard | - | (기존) |
| E2 | `app/coach/e2/page.tsx` | postE2Coach / useE2Coach | CommentaryCard (quoted_metrics) | base 일반화 1회 효과 | 5건 |
| E3 | `app/coach/e3/page.tsx` | postE3Coach / useE3Coach | CommentaryCard (action_items + risk_flags) | base 자동 호환 | 5건 |
| E4 | `app/coach/e4/page.tsx` | postE4Coach / useE4Coach | **E4MessageBubble (말풍선)** | **E4Turn 계약 + 멀티턴 useState** | 6건 |
| E5 | `app/coach/e5/page.tsx` | postE5Coach / useE5Coach | CommentaryCard + 안 C 폼 (토글+4칸+예시) | **TimeSeriesContext string 직렬화** | 8건 |
| E6 | `app/coach/e6/page.tsx` | postE6Coach / useE6Coach | CommentaryCard (risk_flags) | base 완화 효과 | 5건 |

**§3 게이트 호환 효과**: 1회 일반화(Part 1) + 1회 완화(Part 2)로 **E3 / E5 / E4** 3 EP가 §3 작업 0건으로 흡수. base 합집합 + graceful 미렌더 패턴이 매우 강력.

---

## E4 안 C 의도적 분기 (§3 노트)

E4만 CommentaryCard 미사용하고 E4MessageBubble로 분기 — **의도적 결정**이지 정합 위반이 아님:
- **표현은 분기** (말풍선 vs 카드) — 대화 UX 요구에 맞춘 표현
- **데이터 계약은 정합** — E4Output base 필드(summary / key_observations / confidence)는 CommentaryCardData 합집합에 모두 존재
- 향후 통일 시도 금지 — 대화형 UX는 카드형과 본질적으로 다른 패턴

후속 검토 (C 리팩터링) 시: E4MessageBubble을 **BaseCard + EP별 Section** 구조의 출발점으로 활용. E4는 이미 전용 렌더러 보유 → CommentaryCard를 BaseCard로 분해할 때 자연스러운 templat 으로 사용.

---

## 운영 실증 (Slice 16 신규)

### TimeSeriesContext 운영 첫 실증 (Part 4)
- 입력 시계열(3.45/3.40/3.30/3.15 string) → 백엔드 Decimal 안전 수용 → prompt 주입 → LLM이 `dividend_yield_delta_4q: "+4.55% (3.30% → 3.45%)"` 자동 인용
- `E5PromptBuilder.build_user_prompt`의 시계열 블록 정상 작동 첫 검증

### 멀티턴 맥락 인식 운영 첫 실증 (Part 5) ⭐
- 1턴: "기술주 75% 편중" 분석 → 2턴: 그 결과를 정확히 참조하여 "AAPL과 MSFT 중 비중이 높은 종목 조정 검토" 답변
- 2턴 observation #3에 "기술주 75% 편중 상태에서"로 명시 참조 — 멀티턴 prompt 주입 (`E4PromptBuilder` json dump) 정상 작동 확인
- input token 증가 비용: 1턴 732 → 2턴 853 (+121, history 추가분)

### #68 운영 첫 실증 (Part 1)
- ledger entry_point="e2" + slice="runtime" 정합 첫 운영 확인 (Step 0-A 변경의 첫 실증)

---

## 부채 변동 (Slice 16 전체)

### 진입 시점 (Step 0 진입 전)
- 부채 +3 신규: #68 (ledger 정합) / #70 (AllowAny) / #71 (외부 자동화) / #72 (E2~E6 화면 5건)

### close 5건
| # | 사유 | 단계 |
|---|------|------|
| #68 | ledger entry_point + slice_id 정합 (CostGuard 기본값 + 6 service entry_point literal) | Step 0-A |
| #70 | coach view 6건 AllowAny → IsAuthenticated 일괄 전환 | Step 0-B |
| #72 (EP=E2) | Part 1 P1-C 실 round-trip 200 | Part 1 |
| #72 (EP=E6) | Part 2 P2-C 실 round-trip 200 | Part 2 |
| #72 (EP=E3) | Part 3 P3-C 실 round-trip 200 | Part 3 |
| #72 (EP=E5) | Part 4 P4-C 실 round-trip 200 | Part 4 |
| #72 (EP=E4) | Part 5 P5-C 실 round-trip 2턴 모두 200 | Part 5 |
| **#72 (자체)** | **6/6 EP 전건 close** | **본 종결** |

### 신규 0건

### 잔여
- #71 (외부 자동화) — Slice 16 전 구간 무재발. **해소 의견** 기록 (강제 close는 보류, 외부 트리거 모니터링 1슬라이스 더 필요).

### 부채 순감
- 시작 +3 → close 5 + #72 자체 close → **net −3** (전체 잔여 부채는 #71 1건만, 의견은 "해소").

---

## 후속 후보 (Slice 17+ 검토)

### a) C 리팩터링 — CommentaryCard → BaseCard + EP별 Section
**우선순위 ⭐ (Part 5 후속 후보 1순위)**
- 현재 CommentaryCard는 5 EP(E1/E2/E3/E5/E6) output 합집합을 graceful 미렌더로 처리하지만, EP가 늘어날수록 prop 합집합이 비대해질 위험
- 출발점: **E4MessageBubble** — 이미 전용 렌더러로 분리되어 있음. BaseCard 추출 시 E4MessageBubble과 EP별 Section의 자연 모델 제공
- 효과 가설: 각 EP가 자기 화면에 맞는 Section만 import → 합집합 prop 소멸, 타입 안전성 ↑

### b) E4 대화 영속화 — zustand 승격 검토
- 현재: 화면 로컬 useState (§0 의도적 선택)
- 검토 시점: 페이지 전환 시 대화 보존 필요 / 다중 portfolio 대화 동시 진행 / 대화 export 필요 등 요구 발생 시
- 승격 비용: 현재 ChatMessage[] 모델 그대로 store로 이전 가능, toTurns helper 재사용

### c) 진입점별 응답 지연 편차 — 로딩 UX 검토 입력값
| EP | 응답 시간 (실측) |
|----|------------------|
| E4 (1턴) | 4.73s |
| E4 (2턴) | 5.14s |
| E5 | 9.50s |
| E3 | (~30s — history) |
| E2 / E6 | (~10s — history) |

→ EP별 로딩 UX 차별화 검토 가치. E3는 특히 긴 응답 시간(폼 복잡도 영향)으로 별도 진행률 인디케이터 필요할 수 있음.

### d) #71 해소 처리 절차 — 외부 자동화 모니터링
- Slice 16 전 구간 무재발 — 1슬라이스 더 무재발 확인 후 강제 close 검토
- 모니터링 트리거: 야간 자동화 충돌 발생 시 즉시 트래킹

---

## 아키텍처 패턴 (Slice 16 정착)

### 데이터 → 화면 분리 (5 EP 일관)
```
codegen 타입 (api-types.ts) ← schema.yml (drf-spectacular)
        ↓ alias
types.ts (E*Request/E*Response + 도메인 helper)
        ↓
api.ts (post*Coach) ──→ authAxios (JWT)
        ↓
hooks.ts (use*Coach, useMutation)
        ↓
app/coach/eN/page.tsx (E*CoachContent)
        ↓
components/coach/CommentaryCard | E4MessageBubble
```

### MSW 핸들러 패턴 (5 EP 일관)
- defaultE*Response (codegen 봉투 정확 반영)
- mockE*Success(custom?) — output/llm_metadata 부분 override 지원
- mockE*ValidationError / mockE*ServerError
- 기본 handlers 배열에 6 EP 전건 등록

### §3 게이트 처리 패턴 (3 형태)
- **A 일반화** (Part 1): output 합집합 타입 + graceful 미렌더 → prop 일반화로 5 EP 흡수
- **B 완화** (Part 2): 특정 필드를 required → optional 완화 → 신규 EP 자동 호환
- **C 자동 호환** (Part 3/4/5): 기존 합집합 + 완화에 모든 필드 흡수 → §3 작업 0건

### 안 C 폼 패턴 (E5 정착, E4 응용)
- E5: extraction_targets 토글 + 4칸 + 예시 채우기 + Decimal string 직렬화 + 오인 방지
- E4: dialog bubble + useState 누적 + Turn 계약 + a11y aria-live

---

## 회귀 매트릭스 (전 구간)

| 단계 | pytest | vitest files | vitest tests | tsc | cost ledger |
|------|--------|--------------|--------------|-----|-------------|
| Step 0 시작 (slice15 cf37855) | 742 | 15 | 74 | exit 0 | 24 |
| Step 0 종결 (#68/#70 close) | 759 | 15 | 74 | exit 0 | 25 (+1 backfill) |
| Part 1 종결 (E2) | 759 | 17 | 85 | exit 0 | 26 (P1-C auto) |
| Part 2 종결 (E6) | 759 | 19 | 90 | exit 0 | 27 (P2-C auto) |
| Part 3 종결 (E3) | 759 | 21 | 95 | exit 0 | 28 (P3-C auto) |
| Part 4 종결 (E5) | 759 | 23 | 106 | exit 0 | 29 (P4-C auto) |
| **Part 5 종결 (E4)** | **3172** | **25** | **115** | **exit 0** | **31 (P5-C auto ×2)** |
| 슬라이스 전체 변동 | +17 (Step 0) / 0 (Part 1~5) | +10 | +41 | 0 | +6 entries |

> 표의 pytest 759는 portfolio 코치 스코프 별도 측정값(Part 4까지 기록 형식). Part 5 종결의 3172는 전체 `pytest -q` 측정값 — 둘 다 회귀 0.

---

## 누적 비용 분포

```
Part 3 (E3, $0.0095064) ████████████████████████████████████ 37.4%
Part 4 (E5, $0.0052552) █████████████████████ 20.7%
Part 5 (E4 ×2, $0.0048640) ████████████████████ 19.1%
Part 2 (E6, $0.0032456) █████████████ 12.8%
Part 1 (E2, $0.0025416) ██████████ 10.0%
                        ──────────
                        $0.0254128 (cap 2.54%)
```

- E3가 가장 비싼 이유: history 토큰(1923 input + 1992 output) — 폼 복잡도 영향
- E2/E6/E4(1턴)는 700~900 input token 수준으로 매우 저렴
- 멀티턴 추가 비용은 +121 input token (E4 2턴 - 1턴) — history는 conservatve summary content로 잘 통제됨

---

## 핵심 학습 (Slice 16)

### 1. base 일반화 + graceful 미렌더의 비용 효율
1회 일반화 + 1회 완화 작업으로 3 EP를 §3 작업 0건으로 흡수. 합집합 타입 + optional + graceful 미렌더 패턴은 **타입 안전성과 확장성 모두 만족**.

### 2. E4Turn 계약 — 도메인-프론트 계약은 프론트 책임
백엔드 `list[dict[str, Any]]`는 형태 자유. 프론트가 `{role, content}` 표준을 정립하고 assistant content=summary 1:1 매핑으로 멀티턴 토큰 비용을 통제. 백엔드 변경 없이 운영 정합 + 비용 효율 둘 다 확보.

### 3. 안 C 폼 패턴은 재사용 가능
E5의 토글+4칸+예시 채우기 패턴은 시계열 외 복잡 입력(예: 다중 시나리오, 다중 필터) 폼에 일반화 가능. 안 A·B·C 의사결정 트리는 향후 새 EP에서도 1차 분기 도구.

### 4. cost_ledger 자동 정합 (Step 0-A 효과 가시화)
P1-C ~ P5-C 6 round-trip 모두 ledger에 자동 정합 (entry_point="eN" + slice="runtime"). 수동 보정 0건. Step 0-A 작업의 운영 가치 명확 입증.

### 5. 멀티턴 prompt 비용 통제 가능
1턴 assistant content = summary만 → 2턴 input token +121 (history 121 토큰). 운영 비용 폭증 우려 없음. 만약 observations까지 history에 넣었다면 +500~600 토큰 수준으로 3~5배 증가할 뻔.

---

## 다음 슬라이스 진입 메모

### Slice 17 후보 우선순위
1. **C 리팩터링** (BaseCard + EP별 Section) — E4MessageBubble 출발점, prop 일반화 비대 완화. CommentaryCard 5 EP 분기 코드 정리.
2. **E4 대화 영속화** — 사용자 수요 발생 시 zustand 승격. 현재 useState로 작동 정상.
3. **#71 해소 확정** — Slice 17 무재발 시 강제 close.
4. **응답 지연 UX 차별화** — E3의 ~30s를 위한 진행률 인디케이터.

### Slice 16에서 잘된 점 / 개선점
**잘된 점**:
- Step 0의 부채 선처리(#68/#70)로 본작업 5 Part가 매끄럽게 진행
- §3 게이트 처리 패턴 정착 (A/B/C)
- 코드 변경 없이 round-trip 자동 정합 (Step 0-A 효과)

**개선점**:
- pytest 회귀 측정 단위 불일치 (portfolio 스코프 759 vs 전체 3172) — 차후 closing에서 측정 기준 1개 고정 필요
- E5 / E4 응답 지연 편차 큼 — UX 차별화 미흡, Slice 17 후속

---

## 종결 선언

✅ **6 코치 화면(E1~E6) 전건 완성**
✅ **#72 6/6 EP close + #72 자체 close**
✅ **회귀 0 / 비용 cap 2.54%**
✅ **TimeSeriesContext + 멀티턴 맥락 운영 첫 실증**
✅ **base 일반화 + 완화 + 자동 호환 §3 패턴 정착**

Slice 16 종결.
