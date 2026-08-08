"""Stage 1: Indicator Scoring - Robust Z + Decay (수학 모델 v2.3.2, Section 3).

MON-P2-S2 이식: thesis/_reuse → apps/monitor. 소비 모델 = MonitorIndicator/IndicatorReading.
`score_indicator`는 순수 함수, `score_indicator_from_model`은 MonitorIndicator 인스턴스 소비.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)

MAD_FLOOR = 1e-9  # v2.3.2: 고정값 지표에서 z 과폭발 방지

EPSILON_DEFAULTS = {
    'market_data': 0.01,
    'macro': 0.5,
    'sentiment': 0.01,
    'technical': 1.0,
    'custom': 0.01,
}

EXTREME_VOL_THRESHOLD = 5.0  # |z_raw| >= 5.0


def get_scoring_params(indicator):
    """지표별 스코어링 파라미터 조회. 모델 기본값과 일치하도록 None 체크."""
    return {
        'epsilon': indicator.epsilon if indicator.epsilon is not None else EPSILON_DEFAULTS.get(indicator.indicator_type, 0.01),
        'window': indicator.window if indicator.window is not None else 60,
        'decay': indicator.decay if indicator.decay is not None else 0.95,
    }


def score_indicator(readings, dates, support_direction,
                    epsilon=0.01, window=20, decay=0.95):
    """
    지표 원시값 -> Robust Z -> 점수(-1~1) + 메타데이터.

    Args:
        readings: list[float] - validated reading 값 목록 (시간순)
        dates: list[date] - 대응하는 날짜 목록
        support_direction: 'positive' or 'negative'
        epsilon: Robust Z 분모 보호
        window: 히스토리 윈도우 (일)
        decay: 지수 감쇠 lambda

    Returns:
        dict with score, raw_z, is_extreme_vol, effective_window, is_neutral_mad, is_sufficient

    Note (MON-P2A 교정): 이 순수 함수는 **z 계산 가능성**만 게이트한다(robust median/MAD에
        필요한 최소 관측 5). 지표의 **충분성 정책**(min_n)은 여기서 판정하지 않는다 —
        min_n은 '오늘의 지표값을 만들 계산 소스(DailyPrice/EODSignal) 행수' 조건이므로
        readings(z 히스토리) 행수와 다른 범주다. 충분성은 source_n을 아는 상위 계층
        (score_indicator_from_model / score_indicator_dispatch)에서 판정한다.
    """
    n = len(readings)
    effective_window = min(window, n)

    # z 계산 최소선: robust median/MAD가 무의미해지는 n<5는 계산하지 않고 불충분 반환.
    if n < 5:
        return {
            'score': 0.0,
            'raw_z': 0.0,
            'is_extreme_vol': False,
            'effective_window': effective_window,
            'is_neutral_mad': False,
            'is_sufficient': False,
        }

    arr = np.array(readings[-effective_window:])
    dt = dates[-effective_window:]

    # Robust Z-score (MAD)
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))

    # v2.3.2: MAD Floor - 거의 안 움직이는 지표 보호
    if mad < MAD_FLOOR:
        return {
            'score': 0.0,
            'raw_z': 0.0,
            'is_extreme_vol': False,
            'effective_window': effective_window,
            'is_neutral_mad': True,
            'is_sufficient': True,
        }

    robust_sigma = 1.4826 * mad + epsilon
    z_scores = (arr - med) / robust_sigma

    # Extreme Vol (clip 전 raw z)
    z_raw = float(z_scores[-1])
    is_extreme_vol = abs(z_raw) >= EXTREME_VOL_THRESHOLD

    # Decay-weighted average
    today = dt[-1]
    weights = np.array([decay ** (today - d).days for d in dt])
    s_decayed = float(np.average(z_scores, weights=weights))

    # Clip & normalize -> [-1, 1]
    s = float(np.clip(s_decayed, -3, 3)) / 3

    # support_direction 반영
    if support_direction == 'negative':
        s = -s

    return {
        'score': round(s, 4),
        'raw_z': round(z_raw, 4),
        'is_extreme_vol': is_extreme_vol,
        'effective_window': effective_window,
        'is_neutral_mad': False,
        'is_sufficient': True,
    }


def source_row_count(indicator, entry, as_of_date=None):
    """지표의 **계산 소스 행수**(source_n)를 조회 (MON-P2A 교정).

    충분성 판정 기준 = '오늘의 지표값을 만들 원천 데이터가 min_n 이상인가'.
    catalog entry의 source 문자열로 소스 모델을 판별한다:
      - "stocks.DailyPrice ..." → DailyPrice 행수 (sma/momentum/w52/volume/macd/rsi)
      - "stocks.EODSignal ..."  → EODSignal 행수 (composite/change/dollar)
    종목 심볼 = indicator.monitor.target_ref (scope=stock 정규화). as_of_date가 있으면
    그 날짜 이하로 제한(백테스트·회귀 asof 정합). 소스 판별 불가 시 None(게이트 미적용).
    """
    source = (entry or {}).get("source", "")
    symbol = (getattr(indicator.monitor, "target_ref", "") or "").upper()
    if not symbol:
        return None
    if "DailyPrice" in source:
        from packages.shared.stocks.models import DailyPrice
        qs = DailyPrice.objects.filter(stock__symbol=symbol)
        if as_of_date:
            qs = qs.filter(date__lte=as_of_date)
        return qs.count()
    if "EODSignal" in source:
        from packages.shared.stocks.models import EODSignal
        qs = EODSignal.objects.filter(stock__symbol=symbol)
        if as_of_date:
            qs = qs.filter(date__lte=as_of_date)
        return qs.count()
    return None


def score_indicator_from_model(indicator, as_of_date=None):
    """
    MonitorIndicator 모델 인스턴스로부터 score 계산.
    DB에서 validated readings를 조회하여 score_indicator()에 전달.

    Returns:
        dict with score, raw_z, is_extreme_vol, effective_window, is_neutral_mad
    """
    # is_paused -> 중립 반환
    if indicator.is_paused:
        return {
            'score': 0.0,
            'raw_z': 0.0,
            'is_extreme_vol': False,
            'effective_window': 0,
            'is_neutral_mad': False,
            'is_sufficient': True,
            'is_paused': True,
        }

    # override_score -> 그 값 사용
    if indicator.override_score is not None:
        return {
            'score': round(float(indicator.override_score), 4),
            'raw_z': 0.0,
            'is_extreme_vol': False,
            'effective_window': 0,
            'is_neutral_mad': False,
            'is_sufficient': True,
            'is_override': True,
        }

    params = get_scoring_params(indicator)

    # validated readings 조회
    qs = indicator.readings.filter(
        validation_status__in=['ok', 'extreme_jump_allowed']
    ).order_by('asof')

    if as_of_date:
        qs = qs.filter(asof__date__lte=as_of_date)

    readings_qs = list(qs.values_list('value', 'asof'))
    if not readings_qs:
        return {
            'score': 0.0,
            'raw_z': 0.0,
            'is_extreme_vol': False,
            'effective_window': 0,
            'is_neutral_mad': False,
            'is_sufficient': False,
        }

    values = [r[0] for r in readings_qs if r[0] is not None]
    dates = [r[1].date() if hasattr(r[1], 'date') else r[1] for r in readings_qs if r[0] is not None]

    if not values:
        return {
            'score': 0.0,
            'raw_z': 0.0,
            'is_extreme_vol': False,
            'effective_window': 0,
            'is_neutral_mad': False,
            'is_sufficient': False,
        }

    # MON-P2A(교정): 충분성 = 계산 소스 행수(source_n) >= min_n(카탈로그 초안).
    # reading-count(IndicatorReading 행수)는 충분성 판정에 쓰지 않는다 — z 히스토리와
    # 계산 소스 유효성은 별개 범주(P2A 범주 오류 교정). source_n < min_n이면 계산하지
    # 않고 불충분 반환(무언 계산 금지) → aggregator가 재정규화로 제외.
    from apps.monitor.catalog import catalog_entry

    entry = catalog_entry("stock", indicator.source_key) if indicator.source_key else None
    min_n = entry.get("min_n") if entry else None

    if min_n is not None:
        source_n = source_row_count(indicator, entry, as_of_date)
        if source_n is not None and source_n < min_n:
            return {
                'score': 0.0,
                'raw_z': 0.0,
                'is_extreme_vol': False,
                'effective_window': 0,
                'is_neutral_mad': False,
                'is_sufficient': False,
                'source_n': source_n,
            }

    return score_indicator(
        values, dates, indicator.support_direction,
        epsilon=params['epsilon'],
        window=params['window'],
        decay=params['decay'],
    )


def check_extreme_volatility(z_raw, indicator):
    """극단적 변동 감지. |z_raw| >= 5.0이면 경고 dict 반환."""
    if abs(z_raw) >= EXTREME_VOL_THRESHOLD:
        return {
            'flag': 'extreme_volatility',
            'severity': 'critical',
            'z_raw': z_raw,
            'indicator_id': str(indicator.id),
            'indicator_name': indicator.name,
            'message': f'{indicator.name}에서 극단적 변동 감지 (z={z_raw:.1f})',
        }
    return None
