"""snapshot_series 검증 (MON-P2B T1) — 점수 정본 = MonitorSnapshot(동결 기록)."""
from datetime import date, timedelta

import pytest

from apps.monitor.models.monitoring import MonitorSnapshot
from apps.monitor.services.snapshot_series import snapshot_series


@pytest.mark.django_db
class TestSnapshotSeries:
    def _snap(self, monitor, d, score):
        return MonitorSnapshot.objects.create(
            monitor=monitor, asof_date=d, overall_score=score, state="active"
        )

    def test_empty(self, monitor):
        assert snapshot_series(monitor)["series"] == []

    def test_single_delta_none(self, monitor):
        self._snap(monitor, date(2026, 7, 28), 0.5)
        s = snapshot_series(monitor)["series"]
        assert len(s) == 1
        assert s[0]["delta"] is None and s[0]["score"] == 0.5

    def test_delta_prev_snapshot(self, monitor):
        self._snap(monitor, date(2026, 7, 28), 0.5)
        self._snap(monitor, date(2026, 7, 29), 0.7)
        s = snapshot_series(monitor)["series"]
        assert s[0]["delta"] is None
        assert s[1]["delta"] == pytest.approx(0.2)

    def test_zero_delta_kept(self, monitor):
        # Δ=0도 값(무표시 아님) — 반올림 0 은닉 제거.
        self._snap(monitor, date(2026, 7, 28), 0.3)
        self._snap(monitor, date(2026, 7, 29), 0.3)
        assert snapshot_series(monitor)["series"][1]["delta"] == 0.0

    def test_window_boundary_delta_uses_prior(self, monitor):
        # window 밖 직전 스냅샷 대비 delta를 window 첫 점이 보유.
        for i, sc in enumerate([0.1, 0.2, 0.4, 0.8]):
            self._snap(monitor, date(2026, 7, 28) + timedelta(days=i), sc)
        s = snapshot_series(monitor, window=2)["series"]
        assert len(s) == 2
        assert s[0]["delta"] == pytest.approx(0.2)  # 0.4 - 0.2(window 밖)
        assert s[1]["delta"] == pytest.approx(0.4)  # 0.8 - 0.4

    def test_ordering_ascending(self, monitor):
        self._snap(monitor, date(2026, 7, 29), 0.7)
        self._snap(monitor, date(2026, 7, 28), 0.5)
        s = snapshot_series(monitor)["series"]
        assert s[0]["asof"] == "2026-07-28"
        assert s[1]["asof"] == "2026-07-29"
