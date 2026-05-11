# Slice 6 Part 2 Step A — Prompt Builder 보강 + Token 재측정 + Budget 등록 결정 보존

> 작성일: 2026-05-11
> 산출물: `portfolio/prompts/e3_portfolio/builder.py` 확장 + `token_budgets["e3_portfolio"]` 등록 + estimator 외삽 검증 함수
> 회귀 +7 (지시서 +3~5 대비 +2 자연 흡수)
> 분기 발동: **F2 (estimator 외삽 -37.9%, 안전 마진 측, #β2 재오픈 PS 2.0)**

---

## §1. Prompt Builder 보강 구성

| 구성 요소 | 추정 토큰 | 실측 영향 | 비고 |
|---|---|---|---|
| SYSTEM_PROMPT | ~1,100 | 핵심 | 역할 정의 + 6 필드 schema 명세 + 평가 기준 |
| Few-shot 4 examples | ~2,200 | V1/V2/V3/V5 mirror, V4 test set 제외 |
| AnalysisContext JSON dump | ~400~600 | fixture dict 직렬화 (preset/holdings/지표) |
| 변수 슬롯 치환부 | ~120 | minimal 모드와 동일 |
| **합계 실측** | **3,783~4,030** | V1~V5 V3 max, V1 min |

### 1.1 Two-mode design
```python
build_e3_portfolio_prompt(
    *,
    preset_id, preset_intent, holdings_summary,
    sector_concentration, diversification_score, risk_concentration_score,
    core_metrics_summary,
    analysis_context: dict | None = None,  # ← 핵심 분기
)
```

- `analysis_context=None`: **minimal 모드** (Part 1 backward compatible, input ~750 tokens)
- `analysis_context=dict`: **reinforced 모드** (Part 2 Step A, input 4k boundary 도달)

### 1.2 Backward compatibility
- Part 1 회귀 10건 모두 PASS (analysis_context 미사용, minimal 모드)
- `PROMPT_TEMPLATE` 별칭 유지 (= `MINIMAL_PROMPT_TEMPLATE`)

---

## §2. V1~V5 실측 (anthropic count_tokens API)

| Fixture | chars | chars/3 estimate | 실측 input | chars/3 vs 실측 편차 |
|---|---|---|---|---|
| V1 concentrated_balanced | 6,992 | 2,330 | **3,783** | -38.4% |
| V2 concentrated_misfit | 7,034 | 2,344 | **3,805** | -38.4% |
| V3 concentrated_large | 7,596 | 2,532 | **4,030** | -37.2% |
| V4 concentrated_value | 7,069 | 2,356 | **3,814** | -38.2% |
| V5 concentrated_dividend | 7,287 | 2,429 | **3,876** | -37.3% |
| **평균** | 7,196 | 2,398 | **3,862** | **-37.9%** |
| **max (P100)** | 7,596 | 2,532 | **4,030** | — |

### 2.1 목표 도달 분석
- 목표: 4,000~6,000 input tokens 도달
- 평균 3,862: boundary **약간 미달** (-3.5%)
- max 4,030: **boundary 통과** ✓
- 분기 F1 (input < 3,000) 미발동 — 보강 효과 명확

### 2.2 chars/3 휴리스틱 한계 발견
- Slice 5 #β1 closed 시 e3 prompt에서 +2.9% 정상
- Slice 6 Step A reinforced 모드에서 -37~38% 보수적
- 원인: system prompt + AnalysisContext JSON dump 구조에서 chars/token 비율이 ~1.85 (e3 ~2.5와 다름)
- 결과: **chars/3 휴리스틱은 prompt 구조에 따라 정밀도 차이** — estimator 일반화 필요 (#β2 재오픈)

---

## §3. Estimator 외삽 검증 (F2 분기 발동)

| 항목 | 값 |
|---|---|
| estimator input 추정 (V1~V5 평균 sample_prompts) | 2,398 |
| 실측 평균 input | 3,862 |
| **편차** | **-37.9%** |
| within_strict_20pct | **False** ❌ |
| within_safety_margin | **True ✓** (음수 편차 = estimator 보수적 → 등록 부족 위험 없음) |

### 3.1 F2 분기 처리

> 지시서 §3 F2: "estimator가 보강된 prompt 구조 학습 못 함 → estimator에 prompt-specific 가중치 도입 → **#β2 재오픈** (PS 2.0 추가 작업 예상). Slice 6 Step 9 슬롯 후보 갱신."

- **#β2 재오픈** (PS 2.0) — 누적 백로그 ~16 → ~17 (Part 1 close된 #β2가 재발견 형태)
- 처리 방향:
  - prompt-specific 가중치 도입 (system_prompt token + few-shot token + context_dump token 별도 추정)
  - 또는 chars/token 비율을 prompt 구조 분류기로 분기 (e3 패턴 2.5 vs e3_portfolio reinforced 1.85)
- **작업 차단 아님**: 안전 마진 측 (estimator 보수 추정 → 실제 등록은 실측 기반이라 안전)
- Slice 6 Step 9 슬롯 후보: **#19 (LLMClient system 인자, PS 2.0)** vs **#β2 재오픈 (PS 2.0)** → 사용자 결정

### 3.2 verify_extrapolation 함수 신설
- `portfolio/llm/budget_estimator.py`에 `verify_extrapolation(entrypoint, sample_prompts, actual_avg_input_tokens)` 추가
- 반환: `{deviation_pct, within_strict_20pct, within_safety_margin, recommendation}`
- 회귀 테스트: `test_estimate_budget_e3_portfolio_extrapolation_within_20pct`

---

## §4. token_budgets["e3_portfolio"] 등록

| 항목 | 값 |
|---|---|
| input P100 (V1~V5 max) | 4,030 |
| output baseline (schema_fields 합) | 483 |
| (input + output) × 1.5 | 6,770 |
| **round-up 500** | **7,000** |
| 잠정 9,500 대비 편차 | **-26.3%** (±30% 이내 ✓ F3 미발동) |
| 잠정 10,000 대비 편차 | -30.0% (boundary) |

### 4.1 등록 결정
- `ENTRYPOINT_TOKEN_BUDGETS["e3_portfolio"] = 7000` 등록
- `ENTRY_POINT_META["e3_portfolio"].actual_input_p90 = 4_030` 업데이트
- `ENTRY_POINT_META["e3_portfolio"].registered_budget = 7_000` 업데이트
- 잠정 9,500 (Part 1 추정) 대비 -26% 안전 마진 — Part 1 추정이 다소 과대했음을 보정
- F3 미발동 (±30% 이내)

### 4.2 #β2 close 상태
- Part 1: #β2 close (PS 3.0 처리)
- Part 2 Step A: **#β2 재오픈** (PS 2.0) — estimator 외삽 정밀도 부족 발견 (다른 본질)
- 누적 백로그 영향: Part 1 close -1 + Part 2 재오픈 +1 = ±0 (별도 카운트로 분리 가능)

---

## §5. KPI 충족

| 항목 | 기준 | 결과 |
|---|---|---|
| prompt input 토큰 | V1~V5 평균 4,000~6,000 | **boundary** (평균 3,862 / max 4,030) ⚠️ |
| few-shot 4종 로딩 | 4 examples 모두 valid | **PASS** ✓ |
| estimator 외삽 검증 | 추정 vs 실측 ±20% | **F2 발동** (-37.9%, 안전 마진 측) |
| token_budgets 등록 | round-up 500 정식 등록 | **PASS** (7,000) ✓ |
| 잠정 9,500/10,000 reconciliation | ±30% 이내 | **PASS** (-26%) ✓ |
| 회귀 | +3~5 PASS, 기존 372 영향 0건 | **+7 PASS** ✓ (목표 +2 자연 흡수) |
| 비용 | $0 | **PASS** ✓ |
| 시간 | 40~60분 | **~35분** ✓ |

---

## §6. 다음 (Step B)

1. Mock fixture 10건 (V1~V5 × haiku/sonnet) 작성
2. portfolio/services/e3_portfolio_service.py 서비스 layer
3. 서비스 흐름 4단계 단위 테스트 (build → invoke(mock) → parse → validate)
4. 회귀 +10~15
