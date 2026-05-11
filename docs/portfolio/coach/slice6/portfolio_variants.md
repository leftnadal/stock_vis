# Slice 6 Part 1 Step 1 — E3PortfolioCommentary Schema + 변형 5종 결정 보존

> 작성일: 2026-05-10
> 산출물: `portfolio/schemas/llm_outputs.py` E3PortfolioCommentary + `portfolio/prompts/e3_portfolio/` + V1~V5 fixture + DIMENSION_LOOKUP entry
> 회귀 +10 (지시서 +4~8 대비 +2 자연 흡수)

---

## §1. E3PortfolioCommentary Schema (6 필드)

| 필드 | 타입 | 제약 | 토큰 baseline |
|---|---|---|---|
| holistic_assessment | str | 30~300자 | str_long → 175 |
| diversification_comment | str | 20~200자 | str_medium → 100 |
| sector_balance_comment | str | 20~200자 | str_medium → 100 |
| risk_concentration_comment | str | 20~200자 | str_medium → 100 |
| preset_alignment | Literal["aligned", "partial", "misaligned"] | enum | literal → 5 |
| confidence | int | 1~5 | int_float → 3 |

**output 토큰 합**: 175 + 100×3 + 5 + 3 = **483** (×1.5 buffer ≈ 725)

`PresetAlignment` StrEnum 신설 (3종) — `portfolio/schemas/llm_outputs.py`.

---

## §2. Prompt Template 변수 슬롯 7종 (지시서 §2.4)

| # | 변수 | 출처 | 비고 |
|---|---|---|---|
| 1 | preset_id | 입력 | garp/buffett_quality_value/dividend_growth/quality_factor/contrarian |
| 2 | preset_intent | 입력 | preset 의도 자연어 (PRESET_INTENT_MAP) |
| 3 | holdings_summary | 입력 | 보유 종목 평탄화 (`MSFT(30%), NVDA(20%), ...`) |
| 4 | sector_concentration | **분석엔진 사전 산출** | 예: "Tech 50%" |
| 5 | diversification_score | **분석엔진 사전 산출** | 0.0~1.0 |
| 6 | risk_concentration_score | **분석엔진 사전 산출** | 0.0~1.0 |
| 7 | core_metrics_summary | **분석엔진 사전 산출** | Core 7종 raw 평탄화 |

**Few-shot 2개**: concentrated_balanced (partial alignment) + concentrated_dividend (aligned).

→ Slice 1~5 분석 엔진 회피 정책 일관 (정량 재계산 없음, LLM은 자연어 코멘트만).

---

## §3. 변형 5종 Fixture (V1~V5, 5 카테고리 cover)

| Case | holdings | sector top | div | risk_conc | preset | 카테고리 | expected_alignment |
|---|---|---|---|---|---|---|---|
| **V1** concentrated_balanced | 5 | Tech 50% | 0.35 | 0.45 | garp | growth | partial |
| **V2** concentrated_misfit | 5 | Tech 80% | 0.15 | 0.80 | garp | growth | **misaligned** (special-ish) |
| **V3** concentrated_large | 10 | Tech 52% + HC 48% | 0.25 | 0.40 | quality_factor | factor | partial |
| **V4** concentrated_value | 5 | Financials 100% | 0.20 | 0.55 | buffett_quality_value | value | aligned |
| **V5** concentrated_dividend | 7 | Consumer Staples 78% | 0.30 | 0.35 | dividend_growth | income | aligned |

**5 카테고리 cover** (지시서 §2.5):
- growth (V1, V2): GARP × 정합/misfit 패턴
- value (V4): buffett_quality_value
- income (V5): dividend_growth
- factor (V3): quality_factor
- special (V2 misfit이 special-ish 패턴 cover — preset_category=growth지만 expected_alignment=misaligned)

**FIXTURE_GROUPS**:
- `concentrated_baseline`: V1, V2 (Slice 5 hybrid 7 mirror baseline)
- `concentrated_focused`: V3, V4, V5 (preset 다양성)

---

## §4. DIMENSION_LOOKUP[e3_portfolio] (Slice 5 e3 mirror 100%)

```python
"e3_portfolio": {
    "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
    "dim2": {"key": "insight", "manual_field": "insight_manual"},
    "model_label_field": "model_label",
    "result_structure": "nested",
    "default_raw":    "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "default_scored": "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_scored.json",
    "weight": 0.5,
    "additional_lex_check": "completeness_auto",
}
```

→ **`_main_unified()` 변경 0줄** ✓ (자동 dispatch ready). path만 slice5 → slice6, e3 → e3_portfolio.

---

## §5. KPI 충족

| 항목 | 기준 | 결과 |
|---|---|---|
| schema 일관성 | 6 카테고리 cover (5 preset + concentrated 차원) | **PASS** ✓ |
| Core 7종 | 7 변수 슬롯 모두 prompt 매핑 | **PASS** ✓ |
| 출력 schema | 6 필드 (holistic + 3 medium + literal + int) | **PASS** ✓ |
| 변형 5종 | V1~V5 fixture 사전 fix, 5 카테고리 cover | **PASS** ✓ |
| 자동 dispatch | DIMENSION_LOOKUP entry → _main_unified 변경 0줄 | **PASS** ✓ |
| 회귀 | +10 PASS, 기존 232+7=239 영향 0건 (자연 흡수 +2) | **PASS** ✓ |
| 비용 | $0 (LLM 호출 0) | **PASS** ✓ |

**분기 시나리오 발동 0건** (E1~E4 모두 미발동, e5 음수 편차는 안전 마진).

---

## §6. 다음 (Part 2)

1. Slice 6 Part 2 Step 6 smoke (V1 fixture × haiku × 1 call)
2. Step 7 token 측정 — V1~V5 sample_prompts → e3_portfolio P90 산출 → 잠정 9,500/10,000 reconciliation
3. Step 8 14 calls 회고 (haiku 7 + sonnet 7)
4. Step 9 슬롯 후보: **#19 LLMClient.complete `system` 인자 추가** (PS 2.0, E3 패턴 본질 일관)
