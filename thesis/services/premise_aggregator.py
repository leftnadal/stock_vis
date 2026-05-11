"""Stage 2: Premise Aggregation (수학 모델 v2.3.2, Section 4)"""

import logging
from collections import Counter

logger = logging.getLogger(__name__)

# extraction_level별 전제 가중치 (수학 모델 Section 4.1)
EXTRACTION_LEVEL_WEIGHTS = {
    'explicit': 1.0,
    'implicit': 0.8,
    'ai_suggested': 0.6,
}

TYPE_LABELS = {
    'market_data': '시장 데이터',
    'macro': '거시경제',
    'sentiment': '뉴스 심리',
    'technical': '기술적 분석',
    'custom': '사용자 정의',
}

WEAKEST_LINK_THRESHOLD = -0.5
DIVERGENCE_THRESHOLD = 1.2
THESIS_BIAS_MIN_INDICATORS = 5
THESIS_BIAS_RATIO = 0.6


def aggregate_premise(premise, indicator_scores):
    """
    전제 내 지표 점수를 가중평균으로 집계.

    Args:
        premise: ThesisPremise 인스턴스
        indicator_scores: dict {indicator_id(str): score_or_None}

    Returns:
        dict with score, weakest_link, divergence, category_overlap
    """
    indicators = premise.indicators.filter(is_active=True, is_paused=False)
    scores = []
    weights = []

    for ind in indicators:
        s = indicator_scores.get(str(ind.id))
        # None -> 0.0 (수학 모델 12.1 확정)
        score_val = s if s is not None else 0.0
        scores.append(score_val)
        weights.append(ind.weight)

    if not scores:
        return {
            'score': 0.0,
            'weakest_link': None,
            'divergence': False,
            'category_overlap': None,
        }

    # 가중평균: P_j = sum(w_ij * s_i) / sum(w_ij)
    total_weight = sum(weights)
    if total_weight == 0:
        premise_score = 0.0
    else:
        premise_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

    # 최약고리: score < -0.5인 지표
    weakest = None
    for ind, s in zip(indicators, scores):
        if s < WEAKEST_LINK_THRESHOLD:
            if weakest is None or s < weakest['score']:
                weakest = {
                    'indicator_id': str(ind.id),
                    'indicator_name': ind.name,
                    'score': s,
                }

    # 불일치: 양수/음수 혼재 비율 >= 0.3
    positive_count = sum(1 for s in scores if s > 0)
    negative_count = sum(1 for s in scores if s < 0)
    total = len(scores)
    divergence = False
    if total >= 2:
        minority = min(positive_count, negative_count)
        if minority / total >= 0.3:
            divergence = True

    # 카테고리 중복 (전제 레벨)
    category_overlap = _check_indicator_diversity_premise(indicators)

    return {
        'score': round(premise_score, 4),
        'weakest_link': weakest,
        'divergence': divergence,
        'category_overlap': category_overlap,
    }


def aggregate_thesis(thesis, premise_scores, indicator_scores):
    """
    가설 전체 점수를 전제 점수 가중평균으로 집계.

    Args:
        thesis: Thesis 인스턴스
        premise_scores: dict {premise_id(str): float}
        indicator_scores: dict {indicator_id(str): score_or_None}

    Returns:
        dict with overall_score, premise_scores, weakest_link,
              divergence_count, thesis_bias_warning, category_overlap_count
    """
    premises = thesis.premises.filter(is_active=True, is_paused=False)

    p_scores = []
    p_weights = []

    for premise in premises:
        pid = str(premise.id)
        score = premise_scores.get(pid, 0.0)
        weight = premise.weight
        p_scores.append(score)
        p_weights.append(weight)

    # T = sum(W_j * P_j) / sum(W_j)
    total_weight = sum(p_weights)
    if total_weight == 0 or not p_scores:
        overall_score = 0.0
    else:
        overall_score = sum(s * w for s, w in zip(p_scores, p_weights)) / total_weight

    # 최약고리 (전제 레벨)
    weakest = None
    for premise, score in zip(premises, p_scores):
        if score < WEAKEST_LINK_THRESHOLD:
            if weakest is None or score < weakest['score']:
                weakest = {
                    'premise_id': str(premise.id),
                    'premise_content': premise.content[:50],
                    'score': score,
                }

    # 불일치 (전제 간 방향 차이)
    divergence_count = 0
    if len(p_scores) >= 2:
        score_range = max(p_scores) - min(p_scores)
        if score_range > DIVERGENCE_THRESHOLD:
            divergence_count = 1

    # Thesis Bias (total >= 5일 때만)
    thesis_bias_warning = _check_indicator_diversity_thesis(thesis)

    # 카테고리 중복 (전체 레벨)
    category_overlap_count = 0
    for premise in premises:
        overlap = _check_indicator_diversity_premise(
            premise.indicators.filter(is_active=True, is_paused=False)
        )
        if overlap:
            category_overlap_count += 1

    return {
        'overall_score': round(overall_score, 4),
        'premise_scores': premise_scores,
        'weakest_link': weakest,
        'divergence_count': divergence_count,
        'thesis_bias_warning': thesis_bias_warning,
        'category_overlap_count': category_overlap_count,
    }


def _check_indicator_diversity_premise(indicators):
    """전제 내 같은 유형 지표 2개 이상이면 중복 경고."""
    types = [ind.indicator_type for ind in indicators]
    duplicates = {t: c for t, c in Counter(types).items() if c >= 2}
    if duplicates:
        dup_names = [f'{TYPE_LABELS.get(t, t)} {c}개' for t, c in duplicates.items()]
        return {
            'type': 'indicator_overlap',
            'scope': 'premise',
            'severity': 'info',
            'message': f'같은 유형의 지표가 겹쳐요 ({", ".join(dup_names)}).',
        }
    return None


def _check_indicator_diversity_thesis(thesis):
    """가설 전체에서 한 유형이 60% 이상이면 편향 경고. total >= 5일 때만."""
    premises = thesis.premises.filter(is_active=True, is_paused=False)
    all_types = []
    for premise in premises:
        for ind in premise.indicators.filter(is_active=True, is_paused=False):
            all_types.append(ind.indicator_type)

    total = len(all_types)
    if total < THESIS_BIAS_MIN_INDICATORS:
        return None

    for t, c in Counter(all_types).items():
        if c / total >= THESIS_BIAS_RATIO:
            return {
                'type': 'indicator_bias',
                'scope': 'thesis',
                'severity': 'info',
                'message': f'전체 지표 {total}개 중 {TYPE_LABELS.get(t, t)}가 {c}개예요.',
            }
    return None
