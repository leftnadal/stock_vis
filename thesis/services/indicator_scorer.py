"""Stage 1: Indicator Scoring - Robust Z + Decay (수학 모델 v2.3.2, Section 3)"""

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
    """지표별 스코어링 파라미터 조회."""
    return {
        'epsilon': indicator.epsilon or EPSILON_DEFAULTS.get(indicator.indicator_type, 0.01),
        'window': indicator.window or 20,
        'decay': indicator.decay or 0.95,
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
        dict with score, raw_z, is_extreme_vol, effective_window, is_neutral_mad
    """
    effective_window = min(window, len(readings))

    if effective_window < 5:
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


def score_indicator_from_model(indicator, as_of_date=None):
    """
    ThesisIndicator 모델 인스턴스로부터 score 계산.
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
