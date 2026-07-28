"""P2-IMPRESSION-BUILD-S2: impression 수신 API 테스트 (apps/platform).

구획 준수: tests/ 밖 in-app 배치(DoD = apps/platform/** 만).
경계 #43: IssuanceLog 무접촉 — ImpressionLog(serve-time)만 검증.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

import apps.platform.api.views as views_mod
from packages.shared.stocks.models import ImpressionLog, IssuanceLog, Stock

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

URL = "/api/v1/telemetry/impressions"
COVERAGE_URL = "/api/v1/telemetry/coverage"
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


# ─────────────────────────────────────────────────────────────────────────────
# P2-COVERAGE-C1-API: GET /api/v1/telemetry/coverage
# 경계 #43: IssuanceLog·ImpressionLog **읽기만**(스키마 무변경, 신규 모델/필드/인덱스 0).
# ─────────────────────────────────────────────────────────────────────────────


def _issue(stock, signal_date, signal_tag="P5"):
    """발급 로그 1건(user-agnostic). IssuanceLog 읽기 조인 대상 픽스처."""
    return IssuanceLog.objects.create(
        stock=stock,
        signal_date=signal_date,
        signal_tag=signal_tag,
        confidence="high",
        rank=1,
        published_at=timezone.now(),
    )


def _impress(user_id, object_ref, surface=ImpressionLog.SURFACE_DASHBOARD_EOD):
    """impression 행 직접 생성(수신 API 우회 — 커버리지 조회 픽스처)."""
    return ImpressionLog.objects.create(
        user_id=user_id,
        surface=surface,
        object_ref=object_ref,
        event_type=ImpressionLog.EVENT_IMPRESSION,
        first_seen_at=timezone.now(),
        seen_count=1,
        session_id="s",
    )


def _ref(symbol, d, tag="P5"):
    return f"{symbol}:{d.isoformat()}:{tag}"


def test_coverage_normal_aggregation():
    """정상 집계 — issued/exposed/unexposed/rate + 미노출 리스트."""
    client, user = _auth_client()
    today = timezone.localdate()
    s1, s2, s3 = Stock.objects.create(symbol="AAA"), Stock.objects.create(
        symbol="BBB"
    ), Stock.objects.create(symbol="CCC")
    _issue(s1, today, "P5")  # 노출됨
    _issue(s2, today, "P1")  # 미노출
    _issue(s3, today, "S1")  # 미노출
    _impress(user.id, _ref("AAA", today, "P5"))

    resp = client.get(COVERAGE_URL)
    assert resp.status_code == 200
    d = resp.data
    assert d["summary"]["issued"] == 3
    assert d["summary"]["exposed"] == 1
    assert d["summary"]["unexposed_count"] == 2
    assert d["summary"]["exposure_rate"] == round(1 / 3, 4)
    assert {u["object_ref"] for u in d["unexposed"]} == {
        _ref("BBB", today, "P1"),
        _ref("CCC", today, "S1"),
    }
    # 미노출 항목 필드 계약
    item = d["unexposed"][0]
    assert set(item) == {
        "object_ref",
        "ticker",
        "signal_date",
        "signal_tag",
        "days_since_issue",
    }
    assert item["days_since_issue"] == 0
    assert d["meta"]["surfaces_included"] == ["dashboard_eod"]
    assert d["meta"]["join_misses"] == 0


def test_coverage_window_boundary():
    """window 경계 — 창밖 발급 제외, window_days 확장 시 포함."""
    client, _ = _auth_client()
    today = timezone.localdate()
    s_in, s_out = Stock.objects.create(symbol="INW"), Stock.objects.create(
        symbol="OUT"
    )
    _issue(s_in, today, "P5")
    _issue(s_out, today - timedelta(days=40), "P5")  # 40일 전 = 기본창(7) 밖

    resp = client.get(COVERAGE_URL)  # 기본 window_days=7
    assert resp.data["summary"]["issued"] == 1
    assert resp.data["window"]["days"] == 7

    resp2 = client.get(COVERAGE_URL, {"window_days": 90})
    assert resp2.data["summary"]["issued"] == 2
    assert resp2.data["window"]["days"] == 90


def test_coverage_window_days_capped_and_validated():
    """window_days 상한 90 clamp + 부적합 입력 400."""
    client, _ = _auth_client()
    assert client.get(COVERAGE_URL, {"window_days": 999}).data["window"]["days"] == 90
    assert client.get(COVERAGE_URL, {"window_days": "abc"}).status_code == 400
    assert client.get(COVERAGE_URL, {"window_days": 0}).status_code == 400


def test_coverage_detail_surface_excluded():
    """coverage_detail 표면 노출은 유기 exposed 에서 제외(D-P2-COVERAGE-SURFACE)."""
    client, user = _auth_client()
    today = timezone.localdate()
    s = Stock.objects.create(symbol="DET")
    _issue(s, today, "P5")
    # 사용자가 상세페이지(coverage_detail)서만 봄 → 유기 노출 아님 → exposed 0
    _impress(user.id, _ref("DET", today, "P5"), surface="coverage_detail")

    d = client.get(COVERAGE_URL).data
    assert d["summary"]["exposed"] == 0
    assert d["summary"]["unexposed_count"] == 1


def test_coverage_unauthenticated_rejected():
    """비로그인 401/403."""
    resp = APIClient().get(COVERAGE_URL)
    assert resp.status_code in (401, 403)


def test_coverage_scoped_to_requesting_user():
    """타 사용자 impression 은 요청자 커버리지에 미포함."""
    client, user = _auth_client()
    other = User.objects.create_user(
        username="other_u", email="o@example.com", password="pw12345!"
    )
    today = timezone.localdate()
    s = Stock.objects.create(symbol="SCP")
    _issue(s, today, "P5")
    _impress(other.id, _ref("SCP", today, "P5"))  # 타 사용자가 봄

    d = client.get(COVERAGE_URL).data
    assert d["summary"]["exposed"] == 0  # 요청자는 안 봄
    assert d["summary"]["unexposed_count"] == 1


def test_coverage_join_misses_counted():
    """in-window 발급에 귀속 안 되는 노출 = meta.join_misses(침묵 유실 금지)."""
    client, user = _auth_client()
    today = timezone.localdate()
    s = Stock.objects.create(symbol="JMS")
    _issue(s, today, "P5")
    _impress(user.id, _ref("JMS", today, "P5"))  # exposed
    _impress(user.id, "GHOST:2020-01-01:P5")  # 창밖 grain → 귀속 실패

    d = client.get(COVERAGE_URL).data
    assert d["summary"]["exposed"] == 1
    assert d["meta"]["join_misses"] == 1


def test_coverage_no_issuance_zero_rate():
    """발급 0 → ZeroDivision 없이 rate 0.0, 빈 리스트."""
    client, _ = _auth_client()
    d = client.get(COVERAGE_URL).data
    assert d["summary"]["issued"] == 0
    assert d["summary"]["exposure_rate"] == 0.0
    assert d["unexposed"] == []
