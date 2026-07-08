"""Stage 2: Monitor Aggregation (수학 모델 v2.3.2, Section 4 이식·평탄화).

MON-P2-S2 이식: 구 premise_aggregator를 Monitor 직접 집계로 재배선.
Monitor 재정의(ADR D-MONITOR-REBUILD)에서 premise 중간 계층을 제거 →
지표를 Monitor 레벨에서 곧바로 가중평균한다. 최약고리·불일치·유형편향 판정은
Monitor 레벨로 흡수(구 aggregate_thesis + diversity 로직 병합).
"""

import logging
from collections import Counter

logger = logging.getLogger(__name__)

TYPE_LABELS = {
    'market_data': '시장 데이터',
    'macro': '거시경제',
    'sentiment': '뉴스 심리',
    'technical': '기술적 분석',
    'custom': '사용자 정의',
}

WEAKEST_LINK_THRESHOLD = -0.5
DIVERGENCE_MINORITY_RATIO = 0.3
BIAS_MIN_INDICATORS = 5
BIAS_RATIO = 0.6


def aggregate_monitor(monitor, indicator_scores):
    """
    Monitor 종합 점수를 지표 점수 가중평균으로 집계.

    Args:
        monitor: Monitor 인스턴스
        indicator_scores: dict {indicator_id(str): score_or_None}

    Returns:
        dict with overall_score, weakest_link, divergence, bias_warning,
              category_overlap
    """
    indicators = list(monitor.indicators.filter(is_active=True, is_paused=False))

    scores = []
    weights = []
    for ind in indicators:
        s = indicator_scores.get(str(ind.id))
        # None -> 0.0 (수학 모델 12.1 확정)
        scores.append(s if s is not None else 0.0)
        weights.append(ind.weight)

    if not scores:
        return {
            'overall_score': 0.0,
            'weakest_link': None,
            'divergence': False,
            'bias_warning': None,
            'category_overlap': None,
        }

    # 가중평균: T = sum(w_i * s_i) / sum(w_i)
    total_weight = sum(weights)
    if total_weight == 0:
        overall_score = 0.0
    else:
        overall_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

    # 최약고리: score < -0.5인 지표 중 최저
    weakest = None
    for ind, s in zip(indicators, scores):
        if s < WEAKEST_LINK_THRESHOLD and (weakest is None or s < weakest['score']):
            weakest = {
                'indicator_id': str(ind.id),
                'indicator_name': ind.name,
                'score': s,
            }

    # 불일치: 양수/음수 혼재 소수 비율 >= 0.3
    positive_count = sum(1 for s in scores if s > 0)
    negative_count = sum(1 for s in scores if s < 0)
    total = len(scores)
    divergence = False
    if total >= 2:
        minority = min(positive_count, negative_count)
        if minority / total >= DIVERGENCE_MINORITY_RATIO:
            divergence = True

    return {
        'overall_score': round(overall_score, 4),
        'weakest_link': weakest,
        'divergence': divergence,
        'bias_warning': _check_indicator_bias(indicators),
        'category_overlap': _check_category_overlap(indicators),
    }


def _check_category_overlap(indicators):
    """같은 유형 지표 2개 이상이면 중복 경고."""
    types = [ind.indicator_type for ind in indicators]
    duplicates = {t: c for t, c in Counter(types).items() if c >= 2}
    if duplicates:
        dup_names = [f'{TYPE_LABELS.get(t, t)} {c}개' for t, c in duplicates.items()]
        return {
            'type': 'indicator_overlap',
            'scope': 'monitor',
            'severity': 'info',
            'message': f'같은 유형의 지표가 겹쳐요 ({", ".join(dup_names)}).',
        }
    return None


def _check_indicator_bias(indicators):
    """한 유형이 60% 이상이면 편향 경고. 지표 5개 이상일 때만."""
    all_types = [ind.indicator_type for ind in indicators]
    total = len(all_types)
    if total < BIAS_MIN_INDICATORS:
        return None
    for t, c in Counter(all_types).items():
        if c / total >= BIAS_RATIO:
            return {
                'type': 'indicator_bias',
                'scope': 'monitor',
                'severity': 'info',
                'message': f'전체 지표 {total}개 중 {TYPE_LABELS.get(t, t)}가 {c}개예요.',
            }
    return None
