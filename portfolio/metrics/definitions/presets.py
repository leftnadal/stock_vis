"""
Stock-Vis Preset Definitions (코드 상수)
=========================================

설계서 v3.1 기반 MVP 12개 프리셋.
이 파일이 프리셋 정의의 Single Source of Truth.
"""

PRESETS = {
    # ---- Value (2개) ----
    "buffett_quality_value": {
        "display_name": "Buffett Quality Value",
        "category": "value",
        "description": "워렌 버핏 스타일. 높은 ROIC와 안정적 이익을 합리적 가격에 보유.",
        "icon": "shield-check",
    },
    "piotroski_f_score": {
        "display_name": "Piotroski F-Score",
        "category": "value",
        "description": "조지프 피오트로스키 F-Score 기반. 재무 건전성 9개 항목 체크리스트.",
        "icon": "clipboard-check",
    },

    # ---- Growth (2개) ----
    "garp": {
        "display_name": "GARP",
        "category": "growth",
        "description": "합리적 가격의 성장주. PEG 비율 중심으로 성장과 밸류에이션 균형.",
        "icon": "trending-up",
    },
    "quality_growth": {
        "display_name": "Quality Growth / Compounder",
        "category": "growth",
        "description": "높은 수익성과 일관된 성장을 겸비한 복리 성장 기업.",
        "icon": "zap",
    },

    # ---- Income (2개) ----
    "dividend_growth": {
        "display_name": "Dividend Growth",
        "category": "income",
        "description": "배당 성장 투자. 꾸준히 배당을 늘려온 기업 중심.",
        "icon": "dollar-sign",
    },
    "shareholder_yield": {
        "display_name": "Shareholder Yield",
        "category": "income",
        "description": "배당 + 자사주 매입 + 부채 감소를 합산한 총 주주환원.",
        "icon": "gift",
    },

    # ---- Factor (4개) ----
    "quality_factor": {
        "display_name": "Quality Factor",
        "category": "factor",
        "description": "학술적 퀄리티 팩터. 수익성·안정성·재무 건전성의 팩터 관점 분석.",
        "icon": "award",
    },
    "low_volatility": {
        "display_name": "Low Volatility",
        "category": "factor",
        "description": "저변동성 이상현상. 변동성이 낮은 종목이 장기적으로 위험 대비 수익이 우수.",
        "icon": "anchor",
    },
    "price_momentum": {
        "display_name": "Price Momentum",
        "category": "factor",
        "description": "가격 모멘텀 팩터. 최근 상승세가 지속되는 종목.",
        "icon": "rocket",
    },
    "multi_factor": {
        "display_name": "Multi-Factor",
        "category": "factor",
        "description": "밸류·퀄리티·성장·모멘텀·저변동성 5개 팩터 합성 분석.",
        "icon": "layers",
    },

    # ---- Special (2개) ----
    "contrarian": {
        "display_name": "Contrarian",
        "category": "special",
        "description": "역발상 투자. 시장에서 저평가된 종목 중 펀더멘털이 건전한 기업 발굴.",
        "icon": "refresh-ccw",
    },
    "concentrated_portfolio": {
        "display_name": "Concentrated Portfolio",
        "category": "special",
        "description": "집중 투자 분석. 소수 종목에 집중할 때의 구조적 리스크와 확신도 진단.",
        "icon": "target",
    },
}


# ---- Helper ----
def get_preset(preset_id: str) -> dict:
    """preset_id로 프리셋 정의 조회."""
    return PRESETS[preset_id]


def get_presets_by_category(category: str) -> dict:
    """카테고리별 프리셋 필터."""
    return {k: v for k, v in PRESETS.items() if v["category"] == category}


def get_all_preset_ids() -> list[str]:
    """전체 preset_id 목록."""
    return list(PRESETS.keys())
