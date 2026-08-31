"""DSS-BEAT-1 §A — load_dss_weekly 태스크 + load_dss_week command 테스트.

케이스: 가드 skip / 멱등 재실행 무해 / 정상 경로 서비스 위임 / command smoke.
서비스(store_for_anchor)는 mock — 래핑 로직(가드·위임·요약)만 검증(store 자체는 DSS-W8 계열이 검증).
"""
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from apps.chain_sight.models import EstimateSnapshot
from apps.chain_sight.tasks.dss_tasks import load_dss_weekly

UTC = ZoneInfo("UTC")

# ET 19:00(=UTC 23:00 겨울/UTC 00:00 여름 근사) — date만 쓰므로 ET 당일로 떨어지게 UTC 12:00 사용
FIXED_NOW = datetime(2099, 1, 2, 12, 0, tzinfo=UTC)  # → ET 2099-01-02


def _snapshot(d):
    return EstimateSnapshot.objects.create(
        symbol="AAA", snapshot_date=d, fiscal_year=2100, eps_avg=1.0, num_analysts_eps=5
    )


SUMMARY = {
    "n_signals": 10, "up": 5, "down": 3, "flat": 2, "excluded": 0,
    "written_signals": 10, "written_scores": 11, "skipped_existing": False,
}


@pytest.mark.django_db
@patch("apps.chain_sight.tasks.dss_tasks.timezone")
@patch("apps.chain_sight.services.demand_signal.store_for_anchor")
@patch("django.db.connections.close_all")  # #25 fork-safety no-op (테스트=단일 프로세스)
def test_guard_skip_when_snapshot_not_today(mock_close, mock_store, mock_tz):
    """최신 스냅샷 date ≠ 실행일(ET) → skip, store 미호출."""
    mock_tz.now.return_value = FIXED_NOW  # ET 2099-01-02
    _snapshot(date(2099, 1, 1))  # 최신 = 전날
    r = load_dss_weekly.apply().get()
    assert r["skipped"] is True
    assert r["et_today"] == "2099-01-02"
    mock_store.assert_not_called()


@pytest.mark.django_db
@patch("apps.chain_sight.tasks.dss_tasks.timezone")
@patch("apps.chain_sight.services.demand_signal.store_for_anchor")
@patch("django.db.connections.close_all")  # #25 fork-safety no-op (테스트=단일 프로세스)
def test_normal_delegates_to_store(mock_close, mock_store, mock_tz):
    """최신 스냅샷 date == 실행일 → store_for_anchor(et_today) 위임."""
    mock_tz.now.return_value = FIXED_NOW
    mock_store.return_value = dict(SUMMARY)
    _snapshot(date(2099, 1, 2))  # 최신 = 당일
    r = load_dss_weekly.apply().get()
    mock_store.assert_called_once_with(date(2099, 1, 2), dry_run=False)
    assert r["anchor"] == "2099-01-02"
    assert r["written_signals"] == 10 and r["written_scores"] == 11
    assert r["flat_ratio"] == pytest.approx(2 / 10)


@pytest.mark.django_db
@patch("apps.chain_sight.tasks.dss_tasks.timezone")
@patch("apps.chain_sight.services.demand_signal.store_for_anchor")
@patch("django.db.connections.close_all")  # #25 fork-safety no-op (테스트=단일 프로세스)
def test_idempotent_rerun_harmless(mock_close, mock_store, mock_tz):
    """기존재 anchor 재실행 → store가 skipped_existing=True 반환, 태스크 무해 통과."""
    mock_tz.now.return_value = FIXED_NOW
    s = dict(SUMMARY)
    s.update(written_signals=0, written_scores=0, skipped_existing=True)
    mock_store.return_value = s
    _snapshot(date(2099, 1, 2))
    r = load_dss_weekly.apply().get()
    assert r["skipped_existing"] is True
    assert r["written_signals"] == 0


@pytest.mark.django_db
@patch("apps.chain_sight.management.commands.load_dss_week.build_quadrant")
@patch("apps.chain_sight.management.commands.load_dss_week.store_for_anchor")
def test_command_smoke(mock_store, mock_quad, capsys):
    """command --anchor 실행 → 서비스 위임 + 판정 출력(빈 데이터 graceful)."""
    mock_store.return_value = dict(SUMMARY)
    mock_quad.return_value = {
        "arrow_suppressed": False, "flat_ratio_curr": 0.52, "flat_ratio_prev": 0.07,
    }
    call_command("load_dss_week", "--anchor", "2099-01-02")
    out = capsys.readouterr().out
    assert "anchor=2099-01-02" in out
    assert "arrow_suppressed=False" in out
    mock_store.assert_called_once_with(date(2099, 1, 2), dry_run=False)
