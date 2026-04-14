"""
SEC-PR-14: 배치 후 품질 체크.

시간 기준: 대시보드=누적, 알림=최근 배치(hours_back).
7개 체크: 실패율, unknown, 매칭률, confidence, 큐 적체, dirty 적체, 섹션검증.
"""

import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Avg

logger = logging.getLogger(__name__)


def run_post_batch_quality_checks(hours_back: int = 24) -> list:
    """
    최근 배치 품질 체크. 알림 메시지 리스트 반환.

    Args:
        hours_back: 최근 N시간 기준

    Returns:
        list[str] — 경고 메시지 (비어있으면 양호)
    """
    from .models import (
        RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot,
        FilingProcessLog, UnmatchedCompanyQueue,
    )

    since = timezone.now() - timedelta(hours=hours_back)
    alerts = []

    # ── 1. 수집 실패율 ──
    recent_docs = RawDocumentStore.objects.filter(collected_at__gte=since)
    total = recent_docs.count()
    if total > 0:
        failed = recent_docs.filter(status='failed').count()
        fail_rate = failed / total
        if fail_rate > 0.20:
            alerts.append(
                f"⚠️ 수집 실패율 {fail_rate:.0%} ({failed}/{total}) — 20% 초과"
            )

    # ── 2. Track B unknown 비율 ──
    recent_bm = BusinessModelSnapshot.objects.filter(created_at__gte=since)
    bm_total = recent_bm.count()
    if bm_total > 0:
        unknown_count = 0
        fields = ['direct_customer_contact', 'contract_model',
                   'recurring_revenue_signal', 'channel_dependency',
                   'customer_concentration']
        for snap in recent_bm:
            for f in fields:
                if getattr(snap, f) == 'unknown':
                    unknown_count += 1
        unknown_rate = unknown_count / (bm_total * len(fields))
        if unknown_rate > 0.30:
            alerts.append(
                f"⚠️ Track B unknown 비율 {unknown_rate:.0%} — 30% 초과"
            )

    # ── 3. Ticker 매칭률 ──
    recent_ev = SupplyChainEvidence.objects.filter(extracted_at__gte=since)
    ev_total = recent_ev.count()
    if ev_total > 0:
        matched = recent_ev.filter(target_company__isnull=False).count()
        match_rate = matched / ev_total
        if match_rate < 0.30:
            alerts.append(
                f"⚠️ Ticker 매칭률 {match_rate:.0%} ({matched}/{ev_total}) — 30% 미만"
            )

    # ── 4. 평균 confidence ──
    if ev_total > 0:
        avg_conf = recent_ev.aggregate(avg=Avg('system_confidence'))['avg'] or 0
        if avg_conf < 0.5:
            alerts.append(
                f"⚠️ 평균 confidence {avg_conf:.2f} — 0.5 미만"
            )

    # ── 5. 미매칭 큐 적체 ──
    pending_queue = UnmatchedCompanyQueue.objects.filter(status='pending').count()
    if pending_queue > 100:
        alerts.append(
            f"⚠️ 미매칭 큐 적체 {pending_queue}건 — 100건 초과"
        )

    # ── 6. Neo4j dirty 적체 ──
    dirty_count = SupplyChainEvidence.objects.filter(
        neo4j_dirty=True, target_company__isnull=False
    ).count()
    if dirty_count > 50:
        alerts.append(
            f"⚠️ Neo4j dirty 적체 {dirty_count}건 — 50건 초과"
        )

    # ── 7. 섹션 검증 실패 ──
    fail_logs = FilingProcessLog.objects.filter(
        started_at__gte=since,
        stage='section_extract',
        detail__startswith='FAIL:',
    ).count()
    if fail_logs > 0:
        alerts.append(
            f"⚠️ 섹션 검증 실패 {fail_logs}건 (detail=FAIL:)"
        )

    if not alerts:
        logger.info(f"Quality checks passed (last {hours_back}h)")
    else:
        for a in alerts:
            logger.warning(a)

    return alerts


def get_dashboard_stats() -> dict:
    """
    Admin 대시보드용 누적 통계.
    """
    from .models import (
        RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot,
        UnmatchedCompanyQueue,
    )

    docs = RawDocumentStore.objects.all()
    evidences = SupplyChainEvidence.objects.all()
    bm = BusinessModelSnapshot.objects.all()
    queue = UnmatchedCompanyQueue.objects.all()

    return {
        'collection': {
            'total': docs.count(),
            'success': docs.filter(status='success').count(),
            'partial': docs.filter(status='partial').count(),
            'failed': docs.filter(status='failed').count(),
        },
        'track_a': {
            'total_evidences': evidences.count(),
            'matched': evidences.filter(target_company__isnull=False).count(),
            'unmatched': evidences.filter(target_company__isnull=True).count(),
            'neo4j_synced': evidences.filter(neo4j_dirty=False).count(),
            'neo4j_pending': evidences.filter(
                neo4j_dirty=True, target_company__isnull=False
            ).count(),
            'avg_confidence': round(
                evidences.aggregate(avg=Avg('system_confidence'))['avg'] or 0, 3
            ),
        },
        'track_b': {
            'total_snapshots': bm.count(),
            'high_grade': bm.filter(confidence_grade='high').count(),
            'medium_grade': bm.filter(confidence_grade='medium').count(),
            'low_grade': bm.filter(confidence_grade='low').count(),
        },
        'matching': {
            'queue_pending': queue.filter(status='pending').count(),
            'queue_matched': queue.filter(status='matched').count(),
            'queue_not_public': queue.filter(status='not_public').count(),
            'queue_person': queue.filter(status='person').count(),
            'queue_total': queue.count(),
        },
    }
