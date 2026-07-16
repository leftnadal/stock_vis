"""P2-IMPRESSION-BUILD-S2: impression 수신 API 테스트 (apps/platform).

구획 준수: tests/ 밖 in-app 배치(DoD = apps/platform/** 만).
경계 #43: IssuanceLog 무접촉 — ImpressionLog(serve-time)만 검증.
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient

import pytest

import apps.platform.api.views as views_mod
from packages.shared.stocks.models import ImpressionLog

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

URL = "/api/v1/telemetry/impressions"
User = get_user_model()


def _auth_client():
    user = User.objects.create_user(
        username="telemetry_u", email="t@example.com", password="pw12345!"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _imp(object_ref="AAPL:2026-07-14:V1"):
    return {
        "surface": "dashboard_eod",
        "object_ref": object_ref,
        "event_type": "impression",
        "session_id": "sess-1",
    }


def test_impression_first_receive_creates_row():
    client, user = _auth_client()
    resp = client.post(URL, [_imp()], format="json")
    assert resp.status_code == 200
    assert resp.data == {"received": 1, "rejected": 0, "rejected_reasons": {}}
    row = ImpressionLog.objects.get(event_type="impression")
    assert row.user_id == user.id
    assert row.seen_count == 1
    assert row.first_seen_at is not None


def test_impression_reingest_increments_and_keeps_first_seen():
    client, _ = _auth_client()
    client.post(URL, [_imp()], format="json")
    row1 = ImpressionLog.objects.get(event_type="impression")
    first_seen_before = row1.first_seen_at

    client.post(URL, [_imp()], format="json")  # 동일 3중 키 재수신
    assert ImpressionLog.objects.filter(event_type="impression").count() == 1
    row2 = ImpressionLog.objects.get(event_type="impression")
    assert row2.seen_count == 2
    assert row2.first_seen_at == first_seen_before  # 불변


def test_click_always_appends():
    client, _ = _auth_client()
    click = {
        "surface": "news_chip",
        "object_ref": "chip-7",
        "event_type": "click",
        "session_id": "sess-1",
    }
    client.post(URL, [click], format="json")
    client.post(URL, [click], format="json")
    assert ImpressionLog.objects.filter(event_type="click").count() == 2


def test_unauthenticated_rejected():
    resp = APIClient().post(URL, [_imp()], format="json")
    assert resp.status_code in (401, 403)
    assert ImpressionLog.objects.count() == 0


def test_mixed_batch_processes_valid_and_counts_rejects():
    client, _ = _auth_client()
    batch = [
        _imp("A:1"),                                   # 유효
        {"surface": "bogus", "object_ref": "x",
         "event_type": "impression", "session_id": "s"},  # 무효 surface
        {"surface": "dashboard_eod", "object_ref": "y",
         "event_type": "hover", "session_id": "s"},        # 무효 event_type
        {"surface": "dashboard_eod",
         "event_type": "click", "session_id": "s"},        # object_ref 누락
        {"surface": "chain_sight", "object_ref": "z",
         "event_type": "click", "session_id": "s"},        # 유효
    ]
    resp = client.post(URL, batch, format="json")
    assert resp.status_code == 200
    assert resp.data == {
        "received": 2,
        "rejected": 3,
        "rejected_reasons": {"invalid": 3},
    }
    assert ImpressionLog.objects.count() == 2


def test_all_valid_multi_item_batch_all_received():
    """⑴ 정상 배치(전 항목 유효) 전량 수신."""
    client, _ = _auth_client()
    batch = [
        _imp("A:1"),
        _imp("B:2"),
        {"surface": "news_chip", "object_ref": "chip-9",
         "event_type": "click", "session_id": "s"},
    ]
    resp = client.post(URL, batch, format="json")
    assert resp.status_code == 200
    assert resp.data == {"received": 3, "rejected": 0, "rejected_reasons": {}}
    assert ImpressionLog.objects.count() == 3


def test_db_error_isolated_per_item(monkeypatch):
    """⑵ 혼합 배치(정상 + 구조적 DB 오류)에서 정상분 전량 수신 + db_error 집계.

    한 항목의 _record가 IntegrityError(=DatabaseError 계열)를 던져도 배치 전체가
    500이 아니라, 그 항목만 rejected(db_error)로 격리되고 정상 항목은 수신된다.
    """
    client, _ = _auth_client()
    real_record = views_mod._record

    def flaky(user_id, ev, now):
        if ev["object_ref"] == "BOOM":
            raise IntegrityError("induced structural error")
        return real_record(user_id, ev, now)

    monkeypatch.setattr(views_mod, "_record", flaky)

    batch = [_imp("A:1"), _imp("BOOM"), _imp("B:2")]
    resp = client.post(URL, batch, format="json")
    assert resp.status_code == 200
    assert resp.data == {
        "received": 2,
        "rejected": 1,
        "rejected_reasons": {"db_error": 1},
    }
    # 정상 2건만 실제 저장(격리 항목은 savepoint rollback으로 미저장)
    assert ImpressionLog.objects.count() == 2
    assert not ImpressionLog.objects.filter(object_ref="BOOM").exists()


def test_all_items_fail_still_2xx(monkeypatch):
    """⑶ 전 항목이 구조적 DB 오류여도 500이 아닌 정상 2xx로 rejected 전량 보고."""
    client, _ = _auth_client()

    def always_boom(user_id, ev, now):
        raise IntegrityError("induced")

    monkeypatch.setattr(views_mod, "_record", always_boom)

    batch = [_imp("A:1"), _imp("B:2")]
    resp = client.post(URL, batch, format="json")
    assert resp.status_code == 200
    assert resp.data == {
        "received": 0,
        "rejected": 2,
        "rejected_reasons": {"db_error": 2},
    }
    assert ImpressionLog.objects.count() == 0


def test_empty_batch_is_2xx():
    """빈 배치도 500 아닌 2xx(전량 보고 0/0)."""
    client, _ = _auth_client()
    resp = client.post(URL, [], format="json")
    assert resp.status_code == 200
    assert resp.data == {"received": 0, "rejected": 0, "rejected_reasons": {}}
