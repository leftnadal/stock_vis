"""Snapshot Builder (수학 모델 v2.3.2, Section 9)"""

import logging
from datetime import date

from django.utils import timezone

from thesis.models import ThesisSnapshot
from thesis.services.arrow_calculator import score_to_degree
from thesis.services.indicator_scorer import score_indicator_from_model, check_extreme_volatility
from thesis.services.premise_aggregator import aggregate_premise, aggregate_thesis
from thesis.services.thesis_state_machine import determine_state

logger = logging.getLogger(__name__)


def build_snapshot(thesis, as_of_date=None):
    """
    가설의 일일 스냅샷을 생성.

    구현 (수학 모델 Section 9):
    1. as_of_date가 None이면 오늘 날짜 사용
    2. Universe 고정: thesis.indicator_universe_ids 사용
    3. universe 내 각 지표에 대해 score 계산
    4. None -> 0.0 대체는 aggregate_thesis()에서만 (스냅샷은 None 보존)
    5. data_coverage = 유효 score 수 / universe 전체 수
    6. unique_together=['thesis','asof_date'] 충돌 시 update
    7. notable_changes: 이전 스냅샷 대비 |score 변화| >= 0.3

    Returns:
        ThesisSnapshot 인스턴스
    """
    if as_of_date is None:
        as_of_date = date.today()

    # Universe 고정
    indicator_ids = thesis.indicator_universe_ids
    if not indicator_ids:
        active_indicators = thesis.indicators.filter(is_active=True).order_by('created_at')
        indicator_ids = [str(ind.id) for ind in active_indicators]
        thesis.indicator_universe_ids = indicator_ids
        thesis.save(update_fields=['indicator_universe_ids'])

    # 각 지표 score 계산
    indicator_scores = {}  # {id_str: score_or_None}
    indicator_names = {}
    indicator_degrees = {}
    extreme_vol_indicators = []

    for ind_id_str in indicator_ids:
        try:
            indicator = thesis.indicators.get(id=ind_id_str)
        except Exception:
            indicator_scores[ind_id_str] = None
            continue

        # 비활성/일시정지 -> None
        if not indicator.is_active or indicator.is_paused:
            indicator_scores[ind_id_str] = None
            continue

        result = score_indicator_from_model(indicator, as_of_date)
        score = result['score']
        indicator_scores[ind_id_str] = score
        indicator_names[ind_id_str] = indicator.name
        indicator_degrees[ind_id_str] = score_to_degree(score)

        # DB 업데이트: current_score, current_degree, current_color, current_label
        from thesis.services.arrow_calculator import degree_to_color, degree_to_label
        degree = score_to_degree(score)
        indicator.current_score = score
        indicator.current_degree = degree
        indicator.current_color = degree_to_color(degree)
        indicator.current_label = degree_to_label(degree)
        indicator.save(update_fields=[
            'current_score', 'current_degree', 'current_color', 'current_label',
        ])

        # Extreme Volatility 체크
        ev = check_extreme_volatility(result.get('raw_z', 0.0), indicator)
        if ev:
            extreme_vol_indicators.append(ev)

    # data_coverage
    total_count = len(indicator_ids)
    valid_count = sum(1 for v in indicator_scores.values() if v is not None)
    data_coverage = valid_count / total_count if total_count > 0 else 0.0

    # 전제별 점수 집계
    premise_scores = {}
    for premise in thesis.premises.filter(is_active=True, is_paused=False):
        result = aggregate_premise(premise, indicator_scores)
        premise_scores[str(premise.id)] = result['score']

    # 가설 전체 점수 집계
    thesis_result = aggregate_thesis(thesis, premise_scores, indicator_scores)
    overall_score = thesis_result['overall_score']

    # 이전 스냅샷 조회
    prev_snapshot = ThesisSnapshot.objects.filter(
        thesis=thesis,
        asof_date__lt=as_of_date,
    ).order_by('-asof_date').first()

    # notable_changes: 이전 대비 |score 변화| >= 0.3
    notable_changes = []
    if prev_snapshot and prev_snapshot.universe_snapshot:
        for ind_id, curr_score in indicator_scores.items():
            if curr_score is None:
                continue
            prev_score = prev_snapshot.universe_snapshot.get(ind_id)
            if prev_score is None:
                continue
            delta = abs(curr_score - prev_score)
            if delta >= 0.3:
                notable_changes.append({
                    'indicator_id': ind_id,
                    'indicator_name': indicator_names.get(ind_id, ind_id),
                    'prev_score': prev_score,
                    'curr_score': curr_score,
                    'delta': round(delta, 4),
                })

    # 상태 판정
    days_active = (timezone.now() - thesis.created_at).days
    prev_score = prev_snapshot.overall_score if prev_snapshot else None

    # 최근 5일 score_history
    recent_snapshots = ThesisSnapshot.objects.filter(
        thesis=thesis,
    ).order_by('-asof_date')[:5]
    score_history = [s.overall_score for s in reversed(recent_snapshots)]
    score_history.append(overall_score)

    state_result = determine_state(
        thesis=thesis,
        overall_score=overall_score,
        prev_score=prev_score,
        data_coverage=data_coverage,
        days_active=days_active,
        score_history=score_history,
    )

    # Snapshot 생성/업데이트 (upsert)
    snapshot, created = ThesisSnapshot.objects.update_or_create(
        thesis=thesis,
        asof_date=as_of_date,
        defaults={
            'data_coverage': round(data_coverage, 4),
            'universe_snapshot': indicator_scores,
            'ordered_indicator_ids': indicator_ids,
            'overall_score': overall_score,
            'state': state_result['state'],
            'premise_scores': premise_scores,
            'indicator_degrees': indicator_degrees,
            'notable_changes': notable_changes,
        },
    )

    # Thesis 상태 업데이트 (data_coverage >= 0.6일 때만)
    if data_coverage >= 0.6:
        update_fields = ['current_score', 'current_state']
        thesis.current_score = overall_score
        thesis.current_state = state_result['state']
        thesis.save(update_fields=update_fields)

    # 전체 결과를 scoring_result로 구성 (alert_engine에서 사용)
    scoring_result = {
        'indicator_scores': indicator_scores,
        'indicator_names': indicator_names,
        'indicator_degrees': indicator_degrees,
        'extreme_vol_indicators': extreme_vol_indicators,
        'premise_scores': premise_scores,
        'overall_score': overall_score,
        'weakest_link': thesis_result.get('weakest_link'),
        'divergence_count': thesis_result.get('divergence_count', 0),
        'thesis_bias_warning': thesis_result.get('thesis_bias_warning'),
        'state_result': state_result,
        'data_coverage': data_coverage,
    }

    return snapshot, scoring_result, prev_snapshot
