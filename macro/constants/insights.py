"""
Investment-Advisor 설계: 거시경제 인사이트 규칙

시장 상황별 메시지, 색상, 아이콘 등 프론트엔드 UX에 필요한 모든 상수 정의
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal


# ============================================================================
# 1. Fear & Greed Index (공포/탐욕 지수)
# ============================================================================

FEAR_GREED_RULES = {
    "extreme_fear": {
        "range": [0, 25],
        "label": "극단적 공포",
        "label_en": "Extreme Fear",
        "color": "#DC2626",  # red-600
        "bg_color": "#FEF2F2",  # red-50
        "icon": "TrendingDown",
        "message": "시장이 극도로 위축된 상태입니다. 역사적으로 이런 시기는 장기 투자자에게 매수 기회가 될 수 있습니다.",
        "action_hint": "분할 매수 검토",
        "education": {
            "title": "공포 구간의 의미",
            "content": "워런 버핏: '남들이 공포에 떨 때 탐욕을 부려라'. 다만 개별 종목의 펀더멘털 확인 필수.",
            "risk_level": "high"
        }
    },
    "fear": {
        "range": [25, 45],
        "label": "공포",
        "label_en": "Fear",
        "color": "#EA580C",  # orange-600
        "bg_color": "#FFF7ED",  # orange-50
        "icon": "TrendingDown",
        "message": "투자 심리가 위축되어 있습니다. 시장 변동성이 높을 수 있으니 주의가 필요합니다.",
        "action_hint": "관망 또는 신중한 매수",
        "education": {
            "title": "공포 구간에서의 투자",
            "content": "시장 심리가 부정적일 때는 급격한 반등과 추가 하락 모두 가능합니다. 분산 투자가 중요합니다.",
            "risk_level": "medium-high"
        }
    },
    "neutral": {
        "range": [45, 55],
        "label": "중립",
        "label_en": "Neutral",
        "color": "#6B7280",  # gray-500
        "bg_color": "#F9FAFB",  # gray-50
        "icon": "Minus",
        "message": "시장 심리가 균형 잡힌 상태입니다. 특별한 과열이나 공포 없이 정상적인 거래가 이루어지고 있습니다.",
        "action_hint": "기존 전략 유지",
        "education": {
            "title": "중립 구간의 특징",
            "content": "시장이 안정적인 시기입니다. 기업의 실적과 펀더멘털에 따라 종목별 움직임이 달라집니다.",
            "risk_level": "medium"
        }
    },
    "greed": {
        "range": [55, 75],
        "label": "탐욕",
        "label_en": "Greed",
        "color": "#16A34A",  # green-600
        "bg_color": "#F0FDF4",  # green-50
        "icon": "TrendingUp",
        "message": "투자 심리가 낙관적입니다. 상승 모멘텀이 있지만, 점차 주의가 필요한 구간에 진입하고 있습니다.",
        "action_hint": "이익 실현 검토",
        "education": {
            "title": "탐욕 구간의 주의점",
            "content": "상승장이 지속될 때 FOMO(놓칠 것에 대한 두려움)가 커집니다. 원칙에 따른 투자가 중요합니다.",
            "risk_level": "medium"
        }
    },
    "extreme_greed": {
        "range": [75, 100],
        "label": "극단적 탐욕",
        "label_en": "Extreme Greed",
        "color": "#059669",  # emerald-600
        "bg_color": "#ECFDF5",  # emerald-50
        "icon": "AlertTriangle",
        "message": "시장이 과열 구간입니다. 역사적으로 이런 시기에는 조정이 올 가능성이 높습니다. 리스크 관리에 주의하세요.",
        "action_hint": "신규 매수 자제, 리스크 관리",
        "education": {
            "title": "과열 구간의 위험",
            "content": "극단적 탐욕 구간에서 추격 매수는 위험합니다. 버핏: '남들이 탐욕을 부릴 때 공포를 가져라'",
            "risk_level": "high"
        }
    }
}


# ============================================================================
# 2. Yield Curve (수익률 곡선)
# ============================================================================

YIELD_CURVE_RULES = {
    "inverted": {
        "spread_range": [-float('inf'), 0],
        "label": "역전",
        "label_en": "Inverted",
        "color": "#DC2626",  # red-600
        "bg_color": "#FEF2F2",  # red-50
        "icon": "AlertOctagon",
        "message": "장단기 금리가 역전되었습니다. 역사적으로 경기 침체의 선행 지표로 여겨집니다.",
        "historical_note": "1970년 이후 모든 미국 경기침체 전 수익률 곡선이 역전되었습니다.",
        "typical_lag": "역전 후 평균 12-18개월 후 경기침체 시작",
        "education": {
            "title": "수익률 곡선 역전이란?",
            "content": "단기 국채 금리가 장기 국채 금리보다 높은 비정상적 상황입니다. 투자자들이 장기 경기에 비관적임을 나타냅니다.",
            "level": "intermediate"
        }
    },
    "flattening": {
        "spread_range": [0, 0.5],
        "label": "평탄화",
        "label_en": "Flattening",
        "color": "#F59E0B",  # amber-500
        "bg_color": "#FFFBEB",  # amber-50
        "icon": "Minus",
        "message": "장단기 금리 차이가 줄어들고 있습니다. 경기 사이클 후반부에 자주 나타나는 현상입니다.",
        "historical_note": "금리 인상 사이클 후반에 자주 발생합니다.",
        "typical_lag": "경기 정점까지 평균 6-12개월",
        "education": {
            "title": "수익률 곡선 평탄화",
            "content": "연준이 금리를 인상하면 단기 금리가 오르고, 장기 금리와의 차이가 줄어듭니다. 경기 과열 억제 신호입니다.",
            "level": "intermediate"
        }
    },
    "normal": {
        "spread_range": [0.5, 2.5],
        "label": "정상",
        "label_en": "Normal",
        "color": "#16A34A",  # green-600
        "bg_color": "#F0FDF4",  # green-50
        "icon": "CheckCircle",
        "message": "정상적인 수익률 곡선입니다. 장기 투자 수익률이 단기보다 높은 건강한 상태입니다.",
        "historical_note": "경기 확장기의 전형적인 모습입니다.",
        "typical_lag": "N/A - 안정적 경기 확장",
        "education": {
            "title": "정상적인 수익률 곡선",
            "content": "장기 투자가 더 높은 수익률을 제공하는 것이 정상입니다. 미래의 불확실성에 대한 프리미엄이 반영됩니다.",
            "level": "beginner"
        }
    },
    "steep": {
        "spread_range": [2.5, float('inf')],
        "label": "가파름",
        "label_en": "Steep",
        "color": "#2563EB",  # blue-600
        "bg_color": "#EFF6FF",  # blue-50
        "icon": "TrendingUp",
        "message": "수익률 곡선이 가파릅니다. 경기 회복 초기나 완화적 통화정책 시기에 나타납니다.",
        "historical_note": "경기 침체 후 회복기의 전형적 모습입니다.",
        "typical_lag": "경기 회복 초기 신호",
        "education": {
            "title": "가파른 수익률 곡선",
            "content": "연준이 금리를 낮추면 단기 금리가 하락하고, 경기 회복 기대로 장기 금리는 상대적으로 높아집니다.",
            "level": "intermediate"
        }
    }
}


# ============================================================================
# 3. Interest Rate Impact (금리 변동 영향)
# ============================================================================

RATE_IMPACT_RULES = {
    "rising_fast": {
        "change_range": [0.5, float('inf')],  # 6개월간 +0.5%p 이상
        "period_months": 6,
        "label": "급격한 상승",
        "label_en": "Rising Fast",
        "color": "#DC2626",
        "sectors": {
            "negative": ["부동산", "유틸리티", "성장주", "기술주"],
            "positive": ["금융", "보험"],
            "neutral": ["필수소비재", "헬스케어"]
        },
        "message": "금리가 빠르게 상승 중입니다. 성장주와 부채비율 높은 기업에 불리합니다.",
        "education": {
            "title": "금리 상승이 주식에 미치는 영향",
            "content": "금리가 오르면 미래 현금흐름의 현재가치가 낮아져 성장주에 불리합니다. 반면 은행은 예대마진 확대로 수혜.",
            "level": "intermediate"
        }
    },
    "rising_slow": {
        "change_range": [0.1, 0.5],
        "period_months": 6,
        "label": "완만한 상승",
        "label_en": "Rising Slowly",
        "color": "#F59E0B",
        "sectors": {
            "negative": ["부동산", "유틸리티"],
            "positive": ["금융", "산업재"],
            "neutral": ["기술주", "헬스케어"]
        },
        "message": "금리가 점진적으로 상승 중입니다. 건전한 경기 확장의 신호일 수 있습니다.",
        "education": {
            "title": "점진적 금리 인상",
            "content": "연준이 경기과열을 방지하며 연착륙을 유도하는 상황입니다. 시장이 적응할 시간이 있습니다.",
            "level": "beginner"
        }
    },
    "stable": {
        "change_range": [-0.1, 0.1],
        "period_months": 6,
        "label": "안정",
        "label_en": "Stable",
        "color": "#6B7280",
        "sectors": {
            "negative": [],
            "positive": [],
            "neutral": ["전 섹터 중립"]
        },
        "message": "금리가 안정적입니다. 시장이 현재 금리 수준에 적응한 상태입니다.",
        "education": {
            "title": "금리 동결기",
            "content": "연준이 관망하는 시기입니다. 경제 데이터에 따라 다음 방향이 결정됩니다.",
            "level": "beginner"
        }
    },
    "falling_slow": {
        "change_range": [-0.5, -0.1],
        "period_months": 6,
        "label": "완만한 하락",
        "label_en": "Falling Slowly",
        "color": "#16A34A",
        "sectors": {
            "negative": [],
            "positive": ["부동산", "유틸리티", "성장주"],
            "neutral": ["금융"]
        },
        "message": "금리가 점진적으로 하락 중입니다. 성장주와 배당주에 우호적인 환경입니다.",
        "education": {
            "title": "금리 인하 사이클",
            "content": "금리 하락은 주식의 상대적 매력을 높입니다. 특히 고배당주와 성장주가 수혜.",
            "level": "beginner"
        }
    },
    "falling_fast": {
        "change_range": [-float('inf'), -0.5],
        "period_months": 6,
        "label": "급격한 하락",
        "label_en": "Falling Fast",
        "color": "#2563EB",
        "sectors": {
            "negative": ["금융"],
            "positive": ["국채", "금", "유틸리티"],
            "neutral": []
        },
        "message": "금리가 급격히 하락 중입니다. 경기 침체 우려로 연준이 긴급 대응 중일 수 있습니다.",
        "education": {
            "title": "긴급 금리 인하",
            "content": "급격한 금리 인하는 보통 경제 위기 대응입니다. 안전자산 선호 현상이 나타날 수 있습니다.",
            "level": "intermediate"
        }
    }
}


# ============================================================================
# 4. Economic Calendar Importance (경제 이벤트 중요도)
# ============================================================================

CALENDAR_IMPORTANCE_RULES = {
    "critical": {
        "score": 3,
        "label": "매우 중요",
        "label_en": "Critical",
        "color": "#DC2626",
        "bg_color": "#FEF2F2",
        "icon": "AlertTriangle",
        "events": ["FOMC 금리결정", "고용보고서", "CPI", "GDP"],
        "market_impact": "시장 전체에 큰 변동성을 유발할 수 있습니다.",
        "preparation_tip": "발표 전 포지션 조정을 고려하세요."
    },
    "high": {
        "score": 2,
        "label": "중요",
        "label_en": "High",
        "color": "#F59E0B",
        "bg_color": "#FFFBEB",
        "icon": "AlertCircle",
        "events": ["소매판매", "ISM제조업", "개인소비지출", "주택지표"],
        "market_impact": "특정 섹터나 자산군에 영향을 줄 수 있습니다.",
        "preparation_tip": "관련 종목 보유 시 주의가 필요합니다."
    },
    "medium": {
        "score": 1,
        "label": "보통",
        "label_en": "Medium",
        "color": "#6B7280",
        "bg_color": "#F9FAFB",
        "icon": "Info",
        "events": ["산업생산", "소비자신뢰지수", "내구재주문"],
        "market_impact": "일반적으로 제한적인 영향을 미칩니다.",
        "preparation_tip": "참고용으로 확인하세요."
    }
}


# ============================================================================
# 5. VIX Level (변동성 지수)
# ============================================================================

VIX_RULES = {
    "extreme_high": {
        "range": [30, float('inf')],
        "label": "극단적 공포",
        "label_en": "Extreme Fear",
        "color": "#DC2626",
        "message": "시장 변동성이 매우 높습니다. 대규모 시장 이벤트나 위기 상황을 반영합니다.",
        "historical_context": "VIX 30 이상: 금융위기, 팬데믹 등 대형 이벤트 시 발생"
    },
    "high": {
        "range": [20, 30],
        "label": "높은 변동성",
        "label_en": "High Volatility",
        "color": "#F59E0B",
        "message": "변동성이 평균 이상입니다. 시장 불확실성이 높아진 상태입니다.",
        "historical_context": "VIX 20-30: 시장 조정기, 불확실성 증가 시"
    },
    "normal": {
        "range": [12, 20],
        "label": "정상 범위",
        "label_en": "Normal",
        "color": "#16A34A",
        "message": "변동성이 정상 범위입니다. 시장이 안정적으로 움직이고 있습니다.",
        "historical_context": "VIX 12-20: 일반적인 시장 상황"
    },
    "low": {
        "range": [0, 12],
        "label": "낮은 변동성",
        "label_en": "Low Volatility",
        "color": "#2563EB",
        "message": "변동성이 매우 낮습니다. 과도한 안심은 오히려 위험 신호일 수 있습니다.",
        "historical_context": "VIX 12 미만: 과도한 낙관, 급등락 전 나타나기도 함"
    }
}


# ============================================================================
# 6. 통합 상수
# ============================================================================

INSIGHT_RULES = {
    "fear_greed": FEAR_GREED_RULES,
    "yield_curve": YIELD_CURVE_RULES,
    "rate_impact": RATE_IMPACT_RULES,
    "calendar_importance": CALENDAR_IMPORTANCE_RULES,
    "vix": VIX_RULES
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_insight_message(category: str, value: float) -> Dict[str, Any]:
    """
    카테고리와 값에 따른 인사이트 메시지 반환

    Args:
        category: 'fear_greed', 'yield_curve', 'vix' 등
        value: 수치값

    Returns:
        해당 범위의 인사이트 규칙 딕셔너리
    """
    rules = INSIGHT_RULES.get(category, {})

    for rule_key, rule_data in rules.items():
        if 'range' in rule_data:
            min_val, max_val = rule_data['range']
            if min_val <= value < max_val:
                return {**rule_data, "rule_key": rule_key}
        elif 'spread_range' in rule_data:
            min_val, max_val = rule_data['spread_range']
            if min_val <= value < max_val:
                return {**rule_data, "rule_key": rule_key}
        elif 'change_range' in rule_data:
            min_val, max_val = rule_data['change_range']
            if min_val <= value < max_val:
                return {**rule_data, "rule_key": rule_key}

    return {}


def get_rate_impact_sectors(rate_change: float, period_months: int = 6) -> Dict[str, List[str]]:
    """
    금리 변화율에 따른 섹터별 영향 반환

    Args:
        rate_change: 금리 변화율 (예: 0.5 = +0.5%p)
        period_months: 변화 기간 (기본 6개월)

    Returns:
        섹터별 영향 딕셔너리 {'positive': [...], 'negative': [...], 'neutral': [...]}
    """
    for rule_key, rule_data in RATE_IMPACT_RULES.items():
        if rule_data.get('period_months') == period_months:
            min_val, max_val = rule_data['change_range']
            if min_val <= rate_change < max_val:
                return rule_data.get('sectors', {})

    return {"positive": [], "negative": [], "neutral": []}


def calculate_fear_greed_index(vix: float, yield_spread: float, market_momentum: float = 50) -> Dict[str, Any]:
    """
    Fear & Greed Index 계산 (VIX + Yield Spread 기반)

    Args:
        vix: VIX 지수 값
        yield_spread: 10년물-2년물 금리 차이 (%)
        market_momentum: 시장 모멘텀 점수 (0-100, 기본값 50)

    Returns:
        인덱스 값과 관련 메타데이터
    """
    # VIX 점수 (역산: VIX가 높을수록 공포)
    if vix >= 30:
        vix_score = 10
    elif vix >= 20:
        vix_score = 30
    elif vix >= 15:
        vix_score = 50
    elif vix >= 12:
        vix_score = 70
    else:
        vix_score = 85

    # Yield Spread 점수
    if yield_spread < 0:
        spread_score = 20  # 역전 = 공포
    elif yield_spread < 0.5:
        spread_score = 40  # 평탄화 = 우려
    elif yield_spread < 2.5:
        spread_score = 60  # 정상 = 중립~탐욕
    else:
        spread_score = 50  # 가파름 = 회복기

    # 가중 평균 (VIX 50%, Spread 30%, Momentum 20%)
    index_value = int(vix_score * 0.5 + spread_score * 0.3 + market_momentum * 0.2)
    index_value = max(0, min(100, index_value))  # 0-100 범위 제한

    insight = get_insight_message("fear_greed", index_value)

    return {
        "value": index_value,
        "components": {
            "vix_score": vix_score,
            "spread_score": spread_score,
            "momentum_score": market_momentum
        },
        **insight
    }
