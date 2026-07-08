"""
상향 학습 D2 v5.1 — 태스크 배선 테스트 (트리거·본문·격벽·멱등).

설계: docs/features/chain-sight/PR_upward_loop_D2.md (⑨-C 코드 내 체인 트리거).
D1 순수 전이 로직은 test_upward_learning.py 참조(4-path).
"""

import logging
from unittest import mock

import pytest
from django.utils import timezone

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.tasks import relation_tasks

AGG_SVC = "apps.chain_sight.services.pair_aggregation.aggregate_relation_pairs"


def _reconfirmed_pair(status="stale", tier=1, score=80.0, category="truth"):
    """당회 재확인 pair (last_observed_at=오늘 auto_now, 비-market 텍스트 파생)."""
    return RelationConfidence.objects.create(
        symbol_a="AAA", symbol_b="BBB", relation_type="SUPPLIES_TO",
        relation_category=category, relation_status=status,
        truth_score=score, evidence_tier_best=tier,
    )


@pytest.mark.django_db
def test_flag_off_no_trigger_and_aggregate_unchanged(settings):
    """1) flag off → 트리거 미발사 + aggregate 결과 불변."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = False
    with mock.patch(AGG_SVC, return_value={"pairs": 3, "created": 3}), \
         mock.patch.object(relation_tasks.apply_upward_learning_task, "delay") as spy:
        result = relation_tasks.aggregate_relation_pairs_task.apply().get()
    assert result == {"pairs": 3, "created": 3}
    spy.assert_not_called()


@pytest.mark.django_db
def test_flag_on_triggers_upward(settings):
    """2a) flag on → aggregate 말미가 upward를 period 전달로 위임 발사."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    with mock.patch(AGG_SVC, return_value={"pairs": 3}), \
         mock.patch.object(relation_tasks.apply_upward_learning_task, "delay") as spy:
        result = relation_tasks.aggregate_relation_pairs_task.apply().get()
    assert result == {"pairs": 3}
    spy.assert_called_once()
    assert "period" in spy.call_args.kwargs  # 당회 period 전달


@pytest.mark.django_db
def test_upward_body_upgrades_reconfirmed_pair(settings):
    """2b) flag on 정상 경로: 재확인 Tier-1 pair(stale, score≥60) → fast-path 1단계 승급."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    period = timezone.now().date()
    p = _reconfirmed_pair(status="stale", tier=1, score=80.0)
    r = relation_tasks.apply_upward_learning_task.apply(
        kwargs={"period": period.isoformat()}).get()
    assert r["enabled"] is True
    assert r["evaluated"] == 1
    assert r["upgraded"] == 1
    assert r["fastpath"] == 1  # Tier-1 fast-path (streak 면제)
    p.refresh_from_db()
    assert p.relation_status == "probable"  # stale→probable 재획득
    assert p.fastpath_triggered_at is not None


@pytest.mark.django_db
def test_trigger_failure_isolated_from_aggregate(settings, caplog):
    """3) upward 트리거 실패(브로커 예외) → aggregate 성공 유지 + ERROR 로그 (P-6 격벽)."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    with mock.patch(AGG_SVC, return_value={"pairs": 3}), \
         mock.patch.object(relation_tasks.apply_upward_learning_task, "delay",
                           side_effect=RuntimeError("broker down")), \
         caplog.at_level(logging.ERROR, logger="apps.chain_sight.tasks.relation_tasks"):
        result = relation_tasks.aggregate_relation_pairs_task.apply().get()
    assert result == {"pairs": 3}  # 집계 결과 오염 없음
    assert "트리거 실패" in caplog.text


@pytest.mark.django_db
def test_idempotent_same_period(settings):
    """4) 동일 period 이중 실행 → 멱등(이중 상향 금지, last_computed_at 가드)."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    period = timezone.now().date()
    p = _reconfirmed_pair(status="stale", tier=1, score=80.0)

    r1 = relation_tasks.apply_upward_learning_task.apply(
        kwargs={"period": period.isoformat()}).get()
    assert r1["upgraded"] == 1
    p.refresh_from_db()
    assert p.relation_status == "probable"

    r2 = relation_tasks.apply_upward_learning_task.apply(
        kwargs={"period": period.isoformat()}).get()
    assert r2["evaluated"] == 0  # 멱등 가드로 재선별 안 됨
    assert r2["upgraded"] == 0
    p.refresh_from_db()
    assert p.relation_status == "probable"  # 이중 상향 없음


@pytest.mark.django_db
def test_market_relations_excluded(settings):
    """market 관계는 upward 대상 아님(update_relation_confidence가 직접 재산정 — 이중관리 방지)."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    period = timezone.now().date()
    _reconfirmed_pair(status="stale", tier=1, score=80.0, category="market")
    r = relation_tasks.apply_upward_learning_task.apply(
        kwargs={"period": period.isoformat()}).get()
    assert r["evaluated"] == 0
