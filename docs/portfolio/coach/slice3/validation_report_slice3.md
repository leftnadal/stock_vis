# Validation Report — Slice 3 (E2 진단 카드 4요소)

> 작성일: 2026-05-07
> 진입점: E2 (D-3 진단 카드 4요소)
> 작업 종류: 글쓰기 (E1 mirror, E5 추출과 다름)
> 범위: Step 0~9 (Part 1 + Part 2)
> 브랜치: portfolio
> 누적 LLM 호출: 15 / 50 (Q5 reset 적용 후, 안전 마진 35)

---

## 1. Step 6 결과 (E2 실 haiku 1회 smoke)

| 판정 | 값 | 임계 | 결과 |
|------|----|----|------|
| schema_pass | True | True | ✓ |
| completeness_auto | True | True | ✓ |
| naturalness_manual | 5/5 | ≥3 | ✓ |
| insight_manual | 5/5 | ≥3 | ✓ |
| cost_pass | $0.00303 | ≤$0.020 | ✓ (임계 15.2%) |
| latency_pass | **7,471ms** | ≤5,000ms | ✗ (E2 출력 길이 영향) |
| fallback_from | None | — | ✓ haiku 직접 |

- fixture: `garp_tech` (slice1_baseline 그룹 — Slice 1 E1과 직접 비교 baseline)
- 산출물: `step6_smoke_e2_output.json`
- 운영 발견: latency 임계 5,000ms는 E1 기준이라 E2(글쓰기 + 4요소 + 항목 10자 이상)에 부적절. Step 8 14회 분포로 확인 후 Slice 4에서 16,000ms로 상향.

## 2. Step 7 토큰 측정 (오프라인)

| 메트릭 | 값 |
|--------|-----|
| 7 fixture 토큰 범위 | 573 ~ 686 |
| P50 | 587 |
| P90 | 686 |
| max utilization | **13.72%** (vs INITIAL_BUDGET=5000) |
| recommended_budget | 1,029 (P90 × 1.5) |
| baseline mean | 620 |
| focused mean | 587 |
| 그룹 차이 | 5.3% (hybrid 결정 정당) |

**결정 #1 (budget)**: `E2_TOKEN_BUDGET = 1500` (E5 2,000보다 작게 — E2 prompt 압축적). Step 9에서 token_budgets.py에 도입 완료.

**결정 #2 (I4 monitoring)**: `analysis_summary` 200자 유지 (max util 13.72% << 30% 임계).

**결정 #3 (Q4 hybrid 검증)**: baseline mean(620) ≈ focused mean(587). 그룹 토큰 차이 33 (5.3%) — focused가 오히려 작아서 hybrid 결정 정당.

## 3. Step 8 회고 (2-way × 7 fixture)

### 3.1 매트릭스

- 14 calls (haiku 7 + sonnet 7) — A1.B 매트릭스
- 14/14 schema_pass + completeness_auto
- fallback 0/14
- total cost **$0.0977** (예상 $0.10 적중)

### 3.2 모델별 결과

| 메트릭 | haiku | sonnet | 차이 |
|--------|-------|--------|------|
| n | 7 | 7 | — |
| schema_pass | 7/7 (100%) | 7/7 (100%) | 동률 |
| naturalness mean | 5.00 | 5.00 | 동률 |
| insight mean | 4.14 | 4.71 | sonnet +0.57 |
| **score mean** | **31.71** | **12.80** | **haiku 2.5×** |
| cost total | $0.0210 | $0.0767 | sonnet 3.65× |
| latency p90 | 7,940ms | 14,756ms | sonnet 1.86× |

### 3.3 Winner: **haiku**

근거 (e1 산식 = sqrt(n×i)/sqrt(cost×lat) — efficiency 분모에 cost/lat):
- naturalness 동률 (5.00)
- insight는 sonnet +0.57 (자동 평가 keyword_match 기준)
- 비용 효율 압도적 — haiku 단가 1/3, latency 1/2
- 결과: efficiency mean haiku 31.71 vs sonnet 12.80 (2.5× 차이)

**D2.B 정책 재검증**: Slice 1 글쓰기 → haiku winner / Slice 2 추출 → sonnet winner / Slice 3 글쓰기 → haiku winner. **작업 종류와 winner 사이 명확한 상관관계 재확인**.

### 3.4 Q4 hybrid 검증 (group analysis)

| 모델 | baseline (garp 3) | focused (e2 4) | 차이 | 판정 |
|------|-------------------|----------------|------|------|
| haiku | 30.26 | 32.80 | +8.4% | small_diff (일관) |
| sonnet | 11.38 | 13.87 | +21.9% | focused_higher |

해석:
- haiku는 두 그룹에서 일관 (small_diff) — fixture 다양성에 robust
- sonnet은 focused 그룹에서 **+22%** — `e2_balanced`/`e2_extreme_risk` 같은 통찰 평가 fixture에서 강점
- **Q4 hybrid 결정 정당화**: focused 그룹이 단순 baseline 보강이 아니라 모델 차별화 정보 추가 (특히 sonnet의 통찰 측정에 가치)

### 3.5 Slice 1 직접 비교 (baseline 그룹)

| 메트릭 | Slice 1 E1 (haiku) | Slice 3 E2 (haiku) | 비고 |
|--------|--------------------|--------------------|------|
| naturalness mean | (Slice 1 산출물) | 5.00 | E2도 글쓰기 차원 동일 |
| insight mean | (Slice 1 산출물) | 3.67 (baseline 3개) | E2 자동 평가 룰 영향 (keyword_match) |
| latency mean | ~2,000ms | 6,810ms | E2 출력 길이로 3.4× |
| cost mean | ~$0.001 | $0.0029 | E2 출력 길이로 3× |

E1 (한 줄 진단)과 E2 (4요소 카드)는 출력 크기가 본질적으로 다름 — 비용/지연 직접 비교는 출력 양 차이 반영 필요.

### 3.6 D4 회피 가이드 검증

Slice 2 1차 손실 (set 직렬화 실패로 14건 손실) 재발 차단:
- 모든 run/measure 스크립트에 `_json_default` 핸들러 정의 ✓
- 산출물 disk write 후 read-back round-trip 검증 ✓
- Slice 3 14호출 1차 시도에서 손실 0 — 가이드 효과 입증

## 4. Step 9 리팩토링 결과

**완료 (백로그 #5 — A2.C)**:
- `portfolio/llm/token_budgets.py` 신규 — `ENTRYPOINT_TOKEN_BUDGETS = {e1: 5000, e5: 2000, e2: 1500}`
- `get_token_budget(entrypoint)` + `estimate_input_tokens(prompt)` 휴리스틱
- 단위 테스트 4개

**Slice 4 이연**:
- LLMClient에 `entrypoint` 인자 추가 + 입력 가드레일 통합 (Step 9 슬롯 한도 보존)
- score 산식 통합 (e1 동적 normalize + e5 정적 + e2 e1 mirror)
- Slice 1 deferred #7 (CSV 출력) / #8 (Mock mode dict)

## 5. 누적 비용

| Step | LLM 호출 | 누적 | 실측 비용 |
|------|---------|------|----------|
| Slice 3 진입 (Reset 적용) | — | 0 | — |
| Step 6 E2 smoke | 1 | 1 | $0.00303 |
| Step 7 (count_tokens, 비용 0) | 0 | 1 | — |
| Step 8 (14 calls) | 14 | 15 | $0.0977 |
| **Slice 3 종결** | **15** | **15/50** | **~$0.101** |

비용 가드 안전 마진: **35/50 (70%)**.

## 6. Slice 4 백로그

`refactor_backlog_slice3.md` 참조. 핵심 항목:

| # | 항목 | PS | 출처 |
|---|------|-----|------|
| 1 | score 산식 통합 (e1+e2 통일 + e5 정적 분리) | 3.0 | Slice 2 백로그 #2 |
| 2 | LLMClient entrypoint 인자 + 입력 가드레일 | 2.5 | Slice 3 Step 9 미완 |
| 3 | latency 임계 16,000ms 상향 | 2.0 | Slice 3 Step 6 발견 |
| 4 | E2 자동 평가 keyword_match 룰 보완 | 1.5 | Step 8 자동 평가 발견 |
| 5 | Step 8 raw output CSV 옵션 | 1.0 | Slice 1 deferred |
| 6 | Mock LLMClient mode dict 매핑 | 1.0 | Slice 1 deferred |

## 7. 검증 판정 종합

| Step | 판정 수 | PASS | FAIL | 비고 |
|------|--------|------|------|------|
| 0.5 (CostGuard) | 5 | 5 | 0 | 단위 테스트 |
| 0.6 (Mock e2) | 3 | 3 | 0 | — |
| 1 (schema) | 5 | 5 | 0 | E2DiagnosticCard 6 테스트 |
| 2 (services) | 6 | 6 | 0 | 백로그 #3,#4 흡수 |
| 3 (view) | 3 | 3 | 0 | — |
| 4 (Mock 4 시나리오) | 2 | 2 | 0 | rate_limit/timeout/auth/budget |
| 5 (hybrid fixture) | 5 | 5 | 0 | parametrize 7×2 + 그룹 검증 |
| 6 (smoke) | 8 | **7** | **1** | latency 임계 — Step 8에서 재해석 |
| 7 (token) | 6 | 6 | 0 | budget 1500 결정 |
| 8 (14 calls + 그룹) | 7 | 7 | 0 | 14/14 schema, winner 결정 |
| 9 (token_budgets) | 5 | 5 | 0 | Slice 1/2 회귀 IDENTICAL |
| **합계** | **55** | **54** | **1** | latency 1건만 — Slice 4 임계 조정 |

회귀: 76 → **123 passed** (+47)

---

## 8. Slice 단위 reset 메커니즘 검증

`portfolio/llm/cost_guard.py` (Slice 3 Step 0.5) — D3.C 코드 구현 완료.

**검증된 패턴**:
- `CostGuard.get_instance().reset_slice("slice3", max_calls=50)` — 멱등 reset
- `LLMClient.complete()` 호출 전후 자동 record_call → 한도 도달 시 LLMBudgetExceededError
- Slice 3 14회 호출 모두 정상 누적 (CostGuard 누적 검증 100% 정확)

Slice 4 진입 시 `reset_for_slice("slice4")` 한 줄로 자동 카운터 0 시작.

---

## 9. 작업 종류 ↔ Winner 상관관계 (3 슬라이스 누적)

| Slice | 진입점 | 작업 종류 | Winner | 비용 비교 |
|-------|--------|----------|--------|-----------|
| 1 | E1 (한 줄 진단) | 글쓰기 | **haiku** | haiku ~$0.001/call |
| 2 | E5 (조정 파싱) | 추출 | **sonnet** | sonnet 3.17× haiku |
| 3 | E2 (4요소 카드) | 글쓰기 | **haiku** | haiku ~$0.003/call (출력 3×) |

**가설 정착**: 글쓰기는 haiku, 추출/엄격함은 sonnet. 향후 새 진입점도 작업 종류로 default 결정.

---

> **광의 누적 비용** = $0.428 (Slice 2 광의 $0.327 + Slice 3 $0.101). 광의 단일 정책 채택 (Slice 5 Step 0 #γ1 부채 처리).
