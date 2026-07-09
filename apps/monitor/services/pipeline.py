"""Monitor 평가 파이프라인 end-to-end (MON-P2-S3).

evaluate_monitor: 지표 스코어 → 집계 → 스냅샷 upsert → 상태 판정 → Monitor 반영.
구 thesis eod_pipeline(update_readings→scores→snapshots)의 스코어 이후 단계를 한 함수로 통합.
실행 트리거는 수동(관리 커맨드 / API action) — beat 주기 등록은 별도 스텝(EOD 창 경합 설계 필요).
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.monitor.models import Monitor, MonitorSnapshot
from apps.monitor.services.indicator_scorer import score_indicator_from_model
from apps.monitor.services.ingest import BACKFILL_DAYS, ingest_readings_for_monitor
from apps.monitor.services.monitor_aggregator import aggregate_monitor
from apps.monitor.services.state_machine import determine_state

logger = logging.getLogger(__name__)


@transaction.atomic
def evaluate_monitor(monitor, as_of_date=None):
    """Monitor 하나를 평가하고 스냅샷·상태를 갱신한다.

    Returns: 평가 결과 dict (overall_score·state·지표별 점수·경고).
    """
    as_of = as_of_date or timezone.localdate()

    prev_state = monitor.current_state  # 전이 감지용(update 전 상태, MON-P3-ALERT)

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
        'prev_state': prev_state,
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


def refresh_monitor(monitor, backfill_days=BACKFILL_DAYS, as_of_date=None):
    """단일 Monitor를 refresh: ingest(EODSignal→Reading) → evaluate 체이닝.

    수동 커맨드(refresh_monitors)와 Celery beat 태스크가 **공유하는 단일 서비스 함수**
    (MON-P2-BEAT §3 — 커맨드/태스크는 이 함수를 각각 얇게 호출한다).
    반환 = 평가 결과 dict에 이식 증분(ingested)을 덧붙인 요약.
    """
    from datetime import date as _date

    from apps.monitor.services.alerts import (
        detect_and_record_alert,
        update_danger_streak,
    )

    ingest_results = ingest_readings_for_monitor(
        monitor, backfill_days=backfill_days, as_of_date=as_of_date
    )
    ingested = sum(r["ingested"] for r in ingest_results)
    result = evaluate_monitor(monitor, as_of_date=as_of_date)
    result["ingested"] = ingested

    # 전이 알림 감지 + 마감 제안 갱신 (MON-P3-ALERT, evaluate 직후 같은 흐름 — 신규 beat 없음)
    as_of = _date.fromisoformat(result["asof_date"])
    alert_res = detect_and_record_alert(monitor, result)
    newly_close_suggested = update_danger_streak(monitor, as_of)
    result["alert_created"] = bool(alert_res["created"])
    result["alert_suppressed"] = bool(alert_res["suppressed"])
    result["newly_close_suggested"] = newly_close_suggested
    return result


def refresh_monitors(queryset=None, backfill_days=BACKFILL_DAYS, as_of_date=None):
    """stock scope Monitor 전체(또는 주어진 queryset) refresh. 개별 실패는 격리.

    queryset 미지정 시 stock scope 전체가 대상(ingest 매핑이 stock scope 카탈로그 전제).
    """
    if queryset is None:
        queryset = Monitor.objects.filter(scope=Monitor.Scope.STOCK)
    results = []
    for monitor in queryset:
        try:
            results.append(
                refresh_monitor(monitor, backfill_days=backfill_days, as_of_date=as_of_date)
            )
        except Exception:  # noqa: BLE001 — 배치 격리
            logger.exception("refresh_monitor 실패: monitor_id=%s", monitor.id)
    return results
