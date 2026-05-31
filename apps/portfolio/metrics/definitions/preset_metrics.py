"""
Stock-Vis Preset-Metric Mapping (코드 상수)
=============================================

stock-vis-preset-metrics-matrix.md 기반.
각 프리셋이 어떤 지표를 어떤 계층(Core/Supporting/Context)으로 사용하는지 정의.

구조: PRESET_METRICS[preset_id] = [
    {"metric_id": "...", "tier": "core|supporting|context", "direction_override": None},
    ...
]

direction_override: 프리셋별로 방향성을 재정의할 때만 사용.
    예: Contrarian 프리셋에서 pe_ratio를 higher_is_better로 해석 (고PER = 시장 비관 신호).
    None이면 METRICS의 기본 direction 사용.
"""

PRESET_METRICS = {
    # ================================================================
    # VALUE
    # ================================================================
    "buffett_quality_value": [
        # Core
        {"metric_id": "roic", "tier": "core"},
        {"metric_id": "roe", "tier": "core"},
        {"metric_id": "roic_consistency_5y", "tier": "core"},
        {"metric_id": "earnings_consistency_5y", "tier": "core"},
        # Supporting
        {"metric_id": "gross_margin", "tier": "supporting"},
        {"metric_id": "fcf_margin", "tier": "supporting"},
        {"metric_id": "debt_to_equity", "tier": "supporting"},
        {"metric_id": "pe_ratio", "tier": "supporting"},
        {"metric_id": "pb_ratio", "tier": "supporting"},
        {"metric_id": "ev_to_ebitda", "tier": "supporting"},
        {"metric_id": "buyback_yield", "tier": "supporting"},
        # Context
        {"metric_id": "revenue_growth_yoy", "tier": "context"},
        {"metric_id": "eps_growth_yoy", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    "piotroski_f_score": [
        # Core
        {"metric_id": "f_score_total", "tier": "core"},
        # Supporting
        {"metric_id": "pe_ratio", "tier": "supporting"},
        {"metric_id": "pb_ratio", "tier": "supporting"},
        {"metric_id": "ev_to_ebitda", "tier": "supporting"},
        # Context
        {"metric_id": "market_cap", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
        {"metric_id": "return_12m", "tier": "context"},
    ],
    # ================================================================
    # GROWTH
    # ================================================================
    "garp": [
        # Core
        {"metric_id": "peg_ratio", "tier": "core"},
        {"metric_id": "eps_growth_yoy", "tier": "core"},
        {"metric_id": "revenue_growth_yoy", "tier": "core"},
        # Supporting
        {"metric_id": "pe_ratio", "tier": "supporting"},
        {"metric_id": "roic", "tier": "supporting"},
        {"metric_id": "roe", "tier": "supporting"},
        {"metric_id": "revenue_growth_consistency_3y", "tier": "supporting"},
        # Context
        {"metric_id": "debt_to_equity", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    "quality_growth": [
        # Core
        {"metric_id": "roic", "tier": "core"},
        {"metric_id": "roic_consistency_5y", "tier": "core"},
        {"metric_id": "revenue_growth_yoy", "tier": "core"},
        {"metric_id": "eps_growth_yoy", "tier": "core"},
        # Supporting
        {"metric_id": "gross_margin", "tier": "supporting"},
        {"metric_id": "fcf_margin", "tier": "supporting"},
        {"metric_id": "roe", "tier": "supporting"},
        {"metric_id": "revenue_growth_consistency_3y", "tier": "supporting"},
        {"metric_id": "earnings_consistency_5y", "tier": "supporting"},
        # Context
        {"metric_id": "pe_ratio", "tier": "context"},
        {"metric_id": "peg_ratio", "tier": "context"},
        {"metric_id": "debt_to_equity", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    # ================================================================
    # INCOME
    # ================================================================
    "dividend_growth": [
        # Core
        {"metric_id": "dividend_yield", "tier": "core"},
        {"metric_id": "dividend_growth_rate_5y", "tier": "core"},
        {"metric_id": "dividend_growth_consistency_5y", "tier": "core"},
        # Supporting
        {"metric_id": "payout_ratio", "tier": "supporting"},
        {"metric_id": "fcf_margin", "tier": "supporting"},
        {"metric_id": "earnings_consistency_5y", "tier": "supporting"},
        {"metric_id": "debt_to_equity", "tier": "supporting"},
        # Context
        {"metric_id": "roe", "tier": "context"},
        {"metric_id": "pe_ratio", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
    ],
    "shareholder_yield": [
        # Core
        {"metric_id": "shareholder_yield", "tier": "core"},
        {"metric_id": "dividend_yield", "tier": "core"},
        {"metric_id": "net_buyback_yield", "tier": "core"},
        {"metric_id": "net_debt_reduction_rate", "tier": "core"},
        # Supporting
        {"metric_id": "fcf_margin", "tier": "supporting"},
        {"metric_id": "payout_ratio", "tier": "supporting"},
        {"metric_id": "roic", "tier": "supporting"},
        # Context
        {"metric_id": "debt_to_equity", "tier": "context"},
        {"metric_id": "pe_ratio", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    # ================================================================
    # FACTOR
    # ================================================================
    "quality_factor": [
        # Core
        {"metric_id": "roic", "tier": "core"},
        {"metric_id": "roe", "tier": "core"},
        {"metric_id": "gross_margin", "tier": "core"},
        {"metric_id": "roe_stability_5y", "tier": "core"},
        # Supporting
        {"metric_id": "fcf_margin", "tier": "supporting"},
        {"metric_id": "debt_to_equity", "tier": "supporting"},
        {"metric_id": "earnings_consistency_5y", "tier": "supporting"},
        {"metric_id": "earnings_volatility_5y", "tier": "supporting"},
        # Context
        {"metric_id": "pe_ratio", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
    ],
    "low_volatility": [
        # Core
        {"metric_id": "volatility_1y", "tier": "core"},
        {"metric_id": "beta", "tier": "core"},
        {"metric_id": "downside_deviation", "tier": "core"},
        {"metric_id": "max_drawdown_1y", "tier": "core"},
        {"metric_id": "portfolio_volatility", "tier": "core"},
        # Supporting
        {"metric_id": "ulcer_index", "tier": "supporting"},
        {"metric_id": "debt_to_equity", "tier": "supporting"},
        {"metric_id": "earnings_volatility_5y", "tier": "supporting"},
        {"metric_id": "sharpe_ratio", "tier": "supporting"},
        {"metric_id": "sortino_ratio", "tier": "supporting"},
        {"metric_id": "max_risk_contribution", "tier": "supporting"},
        # Context
        {"metric_id": "roic", "tier": "context"},
        {"metric_id": "dividend_yield", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    "price_momentum": [
        # Core
        {"metric_id": "return_12m", "tier": "core"},
        {"metric_id": "return_6m", "tier": "core"},
        {"metric_id": "return_3m", "tier": "core"},
        {"metric_id": "relative_strength", "tier": "core"},
        # Supporting
        {"metric_id": "pct_from_52w_high", "tier": "supporting"},
        {"metric_id": "pct_from_52w_low", "tier": "supporting"},
        {"metric_id": "up_capture_ratio", "tier": "supporting"},
        # Context
        {"metric_id": "volatility_1y", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    "multi_factor": [
        # Core — 5개 합성 지표
        {"metric_id": "composite_value", "tier": "core"},
        {"metric_id": "composite_quality", "tier": "core"},
        {"metric_id": "composite_growth", "tier": "core"},
        {"metric_id": "composite_momentum", "tier": "core"},
        {"metric_id": "composite_low_vol", "tier": "core"},
        # Supporting — 대표 개별 지표
        {"metric_id": "pe_ratio", "tier": "supporting"},
        {"metric_id": "roic", "tier": "supporting"},
        {"metric_id": "eps_growth_yoy", "tier": "supporting"},
        {"metric_id": "return_12m", "tier": "supporting"},
        {"metric_id": "volatility_1y", "tier": "supporting"},
        # Context
        {"metric_id": "market_cap", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
    ],
    # ================================================================
    # SPECIAL
    # ================================================================
    "contrarian": [
        # Core
        {"metric_id": "pe_ratio", "tier": "core"},
        {"metric_id": "pb_ratio", "tier": "core"},
        {"metric_id": "pct_from_52w_high", "tier": "core"},
        {"metric_id": "f_score_total", "tier": "core"},
        # Supporting
        {"metric_id": "ev_to_ebitda", "tier": "supporting"},
        {"metric_id": "roic", "tier": "supporting"},
        {"metric_id": "fcf_margin", "tier": "supporting"},
        {"metric_id": "debt_to_equity", "tier": "supporting"},
        {"metric_id": "volume_change_ratio", "tier": "supporting"},
        # Context
        {"metric_id": "return_12m", "tier": "context"},
        {"metric_id": "beta", "tier": "context"},
        {"metric_id": "market_cap", "tier": "context"},
    ],
    "concentrated_portfolio": [
        # Core — 포트폴리오 구조 지표
        {"metric_id": "hhi_concentration", "tier": "core"},
        {"metric_id": "sector_hhi", "tier": "core"},
        {"metric_id": "top3_weight", "tier": "core"},
        {"metric_id": "holding_count", "tier": "core"},
        {"metric_id": "portfolio_beta", "tier": "core"},
        {"metric_id": "max_position_weight", "tier": "core"},
        {"metric_id": "avg_correlation", "tier": "core"},
        # Supporting
        {"metric_id": "avg_market_cap", "tier": "supporting"},
        {"metric_id": "dividend_yield_portfolio", "tier": "supporting"},
        # Context
        {"metric_id": "roic", "tier": "context"},
        {"metric_id": "volatility_1y", "tier": "context"},
        {"metric_id": "portfolio_volatility", "tier": "context"},
    ],
}


# direction_override가 필요한 경우를 위한 기본값 추가
for _preset_id, _metrics_list in PRESET_METRICS.items():
    for _entry in _metrics_list:
        _entry.setdefault("direction_override", None)


# ---- Helper ----
def get_preset_metrics(preset_id: str) -> list[dict]:
    """프리셋의 지표 목록 조회."""
    return PRESET_METRICS[preset_id]


def get_core_metrics(preset_id: str) -> list[dict]:
    """프리셋의 Core 계층 지표만."""
    return [m for m in PRESET_METRICS[preset_id] if m["tier"] == "core"]


def get_metrics_for_tier(preset_id: str, tier: str) -> list[dict]:
    """프리셋의 특정 계층 지표."""
    return [m for m in PRESET_METRICS[preset_id] if m["tier"] == tier]
