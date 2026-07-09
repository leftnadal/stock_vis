"""
유니버스 갱신 + 감시 테스트 (TH-6, 결정9 + TH-UNIVERSE-REFRESH-ALERT).

커버:
- validate_universe 가드 경계: 479/480/520/521 · 필드 결손 · 심볼 중복 → DB 무접촉
- sync_constituents 멱등: 동일 응답 2회 → 행 수·상태 불변
- 편출입: 신규 추가 / 편출 → is_active 전환, 물리 삭제 0
- 가드 위반 → refresh task 알림 경로(mock)
- staleness 감시: 6/7/8일 경계
- E2E(결정8): 갱신 성공(fresh) → heat 실행 → universe_stale=False
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.chain_sight.models import HeatEntity, ThemeHeatScore
from apps.chain_sight.services import heat_beat as hb
from packages.shared.stocks.models import SP500Constituent
from packages.shared.stocks.services import sp500_service as svc


def _rows(symbols, sector="Information Technology"):
    return [{"symbol": s, "name": f"{s} Inc.", "sector": sector, "subSector": "",
             "headQuarter": "", "dateFirstAdded": "", "cik": "", "founded": ""}
            for s in symbols]


def _n_rows(n):
    return _rows([f"SYM{i:04d}" for i in range(n)])


class _FakeFMP:
    def __init__(self, rows):
        self._rows = rows

    def get_sp500_constituents(self):
        return self._rows


# ────────────────────────────── 가드 경계 ──────────────────────────────
class TestGuard:
    @pytest.mark.parametrize("n,ok", [(479, False), (480, True), (520, True), (521, False)])
    def test_count_boundary(self, n, ok):
        assert svc.validate_universe(_n_rows(n))["ok"] is ok

    def test_missing_field(self):
        rows = _n_rows(480)
        rows[0]["sector"] = ""  # 필수 필드 결손
        r = svc.validate_universe(rows)
        assert r["ok"] is False and r["reason"] == "missing_required_field"

    def test_duplicate_symbols(self):
        rows = _n_rows(480)
        rows[1]["symbol"] = rows[0]["symbol"]  # 중복
        r = svc.validate_universe(rows)
        assert r["ok"] is False and r["reason"] == "duplicate_symbols"


@pytest.mark.django_db
class TestSyncGuardNoDbTouch:
    def test_guard_violation_leaves_db_untouched(self):
        service = svc.SP500Service()
        service.fmp_client = _FakeFMP(_n_rows(479))  # 가드 위반
        result = service.sync_constituents()
        assert result["guard_violation"] == "count_out_of_range(479)"
        assert SP500Constituent.objects.count() == 0  # DB 무접촉


# ────────────────────────────── 멱등 + 편출입 ──────────────────────────────
@pytest.mark.django_db
class TestSyncBehavior:
    def test_idempotent(self):
        service = svc.SP500Service()
        service.fmp_client = _FakeFMP(_n_rows(480))
        r1 = service.sync_constituents()
        n1 = SP500Constituent.objects.count()
        r2 = service.sync_constituents()
        assert r1["created"] == 480 and r2["created"] == 0  # 2회차 신규 0
        assert SP500Constituent.objects.count() == n1  # 행 수 불변

    def test_add_and_deactivate_no_physical_delete(self):
        service = svc.SP500Service()
        base = [f"SYM{i:04d}" for i in range(480)]
        service.fmp_client = _FakeFMP(_rows(base))
        service.sync_constituents()

        # SYM0000 편출 + NEWSYM 편입
        nxt = base[1:] + ["NEWSYM"]
        service.fmp_client = _FakeFMP(_rows(nxt))
        r = service.sync_constituents()

        assert r["deactivated"] == 1 and r["created"] == 1
        assert SP500Constituent.objects.get(symbol="SYM0000").is_active is False  # 편출=비활성
        assert SP500Constituent.objects.get(symbol="NEWSYM").is_active is True
        assert SP500Constituent.objects.filter(symbol="SYM0000").exists()  # 물리 삭제 0


# ────────────────────────────── 알림 경로 ──────────────────────────────
@pytest.mark.django_db
class TestAlert:
    def test_guard_violation_triggers_alert(self):
        from apps.chain_sight.tasks import universe_tasks as ut

        with patch.object(ut.SP500Service if hasattr(ut, "SP500Service") else svc.SP500Service,
                          "sync_constituents",
                          return_value={"created": 0, "updated": 0, "deactivated": 0,
                                        "total": 479, "guard_violation": "count_out_of_range(479)"}):
            with patch.object(ut, "_alert") as m_alert:
                ut.refresh_sp500_universe_task.run()
        assert m_alert.called
        assert "가드 위반" in m_alert.call_args[0][0]


# ────────────────────────────── staleness 감시 ──────────────────────────────
@pytest.mark.django_db
class TestStaleness:
    def _seed_with_updated(self, days_ago):
        SP500Constituent.objects.create(symbol="AAA", company_name="A", sector="Tech")
        past = timezone.now() - timedelta(days=days_ago)
        SP500Constituent.objects.filter(symbol="AAA").update(updated_at=past)  # auto_now 우회

    @pytest.mark.parametrize("days,warn", [(6, False), (7, False), (8, True)])
    def test_warn_boundary(self, days, warn):
        from apps.chain_sight.services.universe_refresh import universe_staleness_status
        self._seed_with_updated(days)
        st = universe_staleness_status(timezone.now().date())
        assert st["warn"] is warn


# ────────────────────────────── E2E (결정8 연동) ──────────────────────────────
@pytest.mark.django_db
class TestDecision8Linkage:
    def test_fresh_universe_makes_heat_not_stale(self):
        """갱신 성공(fresh updated_at) → heat 실행 → universe_stale=False (결정8 자연 전환)."""
        # 갱신 성공: 480 종목 sync (updated_at=now, auto_now)
        service = svc.SP500Service()
        service.fmp_client = _FakeFMP(_n_rows(480))
        service.sync_constituents()

        # HeatEntity 1개 (시드 정리)
        from apps.chain_sight.models import ThemeEtfMap
        ThemeEtfMap.objects.all().delete()
        HeatEntity.objects.filter(kind="sector").delete()
        entity = HeatEntity.objects.create(kind="sector", ref_id="Technology", constituent_policy="static")

        computable = lambda e, s: {
            k: {"z": 0.5, "raw": None, "missing_reason": None}
            for k in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")
        }
        results = hb.compute_theme_heat(date.today(), build_components=computable)
        assert results[0]["stored"] is True
        row = ThemeHeatScore.objects.get()
        assert row.components["universe_stale"] is False  # 신선 → 자연 해제
