"""P2-IMPRESSION-BUILD-S2: impression 수신 API 테스트 (apps/platform).

구획 준수: tests/ 밖 in-app 배치(DoD = apps/platform/** 만).
경계 #43: IssuanceLog 무접촉 — ImpressionLog(serve-time)만 검증.
"""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

import pytest

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
    assert resp.data == {"received": 1, "rejected": 0}
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
    assert resp.data == {"received": 2, "rejected": 3}
    assert ImpressionLog.objects.count() == 2
