"""D-RC-DECAY-SEMANTIC (RC-A-1 PART 1) — 감쇠 타입 게이트 회귀.

check_stale_and_decay가 DECAYABLE_RELATION_TYPES(재기록자 보유 타입)만 감쇠하고,
재기록자 없는 타입(PEER_OF·PRICE_CORRELATED)은 last_observed_at이 아무리 낡아도
status를 건드리지 않음을 고정한다. auto_now 동결로 인한 오발 감쇠(RC-A-0 실측: 2,054행
2026-09-18 일괄 stale 예약) 차단이 목적.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.tasks import relation_tasks


def _mk(symbol_b, relation_type, status="confirmed", category="truth"):
    """행 생성 후 last_observed_at을 200일 전으로 강제(auto_now 우회 update)."""
    rc = RelationConfidence.objects.create(
        symbol_a="AAA", symbol_b=symbol_b, relation_type=relation_type,
        relation_category=category, relation_status=status,
    )
    old = timezone.now() - timedelta(days=200)
    # auto_now 필드는 create 시 now로 세팅되므로 QuerySet.update로 소급 동결
    RelationConfidence.objects.filter(pk=rc.pk).update(last_observed_at=old)
    return rc


@pytest.mark.django_db
def test_excluded_types_never_decay_however_stale():
    """(a) 제외 타입(PEER_OF·PRICE_CORRELATED)은 last_observed 200일 낡아도 status 불변."""
    peer = _mk("PEE", "PEER_OF", status="confirmed")
    price = _mk("PRC", "PRICE_CORRELATED", status="confirmed")

    result = relation_tasks.check_stale_and_decay.apply().get()

    peer.refresh_from_db()
    price.refresh_from_db()
    assert peer.relation_status == "confirmed", "PEER_OF는 감쇠 대상 아님"
    assert price.relation_status == "confirmed", "PRICE_CORRELATED는 감쇠 대상 아님"
    assert result["decayed"] == 0


@pytest.mark.django_db
def test_decayable_confirmed_to_stale_isolated():
    """(b-1) 등재 타입 confirmed(>90d) → stale (bomb 전이). 기존 로직 그대로."""
    cm_conf = _mk("CM1", "CO_MENTIONED", status="confirmed", category="market")

    result = relation_tasks.check_stale_and_decay.apply().get()

    cm_conf.refresh_from_db()
    assert cm_conf.relation_status == "stale", "confirmed(>90d) → stale"
    assert result["decayed"] == 1
    # neo4j_dirty 토글 확인 (bulk update 경로)
    assert cm_conf.neo4j_dirty is True


@pytest.mark.django_db
def test_decayable_cascade_is_preserved():
    """(b-2) 등재 타입 순차 감쇠 — 원 함수의 사전존재 cascade 보존.

    한 실행 내 3개 .update()가 순차 적용되므로 probable(>60d)은 probable→weak 직후
    weak→hidden 필터에 재포착돼 hidden까지 연쇄한다. PART 1은 타입 게이트만 추가했고
    이 순차 동작은 무변경(지시서 6b "기존 로직 그대로")임을 고정한다.
    """
    cm_conf = _mk("CM1", "CO_MENTIONED", status="confirmed", category="market")
    sec_prob = _mk("SC1", "SUPPLIES_TO", status="probable")
    comp_weak = _mk("CP1", "COMPETES_WITH", status="weak")

    result = relation_tasks.check_stale_and_decay.apply().get()

    cm_conf.refresh_from_db()
    sec_prob.refresh_from_db()
    comp_weak.refresh_from_db()
    assert cm_conf.relation_status == "stale", "confirmed(>90d) → stale"
    assert sec_prob.relation_status == "hidden", "probable(>60d) → weak → (cascade) hidden"
    assert comp_weak.relation_status == "hidden", "weak(>30d) → hidden"
    # decayed = stale(1) + probable→weak(1) + weak→hidden(sec+comp=2) = 4
    assert result["decayed"] == 4


@pytest.mark.django_db
def test_mixed_only_decayable_moves():
    """등재+제외 혼재 시: 등재만 전이, 제외는 불변, decayed 카운트는 등재분만."""
    cm = _mk("CM2", "CO_MENTIONED", status="confirmed", category="market")
    peer = _mk("PE2", "PEER_OF", status="confirmed")

    result = relation_tasks.check_stale_and_decay.apply().get()

    cm.refresh_from_db()
    peer.refresh_from_db()
    assert cm.relation_status == "stale"
    assert peer.relation_status == "confirmed"
    assert result["decayed"] == 1


@pytest.mark.django_db
def test_empty_whitelist_is_noop():
    """(c) 빈 DECAYABLE 목록이면 어떤 타입도 감쇠 안 함 — no-op."""
    cm = _mk("CM3", "CO_MENTIONED", status="confirmed", category="market")

    with mock.patch.object(relation_tasks, "DECAYABLE_RELATION_TYPES", []):
        result = relation_tasks.check_stale_and_decay.apply().get()

    cm.refresh_from_db()
    assert cm.relation_status == "confirmed", "빈 화이트리스트 → no-op"
    assert result == {"decayed": 0}
