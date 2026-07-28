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


# ─────────────────────────── T-3b Phase A (①②③ⓔ) ───────────────────────────

def _make_pair(sym_a, sym_b, *, status="probable", tier=1, score=80.0,
               category="truth", rel_type="SUPPLIES_TO"):
    return RelationConfidence.objects.create(
        symbol_a=sym_a, symbol_b=sym_b, relation_type=rel_type,
        relation_category=category, relation_status=status,
        truth_score=score, evidence_tier_best=tier,
    )


@pytest.mark.django_db
def test_a_backfilled_pairs_not_reselected_until_reobserved(settings):
    """(a) ① 백필 후: last_observed==last_computed 정지 pair는 재선별 안 됨(콜드스타트 폭주 방지);
    재관측(last_observed>last_computed)된 pair만 evaluated."""
    from datetime import timedelta
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    t0 = timezone.now() - timedelta(days=2)
    stable = _make_pair("AAA", "BBB")  # 백필됨, 재관측 없음
    RelationConfidence.objects.filter(pk=stable.pk).update(
        last_observed_at=t0, last_computed_at=t0)
    reobs = _make_pair("CCC", "DDD")   # 재관측: last_observed > last_computed
    RelationConfidence.objects.filter(pk=reobs.pk).update(
        last_observed_at=timezone.now(), last_computed_at=t0)
    r = relation_tasks.apply_upward_learning_task.apply(kwargs={"period": None}).get()
    assert r["evaluated"] == 1  # reobs만 (stable은 gt 미충족)


@pytest.mark.django_db
def test_b_last_observed_at_unchanged_after_upward_save(settings):
    """(b) ② 자가오염 차단: upward save가 last_observed_at(auto_now)을 밀지 않음."""
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    p = _make_pair("AAA", "BBB", status="probable", tier=1, score=80.0)  # last_computed NULL
    p.refresh_from_db()
    before = p.last_observed_at
    relation_tasks.apply_upward_learning_task.apply(kwargs={"period": None}).get()
    p.refresh_from_db()
    assert p.last_observed_at == before      # 불변 (update_fields 제외)
    assert p.last_computed_at is not None     # 멱등 마커는 갱신


@pytest.mark.django_db
def test_c_processed_pair_not_reselected(settings):
    """(c) F() 멱등: last_computed_at >= last_observed_at 이면 재선별 안 됨."""
    from datetime import timedelta
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    now = timezone.now()
    p = _make_pair("AAA", "BBB")
    RelationConfidence.objects.filter(pk=p.pk).update(
        last_observed_at=now - timedelta(minutes=1), last_computed_at=now)
    r = relation_tasks.apply_upward_learning_task.apply(kwargs={"period": None}).get()
    assert r["evaluated"] == 0


@pytest.mark.django_db
def test_d_confirmed_pair_skipped_and_fastpath_preserved(settings):
    """(d) ⓔ: 이미 confirmed면 선별돼도 fast-path·save skip; fastpath_triggered_at 보존."""
    from datetime import timedelta
    settings.CHAINSIGHT_UPWARD_LEARNING_ENABLED = True
    witness = timezone.now() - timedelta(days=5)
    old_comp = timezone.now() - timedelta(days=3)
    p = _make_pair("AAA", "BBB", status="confirmed", tier=1, score=80.0)
    # 재관측되게(선별 대상) + witness/last_computed 고정
    RelationConfidence.objects.filter(pk=p.pk).update(
        last_observed_at=timezone.now(), last_computed_at=old_comp,
        fastpath_triggered_at=witness)
    r = relation_tasks.apply_upward_learning_task.apply(kwargs={"period": None}).get()
    assert r["evaluated"] == 1   # 선별은 됨
    assert r["upgraded"] == 0    # confirmed → skip
    p.refresh_from_db()
    assert p.relation_status == "confirmed"
    assert p.fastpath_triggered_at == witness   # 보존
    assert p.last_computed_at == old_comp        # skip = save 안 함 → 불변
