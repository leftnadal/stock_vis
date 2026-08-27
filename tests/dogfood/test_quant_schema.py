"""AGENT-S1 — 정량 리포트 JSON 스키마 + 판정 로직(네트워크 없이)."""
import json
from datetime import date

import pytest

from auto_agent_system.dogfood import check_quant as cq

REQUIRED_TOP = {
    "schema_version", "run_date", "generated_at", "session_date",
    "market", "auth_mode", "summary", "checks",
}
ITEM_KEYS = {"status", "value", "threshold", "note"}


@pytest.fixture
def offline(monkeypatch):
    """모든 HTTP를 연결 실패(0)로 — 네트워크 없이 스키마·집계를 검증한다."""
    monkeypatch.setattr(cq, "_fetch", lambda url, timeout=cq.ROUTE_TIMEOUT_S: (0, b"", 1.0))
    monkeypatch.setattr(cq, "_login_token", lambda: None)


def test_report_shape_and_summary_math(offline):
    report = cq.build_report(date(2026, 8, 27))

    assert REQUIRED_TOP <= set(report)
    assert report["schema_version"] == 1
    assert report["run_date"] == "2026-08-27"
    assert report["session_date"] == "2026-08-26"          # 직전 거래일
    assert report["auth_mode"] == "unauthenticated"

    checks = report["checks"]
    assert checks, "체크 항목이 하나도 없다"
    for key, item in checks.items():
        assert set(item) == ITEM_KEYS, f"{key}: 스키마 불일치 {set(item)}"
        assert item["status"] in {cq.OK, cq.WARN, cq.FAIL}
        assert item["note"], f"{key}: note 비어 있음"

    s = report["summary"]
    assert s["total"] == len(checks)
    assert s["passed"] + s["warn"] + s["failed"] == s["total"]


def test_checks_are_namespaced(offline):
    report = cq.build_report(date(2026, 8, 27))
    prefixes = {k.split(".", 1)[0] for k in report["checks"]}
    assert prefixes == {"route", "data", "api"}


def test_unreachable_service_fails_not_passes(offline):
    """서버가 죽었는데 통과로 집계되면 점검이 무의미하다."""
    report = cq.build_report(date(2026, 8, 27))
    assert report["summary"]["failed"] > 0
    assert report["checks"]["route.dashboard.main"]["status"] == cq.FAIL


def test_market_block_reports_holiday(offline):
    report = cq.build_report(date(2026, 12, 25))
    assert report["market"]["run_date_is_trading_day"] is False
    assert report["market"]["run_date_holiday"] == "Christmas Day"


def test_write_report_filename_and_roundtrip(tmp_path, offline):
    report = cq.build_report(date(2026, 8, 27))
    path = cq.write_report(report, tmp_path)
    assert path.name == "quant_20260827.json"
    assert json.loads(path.read_text(encoding="utf-8"))["run_date"] == "2026-08-27"


def test_visible_text_strips_scripts():
    """Next의 RSC 페이로드가 인라인 스크립트로 실려 마커를 오탐시키는 것을 막는다."""
    html = (
        "<body><p>정상 화면</p>"
        '<script>self.__next_f.push("This page could not be found")</script>'
        "<style>.a{content:'데이터를 불러오지 못했습니다'}</style></body>"
    )
    text = cq.visible_text(html)
    assert "정상 화면" in text
    assert "This page could not be found" not in text
    assert "데이터를 불러오지 못했습니다" not in text


@pytest.mark.parametrize(
    "body,expected",
    [
        (b"[]", True),
        (b"[1]", False),
        (b'{"results": []}', True),
        (b'{"results": [1]}', False),
        (b"{}", True),
        (b'{"a": 1}', False),
        (b"not json", False),
    ],
)
def test_looks_empty(body, expected):
    assert cq._looks_empty(body) is expected


def test_freshness_flags_stale_trading_date(monkeypatch):
    payload = json.dumps({
        "trading_date": "2026-08-20",
        "is_stale": False,
        "signal_cards": [{"id": "x"}],
        "recommendations": [],
    }).encode()
    monkeypatch.setattr(cq, "_fetch", lambda url, timeout=cq.ROUTE_TIMEOUT_S: (200, payload, 1.0))

    out = cq.check_freshness(date(2026, 8, 26))
    assert out["eod.trading_date"]["status"] == cq.FAIL   # 6일 지연
    assert out["eod.signal_cards"]["status"] == cq.OK
    assert out["eod.recommendations"]["status"] == cq.WARN  # 0건


def test_freshness_ok_when_dates_match(monkeypatch):
    payload = json.dumps({
        "trading_date": "2026-08-26",
        "is_stale": False,
        "signal_cards": [{"id": "x"}],
        "recommendations": [{"id": "y"}],
    }).encode()
    monkeypatch.setattr(cq, "_fetch", lambda url, timeout=cq.ROUTE_TIMEOUT_S: (200, payload, 1.0))

    out = cq.check_freshness(date(2026, 8, 26))
    assert all(v["status"] == cq.OK for v in out.values())


def test_freshness_empty_signal_cards_fails(monkeypatch):
    payload = json.dumps({"trading_date": "2026-08-26", "signal_cards": []}).encode()
    monkeypatch.setattr(cq, "_fetch", lambda url, timeout=cq.ROUTE_TIMEOUT_S: (200, payload, 1.0))
    out = cq.check_freshness(date(2026, 8, 26))
    assert out["eod.signal_cards"]["status"] == cq.FAIL


def test_api_401_is_ok_without_token_but_fail_with_token(monkeypatch):
    monkeypatch.setattr(cq, "_fetch", lambda url, timeout=cq.ROUTE_TIMEOUT_S: (401, b"", 1.0))
    without = cq.check_apis(None)
    assert without["monitor.monitors"]["status"] == cq.OK      # 인증 게이트 = 존재 확인
    assert without["health"]["status"] == cq.FAIL              # 무인증 엔드포인트가 401이면 이상

    with_token = cq.check_apis("dummy-token")
    assert with_token["monitor.monitors"]["status"] == cq.FAIL  # 토큰이 있는데 401 = 인증 실패
