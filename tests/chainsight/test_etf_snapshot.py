"""
C4 ETF 플로우 원료 스냅샷 테스트 (TH-7c, 결정11=A · 결정12a) — 설계 앵커 §2 · §6.4 · §7.

커버:
- SPDR 11종 원본 시드(migration 0018): active primary 11 / 순수 테마 ETF 7 active=False 불변
- XLE·XLV 원본 승격(active=True)
- 시드 멱등: update_or_create 재호출 → 무변화
- active_primary_etf_symbols: 11종 정렬 반환
- snapshot_etf_metrics: 정상 적립 / 멱등(2회 → 행 불변) / 가드(shares·nav 결측 → DB 무접촉)
- 태스크 알림: 대상 0건 · 전 심볼 skip → _alert 호출(mock)
- beat 중복 가드: chainsight-snapshot-etf-metrics 재등록 no-op
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.chain_sight.models import EtfSnapshot, HeatEntity, ThemeEtfMap
from apps.chain_sight.services import etf_snapshot_service as svc

AS_OF = date(2026, 7, 9)

SPDR_PRIMARY = {"XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"}
THEME_ETF_7 = {"SOXX", "SMH", "SOXL", "QQQ", "TQQQ", "ITA", "ERX"}


# ────────────────────────────── 시드 (migration 0018) ──────────────────────────────
@pytest.mark.django_db
class TestSpdrPrimarySeed:
    def test_active_primary_is_11_spdr(self):
        active = set(
            ThemeEtfMap.objects.filter(active=True, role="primary").values_list(
                "etf_symbol", flat=True
            )
        )
        assert active == SPDR_PRIMARY

    def test_theme_etf_7_active_false_unchanged(self):
        inactive = set(
            ThemeEtfMap.objects.filter(active=False).values_list("etf_symbol", flat=True)
        )
        assert inactive == THEME_ETF_7

    def test_xle_xlv_promoted_to_active_primary(self):
        # XLE(Energy)·XLV(Healthcare)는 0016 테마 시드에 active=False 로 있었으나 SPDR 원본으로 승격.
        for sym, ref in [("XLE", "Energy"), ("XLV", "Healthcare")]:
            row = ThemeEtfMap.objects.get(etf_symbol=sym, role="primary", theme__ref_id=ref)
            assert row.active is True

    def test_seed_idempotent(self):
        """SPDR 원본 시드 재호출(update_or_create) → 행수·active 불변."""
        before = ThemeEtfMap.objects.count()
        entity = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        ThemeEtfMap.objects.update_or_create(
            theme=entity, etf_symbol="XLK", role="primary",
            defaults={"leverage_factor": 1, "active": True},
        )
        assert ThemeEtfMap.objects.count() == before
        assert ThemeEtfMap.objects.get(etf_symbol="XLK", role="primary").active is True


# ────────────────────────────── 수집 대상 헬퍼 ──────────────────────────────
@pytest.mark.django_db
class TestActivePrimarySymbols:
    def test_returns_11_sorted(self):
        syms = svc.active_primary_etf_symbols()
        assert set(syms) == SPDR_PRIMARY
        assert syms == sorted(syms)


# ────────────────────────────── 수집 서비스 ──────────────────────────────
def _client(shares=1_000_000, nav=50.0, aum=5e10):
    c = MagicMock()
    c.get_etf_shares_float.return_value = {"outstandingShares": shares}
    c.get_etf_info.return_value = {"nav": nav, "assetsUnderManagement": aum}
    return c


@pytest.mark.django_db
class TestSnapshotEtfMetrics:
    def test_normal_store(self):
        r = svc.snapshot_etf_metrics(_client(), ["XLK", "XLF"], AS_OF)
        assert r["created"] == 2 and r["skipped"] == 0
        obj = EtfSnapshot.objects.get(symbol="XLK", snapshot_date=AS_OF)
        assert obj.shares_outstanding == Decimal("1000000")
        assert obj.nav == Decimal("50.000000")
        assert obj.aum == Decimal("50000000000")

    def test_idempotent(self):
        svc.snapshot_etf_metrics(_client(), ["XLK"], AS_OF)
        r2 = svc.snapshot_etf_metrics(_client(shares=1_234_567), ["XLK"], AS_OF)
        assert r2["created"] == 0 and r2["updated"] == 1
        assert EtfSnapshot.objects.filter(symbol="XLK").count() == 1  # 행 불변
        # 값은 최신으로 갱신(멱등 upsert)
        assert EtfSnapshot.objects.get(symbol="XLK").shares_outstanding == Decimal("1234567")

    def test_guard_missing_shares_skips_no_db(self):
        r = svc.snapshot_etf_metrics(_client(shares=None), ["XLK"], AS_OF)
        assert r["skipped"] == 1 and r["created"] == 0
        assert EtfSnapshot.objects.count() == 0  # DB 무접촉

    def test_guard_nonpositive_nav_skips(self):
        r = svc.snapshot_etf_metrics(_client(nav=0), ["XLK"], AS_OF)
        assert r["skipped"] == 1
        assert EtfSnapshot.objects.count() == 0

    def test_aum_optional(self):
        c = _client()
        c.get_etf_info.return_value = {"nav": 50.0}  # aum 없음
        r = svc.snapshot_etf_metrics(c, ["XLK"], AS_OF)
        assert r["created"] == 1
        assert EtfSnapshot.objects.get(symbol="XLK").aum is None


# ────────────────────────────── 태스크 알림 경로 ──────────────────────────────
@pytest.mark.django_db
class TestSnapshotTaskAlerts:
    def test_all_skip_triggers_alert(self):
        from apps.chain_sight.tasks import etf_snapshot_tasks as t

        alerts = []
        with patch("django.db.connections.close_all"), \
             patch("apps.chain_sight.tasks.universe_tasks._alert",
                   side_effect=lambda s, b: alerts.append(s)), \
             patch("packages.shared.api_request.providers.fmp.client.FMPClient",
                   return_value=_client(shares=None)):
            t.snapshot_etf_metrics_task.run()
        assert any("저장 0건" in s for s in alerts)


# ────────────────────────────── beat 등록 가드 ──────────────────────────────
@pytest.mark.django_db
class TestBeatRegistrationGuard:
    def test_snapshot_beat_reregister_noop(self):
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        call_command("register_chainsight_beats")
        n1 = PeriodicTask.objects.filter(name="chainsight-snapshot-etf-metrics").count()
        call_command("register_chainsight_beats")
        n2 = PeriodicTask.objects.filter(name="chainsight-snapshot-etf-metrics").count()
        assert n1 == 1 and n2 == 1
