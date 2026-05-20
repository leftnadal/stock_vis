# Slice 12 Part 2 — PresetSpec 명세 + 12 preset 매핑

**작업일**: 2026-05-20
**source**: Slice 11 Part 1 inventory + `portfolio/metrics/definitions/preset_metrics.py`

---

## §1. PresetSpec schema

```python
class PresetSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    preset_id: str
    category: Literal["value", "growth", "income", "factor", "special"]
    weights: dict[str, float]  # 합 1.0 ± 0.001, 모두 ≥ 0
    gate: Optional[dict[str, float | str]] = None
    description: str = ""
```

Validators:
- `_validate_weights`: 합 1.0 ± 0.001 + 음수 차단
- `_validate_gate_op`: `_op` ∈ {gte, lte, gt, lt}, metric 키 최소 1개

---

## §2. 12 preset → 5 카테고리 매핑

| 카테고리 (n) | preset_id                  | weights (지표 → 가중치)                                                                       | gate                                |
| ------------ | -------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------- |
| **value (2)** | buffett_quality_value      | roic 0.30 / roe 0.25 / roic_consistency_5y 0.25 / earnings_consistency_5y 0.20               | None                                |
|              | piotroski_f_score          | f_score_total 1.00                                                                            | None                                |
| **growth (2)** | garp                       | peg_ratio 0.40 / eps_growth_yoy 0.30 / revenue_growth_yoy 0.30                               | None                                |
|              | quality_growth             | roic 0.30 / roic_consistency_5y 0.20 / revenue_growth_yoy 0.25 / eps_growth_yoy 0.25         | None                                |
| **income (2)** | dividend_growth            | dividend_yield 0.40 / dividend_growth_rate_5y 0.35 / dividend_growth_consistency_5y 0.25     | **dividend_yield ≥ 0.02**           |
|              | shareholder_yield          | shareholder_yield 0.40 / dividend_yield 0.25 / net_buyback_yield 0.20 / net_debt_reduction_rate 0.15 | **shareholder_yield ≥ 0.02** |
| **factor (4)** | quality_factor             | roic 0.30 / roe 0.25 / gross_margin 0.20 / roe_stability_5y 0.25                             | None                                |
|              | low_volatility             | volatility_1y 0.30 / beta 0.20 / downside_deviation 0.25 / max_drawdown_1y 0.15 / portfolio_volatility 0.10 | **beta ≤ 1.2**                   |
|              | price_momentum             | return_12m 0.40 / return_6m 0.25 / return_3m 0.15 / relative_strength 0.20                   | None                                |
|              | multi_factor               | composite_value/quality/growth/momentum/low_vol 각 0.20                                       | None                                |
| **special (2)** | contrarian                 | pe_ratio 0.25 / pb_ratio 0.25 / pct_from_52w_high 0.30 / f_score_total 0.20                  | None (direction_override 호출자 책임) |
|              | concentrated_portfolio     | hhi_concentration 0.25 / sector_hhi 0.20 / top3_weight 0.15 / holding_count 0.10 / portfolio_beta 0.10 / max_position_weight 0.10 / avg_correlation 0.10 | None |

**모든 preset weights 합 = 1.0000** (validator PASS).

---

## §3. Gate 정책 (D2-B)

| preset_id          | gate                            | 의미                                       |
| ------------------ | ------------------------------- | ------------------------------------------ |
| dividend_growth    | dividend_yield ≥ 0.02           | 배당주 본질 — yield 2% 미만 컷             |
| shareholder_yield  | shareholder_yield ≥ 0.02        | 총 주주환원 2% 미만 컷                     |
| low_volatility     | beta ≤ 1.2                      | 저변동성 본질 — 베타 초과 컷               |

총 3건 gate (income 2 + factor 1). 나머지 9 preset은 gate=None.

---

## §4. 정규화 책임 분리

본 모듈은 **정규화된 metrics dict (0~1 범위)**를 받는다고 가정.

호출자(Part 3 smoke)가 다음을 처리:
- `peg_ratio` → `peg_score` (lower-is-better inverse)
- `volatility_1y` → `1 - volatility_score` (inverse)
- `pe_ratio` (contrarian 해석 시) → direction_override 처리
- `pct_from_52w_high` → 음수 정규화 (-100% → 1, 0% → 0)

이 책임 분리는 Slice 11 Part 1 input schema 정합성 + Part 3 통합 호환성 보장.
