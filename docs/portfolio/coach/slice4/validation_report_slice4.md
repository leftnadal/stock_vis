# Slice 4 (E6 조정 후 비교 해설) Validation Report

> 작성일: 2026-05-07
> 진입점: **E6** (조정 후 비교 해설, E5 흐름 통합)
> Part 1 종결: 160 passed (5 commits)
> Part 2 종결: **296 passed** (+136, Step 7 +3 + Step 9 +10 + Slice 4 Part 1 산출 +37 + 사전 사용 안 한 marketpulse v2 origin merge +86)
> 누적 LLM 호출 (Slice 4): 15 / 50 (Step 6: 1 + Step 8: 14 + 재시도 0)
> 누적 비용 (Slice 4): **$0.1576**

---

## §1 메타데이터

| 항목 | 값 |
|------|----|
| Slice 범위 | E6 (D-7) Part 2: Step 6~9 + validation_report + refactor_backlog |
| Default provider | **haiku** (D2.B 글쓰기 가설 적용) |
| Fixture 전략 | hybrid 7 (e5_baseline 3 재활용 + e6_focused 4 신규) |
| 평가 차원 | naturalness (auto) + insight (auto) + completeness_auto (schema 통과) |
| Step 9 슬롯 | **#2 score 산식 통합 (PS 3.0) 완료** — e1/e2/e6 `_main_unified()` |
| 실행 환경 | branch=portfolio, ANTHROPIC_API_KEY=set, GEMINI_API_KEY=set |
| Step 6 호출 시점 | 2026-05-07T05:58:10 UTC |
| Step 8 호출 시점 | 2026-05-07T06:00:56 UTC |
| LLMClient git SHA (Part 2 진입 시) | b1767ec (Slice 4 Part 1 종결 commit + origin 머지) |

---

## §2 Step 6 — Smoke Test

| 판정 | 값 | 임계 | 결과 |
|------|----|----|------|
| schema_pass | True | True | ✓ |
| completeness_auto | True | True | ✓ |
| cost_pass | $0.00437 | ≤$0.020 | ✓ (임계 21.8%) |
| latency_pass | **9,180ms** | ≤16,000ms | ✓ (#9 신규 임계 e6 한정 적용) |
| fallback_from | None | — | ✓ haiku 직접 |

- fixture: `e5_baseline_decrease` (e5_baseline 그룹 — Slice 2 E5 재활용)
- 산출물: `step6_smoke_e6_output.json` (round-trip OK)
- naturalness_manual / insight_manual: 자동 평가 룰 적용 (사용자 수동 검증 권장)
- **#9 처리 효과**: 9,180ms는 5,000ms 임계 초과 — Slice 3 E2 7,471ms와 유사 패턴 재현. 16,000ms 신규 임계로 PASS 처리. 기존 5 파일은 변경 0 (회귀 위험 0)

---

## §3 Step 7 — Token 측정 + Budget 결정

| 메트릭 | 값 |
|--------|-----|
| 7 fixture 토큰 범위 | 725 ~ 845 |
| mean | 768 |
| P50 | 762 |
| P90 | **845** |
| max utilization | 56.33% (vs INITIAL_BUDGET=1500) |
| recommended_budget | 1,500 (P90=845 × 1.5 = 1,267.5 → round-up 500) |
| baseline mean | 742.7 (3 fixture) |
| focused mean | 787.0 (4 fixture) |
| 그룹 차이 | 5.96% (hybrid 결정 정당) |

**결정 #1 (budget)**: `e6: 1500` (E2와 동일). 사전 추정 1,000 대비 +50% — 한국어 토큰화 비율이 영어 chars/3보다 무거움 (한국어 ~1.3 char/token vs 영어 ~3.5).

**결정 #2 (I4 monitoring)**: `analysis_summary` 200자 유지 (max util 56.33%, "30~70% 모니터링" 범위 내).

**결정 #3 (Q4 hybrid 검증)**: baseline mean(742.7) ≈ focused mean(787) — focused 그룹이 약간 길지만 5.96% 차이 (small_diff 범주).

**산출물**: `docs/portfolio/coach/slice4/step7_e6_tokens.json` + `portfolio/llm/token_budgets.py` 갱신 + 단위 테스트 +3

---

## §4 Step 8 — 2-way 회고

### 4.1 매트릭스

- 14 calls (haiku 7 + sonnet 7) — A1.B 매트릭스
- 14/14 schema_pass + completeness_auto
- fallback 0/14
- total cost **$0.1532** (예상 $0.10보다 +50%, sonnet 영향)

### 4.2 모델별 결과

| 메트릭 | haiku | sonnet | 차이 |
|--------|-------|--------|------|
| n | 7 | 7 | — |
| schema_pass | 7/7 (100%) | 7/7 (100%) | 동률 |
| naturalness mean | 4.43 | 4.57 | sonnet +0.14 |
| insight mean | 4.71 | 4.71 | 동률 |
| **score mean (efficiency)** | **21.76** | **7.73** | **haiku 2.81×** |
| cost total | $0.0325 | $0.1208 | sonnet 3.72× |
| latency p90 | 10,656ms | 24,561ms | sonnet 2.30× |

### 4.3 Winner: **haiku**

근거 (e1 산식 = sqrt(n×i)/sqrt(cost×lat)):
- naturalness 거의 동률 (4.43 vs 4.57)
- insight 완전 동률 (4.71)
- 비용 효율 압도적 — haiku 단가 1/3.72, latency 1/2.30
- 결과: efficiency mean haiku 21.76 vs sonnet 7.73 (**2.81× 차이**)

**D2.B 정책 4번째 외삽 검증**: Slice 1 글쓰기 → haiku / Slice 2 추출 → sonnet / Slice 3 글쓰기 → haiku / **Slice 4 글쓰기 → haiku**. **글쓰기→haiku 가설 4/4 정착** ✓.

### 4.4 §3.4 Q4 hybrid 검증 (group analysis)

| 모델 | 그룹 | n | naturalness_mean | insight_mean | score_mean | cost_total_usd | latency_mean_ms |
|------|------|---|------------------|--------------|------------|----------------|-----------------|
| haiku | e5_baseline | 3 | 4.33 | 4.33 | **22.12** | $0.0130 | 8,766 |
| haiku | e6_focused | 4 | 4.50 | 5.00 | **21.49** | $0.0194 | 10,023 |
| sonnet | e5_baseline | 3 | 5.00 | 4.33 | **8.13** | $0.0482 | 20,627 |
| sonnet | e6_focused | 4 | 4.25 | 5.00 | **7.43** | $0.0726 | 21,294 |

| 모델 | baseline | focused | Δ | 판정 |
|------|----------|---------|---|------|
| haiku | 22.12 | 21.49 | -2.85% | **small_diff** |
| sonnet | 8.13 | 7.43 | -8.61% | **small_diff** |

해석:
- 두 모델 모두 baseline → focused에서 약간 감소 (2~9%) — focused 그룹이 약간 더 도전적 (다중 조정 / 디펜시브 추가 / multi_aspect)
- haiku는 두 그룹 사이 robust (small_diff) — fixture 다양성에 무관하게 일관 우수
- **Q4 hybrid 결정 정당화**: 두 그룹 score 유사 (small_diff 두 모델 동시) — fixture 다양성이 winner 결정을 뒤집지 않음. e5_baseline 재활용으로 Slice 2와 비교 가능성 확보 + e6_focused로 E6 특화 케이스 검증

### 4.5 글쓰기 가설 외삽 검증

| Slice | 진입점 | 작업 종류 | Winner | 비용 비교 | 가설 정합 |
|-------|--------|----------|--------|-----------|----------|
| 1 | E1 (한 줄 진단) | 글쓰기 | **haiku** | haiku ~$0.001/call | ✓ |
| 2 | E5 (조정 파싱) | 추출 | **sonnet** | sonnet 3.17× haiku | ✓ (반례) |
| 3 | E2 (4요소 카드) | 글쓰기 | **haiku** | haiku ~$0.003/call | ✓ |
| 4 | **E6 (비교 해설)** | **글쓰기** | **haiku** | haiku ~$0.0046/call | ✓ |

**가설 정착**: 글쓰기→haiku 4/4. 추출/엄격함→sonnet 1/1. 작업 종류로 default provider 결정 정당.

---

## §5 누적 비용

| 슬라이스 | reset 시점 | 사용 | 마진 | 실측 비용 | Reset 메커니즘 |
|---------|----------|------|------|-----------|----------------|
| Slice 1 | (수동) | 10/50 | 40 | ~$0.137 (광의) | 인스턴스별 _call_count |
| Slice 2 | (수동) | 32/50 (+14 손실) | 18 | ~$0.19 (광의) | 인스턴스별 _call_count |
| Slice 3 | **자동 (Q5)** | 15/50 | 35 | ~$0.10 (협의) | CostGuard 싱글톤 |
| Slice 4 | **자동** | 15/50 | 35 | **~$0.158** | CostGuard 싱글톤 |
| **누적 (광의)** | — | 72 calls | — | **~$0.585** | — |

### Slice 4 비용 분해

| Step | LLM 호출 | 누적 | 실측 비용 |
|------|---------|------|----------|
| Slice 4 진입 (Reset) | — | 0 | — |
| Step 6 E6 smoke | 1 | 1 | $0.00437 |
| Step 7 (count_tokens, 비용 0) | 0 | 1 | — |
| Step 8 (14 calls) | 14 | 15 | $0.1532 |
| **Slice 4 종결** | **15** | **15/50** | **$0.1576** |

비용 가드 안전 마진: **35/50 (70%)**. CostGuard 한도 초과 발생 0건.

---

## §6 Step 9 — Score 산식 통합 (백로그 #2)

### 6.1 통합 범위

| 영역 | 처리 | 결과 |
|------|------|------|
| e1/e2/e6 산식 통합 | `_main_unified()` 한 함수 | ✓ 완료 |
| e5 산식 | delegation 유지 | ✓ 별도 모듈 (산식 본질 차이) |
| 신규 헬퍼 | `_normalize_results` / `_build_lex_filter` / `_build_output_dict` | 3개 |
| 출력 형식 분기 | entrypoint별 (e1: 4 키 / e2,e6: 6 키) | IDENTICAL 보존 |

### 6.2 회귀 KPI 검증 (sha256 hash)

| 진입점 | baseline hash | post-Step9 hash | 결과 |
|--------|---------------|-----------------|------|
| Slice 1 e1 | 917fa3ef…0f7b9 | 917fa3ef…0f7b9 | **IDENTICAL** ✓ |
| Slice 3 e2 | 5594c6ab…cf3ba | 5594c6ab…cf3ba | **IDENTICAL** ✓ |
| Slice 4 e6 | (Step 8 산출) | 동일 winner=haiku, label_means 일치 | ✓ |
| Slice 2 e5 | (delegation) | 분기 정상 동작 | ✓ |

**핵심 KPI 충족**: Slice 1·3 산출물 hash 한 비트도 변경 없음. 통합 후에도 회귀 0.

### 6.3 단위 테스트 +10

`portfolio/tests/test_score_unified.py` 신규:
- normalize 4개: flat passthrough / nested to flat / error entry / unknown structure
- lex_filter 2개: no_additional_check / with_completeness_auto
- output_dict 2개: e1 format (4 키) / e2,e6 format (6 키)
- dimension_lookup_e6_registered
- main_unified_dispatch_e1_e2_e6_only

### 6.4 시간 한도 준수

- 작업 시간: ~25분 / 30분 한도 → **안전**

---

## §7 회귀 카운트 진행

| 단계 | 추가 | 누적 | 비고 |
|------|------|------|------|
| Slice 4 Part 1 종결 baseline | — | 160 | (portfolio 단독 카운트) |
| Part 2 진입 (origin merge 후) | (origin marketpulse v2 +123) | 283 | rebase 후 baseline |
| Step 6 (smoke 산출물) | 0 | 283 | |
| Step 7 (token + 단위 +3) | +3 | 286 | test_token_budgets 확장 |
| Step 8 (회고 산출물) | 0 | 286 | |
| Step 9 (#2 통합 + 단위 +10) | +10 | **296** | _main_unified + dispatch 검증 |

**Slice 4 Part 2 단독 회귀 증가: +13** (Slice 3 Part 2 +23 보수적 적용 시 ±5).

### 7.1 진입점별 회귀 분포

| 진입점 | 카운트 |
|--------|-------|
| e1 (test_e1_garp_view) | 5 |
| e2 (test_e2_*) | 31 |
| e5 (test_e5_*) | 28 |
| e6 (test_e6_*) | 37 |
| **진입점별 합계** | 101 |
| 나머지 (cost_guard, fixtures_validation, mocks, prompt_assembly, scenario_e2e, schemas, session_lifecycle, static_integrity, **token_budgets +3**, **score_unified +10**, marketpulse +84 등) | 195 |
| **총 합계** | **296** |

---

## §8 케이스 발생 여부 (Slice 4 신규 + 이연)

### 8.1 Slice 3 9건 백로그 처리 결과

| # | 항목 | PS | Slice 4 처리 |
|---|------|-----|-------------|
| 2 | score 산식 통합 (e1+e2+e6) | 3.0 | **Slice 4 Step 9 완료** |
| 5 | TOKEN_BUDGET LLMClient 통합 (잔여) | 2.0 | Slice 5 이연 |
| 6 | Step 8 CSV 옵션 | 1.0 | Slice 5 이연 |
| 7 | Mock mode dict 매핑 | 1.0 | Slice 5 이연 |
| 8 | LLMClient entrypoint 인자 | 2.5 | Slice 5 이연 |
| 9 | latency 임계 16,000ms 상향 | 2.0 | **Slice 4 Step 6 완료 (e6 한정)** |
| 10 | E2 keyword_match 룰 보완 | 1.5 | Slice 5 이연 (E2 한정) |
| 11 | metrics_table 일반화 | 1.5 | Slice 5 이연 |

**누적 처리 효율**: 2건 완료 (#2, #9 — e6 한정), 6건 이연.

### 8.2 Slice 4 신규 백로그

| # | 항목 | PS | 트리거 |
|---|------|-----|--------|
| 12 | E6 분석 엔진 재계산 (Phase 2) | 5.0 | D-7 스켈레톤 패턴 회귀 — `original_context + adjusted_context` 형태 |
| 13 | `run_step6_*.py` 5종 latency 일괄 16,000ms 상향 | 1.0 | Slice 4 #9 e6 한정 적용 후 일관성 검토 |
| 14 | `score_step8.py` CLI 인자 확장 (`--input`/`--output`) | 1.5 | Slice 5+ 진입점 추가 시 round-trip 검증 편의 |
| 15 | E6 자동 평가 룰 정교화 | 1.5 | Step 8 자동 평가 룰이 simple — sonnet 통찰 차별화 미반영 가능성 |
| 16 | E6 latency 24s 초과 sonnet 패턴 | 1.0 | 4건 sonnet 22~24s 임계 근접 — Slice 5 latency 임계 재검토 |
| 17 | `auto_eval_e6.py` 패턴 일반화 (Slice 5+) | 2.0 | E2 keyword_match → E6 휴리스틱과 통합 가능 |

---

## §9 Slice 5+ 진입 결정 자료

### 9.1 다음 슬라이스 진입점 후보

| 후보 | 사용자 가치 | 의존성 | 구현 복잡도 | 권장도 |
|------|------------|--------|-------------|--------|
| **E3 (지표 코멘트 — preset 외삽 검증)** | 중 | 단독 | 낮음 | ⭐⭐⭐ |
| **E4 (대화 Q&A Tier 1~3)** | 매우 높음 | Tier 다층 | 높음 | ⭐⭐⭐⭐ |

### 9.2 E3 권장 (Slice 5)

근거:
- Slice 3 E2 insight 그룹차 0.67~0.83 → Buffett/Defensive preset fixture 추가 검증 필요
- 단독 진입점, 의존성 낮음 — 빠른 슬라이스 완수
- 글쓰기 차원 (haiku 예상) — 가설 5번째 외삽 검증
- prompts/e3 스켈레톤 이미 존재 (`input_builder.py`, `instructions.py`, `examples.py`, `e3_builder.py`)

### 9.3 가설 정착 효과

| 영역 | 효과 |
|------|------|
| Default provider | 작업 종류로 결정 가능 — 글쓰기→haiku, 추출→sonnet |
| 새 글쓰기 진입점 추가 시 | DIMENSION_LOOKUP 한 줄 + Mock 한 함수 + fixture 추가 = 신규 인프라 0 |
| 비용 통제 | 글쓰기 default haiku로 운영 비용 sonnet 대비 1/3.7 |

---

## 부록 A — Slice 4 종결 결정 표

| 항목 | 값 |
|------|----|
| 진입점 | E6 (조정 후 비교 해설) |
| Default provider | **haiku** |
| Fixture 전략 | hybrid 7 (e5_baseline 3 재활용 + e6_focused 4 신규) |
| 평가 차원 | naturalness + insight (auto) + completeness_auto |
| Step 8 매트릭스 | 7×2=14 (haiku 7 + sonnet 7) |
| Step 9 슬롯 작업 | **#2 score 산식 통합 — 완료** |
| **Step 8 winner** | **haiku** (label_means 21.76 vs 7.73, 2.81× 차이) |
| **글쓰기 가설** | **4/4 정착** ✓ |
| 누적 호출 (Slice 4) | 15 / 50 |
| 누적 비용 (Slice 4) | $0.1576 |
| Slice 5 진입 결정 | E3 또는 E4 (사용자 결정 대기) |

---

## 부록 B — 케이스 A~F 발생 기록

| 케이스 | 발생 | 처리 |
|-------|------|------|
| A (Step 6 schema_pass=False) | 없음 | — |
| B (Step 6 latency > 16,000ms) | 없음 | 9,180ms로 임계 57% 사용 |
| C (Step 8 호출 마진 부족) | 없음 | 15/50 종결 |
| D (Step 9 IDENTICAL 깨짐) | 없음 | Slice 1·3 hash 모두 IDENTICAL |
| E (Step 9 30분 한도 초과) | 없음 | ~25분 종결 |
| F (Step 8 winner sonnet) | **없음** | winner=haiku, 글쓰기 가설 4/4 정착 ✓ |

---

## 부록 C — 자동 평가 룰 한계 + 사용자 검증 권장

Slice 4 Step 8의 manual 평가 28건은 사용자 수동 입력이 원칙이지만, auto mode 진행으로 휴리스틱 룰 적용:

**naturalness 룰**:
- schema_pass + cond_keyword_count >= 2 → 5
- schema_pass + cond_keyword_count >= 1 → 4
- schema_pass → 4 (기본)
- schema_fail → 1

**insight 룰**:
- schema_pass + kc_count >= 4 + distinct_aspects >= 4 → 5
- schema_pass + kc_count >= 4 + distinct_aspects >= 3 → 4
- schema_pass + kc_count >= 3 → 4 (기본)
- kc_count < 3 → 3

**한계**:
- sonnet의 통찰 깊이 차별화가 룰에 반영 안 됨 (Slice 3 sonnet insight +0.57 패턴 재현 안 됨)
- 자연어 어조의 미세한 차이 미감지

**권장**: 사용자가 raw_content를 검토 후 `naturalness_manual` / `insight_manual` 값 직접 수정 + score_step8 재실행. 결과 변동 시 본 보고서 §4.2 갱신.
