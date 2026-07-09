"""Monitor 평가 파이프라인 end-to-end (MON-P2-S3).

evaluate_monitor: 지표 스코어 → 집계 → 스냅샷 upsert → 상태 판정 → Monitor 반영.
구 thesis eod_pipeline(update_readings→scores→snapshots)의 스코어 이후 단계를 한 함수로 통합.
실행 트리거는 수동(관리 커맨드 / API action) — beat 주기 등록은 별도 스텝(EOD 창 경합 설계 필요).
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.monitor.models import MonitorSnapshot
from apps.monitor.services.indicator_scorer import score_indicator_from_model
from apps.monitor.services.monitor_aggregator import aggregate_monitor
from apps.monitor.services.state_machine import determine_state

logger = logging.getLogger(__name__)


@transaction.atomic
def evaluate_monitor(monitor, as_of_date=None):
    """Monitor 하나를 평가하고 스냅샷·상태를 갱신한다.

    Returns: 평가 결과 dict (overall_score·state·지표별 점수·경고).
    """
    as_of = as_of_date or timezone.localdate()

    indicators = list(monitor.indicators.filter(is_active=True))

    indicator_scores = {}
    scored = 0    # active·non-paused 지표 수 (coverage 분모)
    covered = 0   # 그 중 충분한 실데이터 보유 수 (분자)
    for ind in indicators:
        res = score_indicator_from_model(ind, as_of_date=as_of)
        indicator_scores[str(ind.id)] = res['score']
        if not ind.is_paused:
            scored += 1
            if res.get('is_sufficient') and not res.get('is_paused'):
                covered += 1

    agg = aggregate_monitor(monitor, indicator_scores)
    overall_score = agg['overall_score']

    data_coverage = (covered / scored) if scored else 0.0

    # 과거 스냅샷 점수(현재 asof 이전) → prev_score·score_history
    prev_scores = list(
        monitor.snapshots.filter(asof_date__lt=as_of)
        .order_by('asof_date')
        .values_list('overall_score', flat=True)
    )
    prev_score = prev_scores[-1] if prev_scores else None
    score_history = prev_scores + [overall_score]  # 현재 포함, 시간순

    days_active = (as_of - monitor.created_at.date()).days

    state_res = determine_state(
        monitor, overall_score, prev_score, data_coverage, days_active, score_history
    )
    new_state = state_res['state']

    snapshot, _created = MonitorSnapshot.objects.update_or_create(
        monitor=monitor,
        asof_date=as_of,
        defaults={
            'overall_score': overall_score,
            'state': new_state,
            'data_coverage': round(data_coverage, 4),
        },
    )

    if monitor.current_state != new_state:
        monitor.current_state = new_state
        monitor.save(update_fields=['current_state', 'updated_at'])

    return {
        'monitor_id': str(monitor.id),
        'asof_date': as_of.isoformat(),
        'overall_score': overall_score,
        'state': new_state,
        'state_changed': state_res['state_changed'],
        'reminder_needed': state_res['reminder_needed'],
        'data_coverage': round(data_coverage, 4),
        'indicator_scores': indicator_scores,
        'weakest_link': agg['weakest_link'],
        'divergence': agg['divergence'],
        'bias_warning': agg['bias_warning'],
        'category_overlap': agg['category_overlap'],
        'snapshot_id': str(snapshot.id),
    }


def evaluate_monitors(queryset, as_of_date=None):
    """여러 Monitor를 평가. 개별 실패는 격리(로그)하고 계속 진행."""
    results = []
    for monitor in queryset:
        try:
            results.append(evaluate_monitor(monitor, as_of_date=as_of_date))
        except Exception:  # noqa: BLE001 — 배치 격리
            logger.exception("evaluate_monitor 실패: monitor_id=%s", monitor.id)
    return results
