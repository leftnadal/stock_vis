"""
Heat beat 오케스트레이션 테스트 (TH-5, 설계 §7 + 결정8).

커버:
- c2_supply_reaction: C2a+C2b 결합 / 하위 결측 재분배 / 둘 다 결측
- is_universe_stale 경계: 29일 → 마킹 없음 / 30 · 31일 → 마킹
- compute_theme_heat upsert 멱등: 2회 실행 → 행 수 불변, 값 갱신
- E2E: fixture 유니버스 → C8 None 재분배 포함 전 경로 → 저장 행 + universe_stale
- not_computed 섹터 미저장
- 섹터 실패 격리: build_components 예외 → 부분 저장 없이 스킵
- 등록 중복 가드: register_chainsight_beats 재실행 → no-op
"""

from datetime import date, timedelta

import pytest

from apps.chain_sight.models import HeatEntity, ThemeHeatScore
from apps.chain_sight.services import heat_beat as hb
from apps.chain_sight.services import heat_components as hc

AS_OF = date(2026, 7, 9)


# ────────────────────────────── C2 복합 슬롯 ──────────────────────────────
class TestC2SupplyReaction:
    def test_combines_both_subweights(self):
        c2a = hc.make_component(2.0, raw=0.9)   # 0.12
        c2b = hc.make_component(-1.0, raw=3)    # 0.06
        comp = hc.c2_supply_reaction(c2a, c2b)
        # (0.12*2 + 0.06*-1)/(0.18) = (0.24-0.06)/0.18 = 1.0
        assert comp["z"] == pytest.approx(1.0)
        assert comp["missing_reason"] is None
        assert comp["raw"]["c2a"] == c2a

    def test_sub_missing_redistributes(self):
        c2a = hc.make_component(1.5)
        c2b = hc.make_component(None, missing_reason="c2b_no_issuance")
        comp = hc.c2_supply_reaction(c2a, c2b)
        assert comp["z"] == pytest.approx(1.5)  # C2a 단독 = 그 z

    def test_both_missing(self):
        comp = hc.c2_supply_reaction(
            hc.make_component(None, missing_reason="x"),
            hc.make_component(None, missing_reason="y"),
        )
        assert comp["z"] is None and comp["missing_reason"] == "c2_no_supply"


# ────────────────────────────── universe_stale 경계 (결정8) ──────────────────────────────
class TestUniverseStale:
    def test_29_days_not_stale(self):
        assert hb.is_universe_stale(AS_OF - timedelta(days=29), AS_OF) is False

    def test_30_days_not_stale(self):
        assert hb.is_universe_stale(AS_OF - timedelta(days=30), AS_OF) is False  # >30 이 stale

    def test_31_days_stale(self):
        assert hb.is_universe_stale(AS_OF - timedelta(days=31), AS_OF) is True

    def test_none_is_stale(self):
        assert hb.is_universe_stale(None, AS_OF) is True

    def test_threshold_constant(self):
        assert hb.UNIVERSE_STALE_DAYS == 30


# ────────────────────────────── 오케스트레이션 ──────────────────────────────
def _full_components(c8=None):
    """C1~C7 present(z=0.5) + C8(주입). 결측 처리 테스트용."""
    comps = {k: {"z": 0.5, "s": None, "raw": None, "missing_reason": None}
             for k in ("C1", "C2", "C3", "C4", "C5", "C6", "C7")}
    comps["C8"] = c8 if c8 is not None else {
        "z": None, "s": None, "raw": None, "missing_reason": "c8_none", "z_mode": None}
    return comps


@pytest.mark.django_db
class TestOrchestration:
    def _mk_entity(self, ref_id="Technology"):
        # 마이그레이션 0016 이 11 섹터 + ThemeEtfMap 시드 → 결정론 위해 정리 후 1개만.
        from apps.chain_sight.models import ThemeEtfMap
        ThemeEtfMap.objects.all().delete()  # 섹터 FK(PROTECT) 선해제
        HeatEntity.objects.filter(kind="sector").delete()
        return HeatEntity.objects.create(kind="sector", ref_id=ref_id, constituent_policy="static")

    def test_e2e_stores_row_with_stale_and_c8_redistribution(self):
        """fixture 유니버스 → C8 None 재분배 → 저장 행 + universe_stale."""
        self._mk_entity()
        results = hb.compute_theme_heat(
            AS_OF, build_components=lambda e, s: _full_components(),  # C8 None
            universe_as_of=AS_OF - timedelta(days=69),  # stale
        )
        assert len(results) == 1 and results[0]["stored"] is True
        row = ThemeHeatScore.objects.get()
        assert row.date == AS_OF and row.score is not None
        assert row.components["universe_stale"] is True
        assert row.components["universe_as_of"] == (AS_OF - timedelta(days=69)).isoformat()
        assert row.components["C8"]["z"] is None  # 재분배(결측 1 < 3)

    def test_upsert_idempotent(self):
        """같은 테마×날짜 2회 → 행 수 불변, 값 갱신(created→updated)."""
        self._mk_entity()
        provider_hi = lambda e, s: _full_components(
            c8={"z": 3.0, "s": None, "raw": None, "missing_reason": None, "z_mode": "cross_sectional"})
        r1 = hb.compute_theme_heat(AS_OF, build_components=provider_hi)
        assert r1[0]["created"] is True
        score1 = ThemeHeatScore.objects.get().score

        provider_lo = lambda e, s: _full_components(
            c8={"z": -3.0, "s": None, "raw": None, "missing_reason": None, "z_mode": "cross_sectional"})
        r2 = hb.compute_theme_heat(AS_OF, build_components=provider_lo)
        assert r2[0]["created"] is False
        assert ThemeHeatScore.objects.count() == 1  # 중복 행 없음
        assert ThemeHeatScore.objects.get().score != score1  # 값 갱신

    def test_not_computed_not_stored(self):
        """결측 ≥3 → not_computed → 미저장."""
        self._mk_entity()
        few = lambda e, s: {  # C1·C2만 present, 6 결측
            "C1": {"z": 0.5, "raw": None, "missing_reason": None},
            "C2": {"z": 0.5, "raw": None, "missing_reason": None},
        }
        results = hb.compute_theme_heat(AS_OF, build_components=few)
        assert results[0]["status"] == "not_computed" and results[0]["stored"] is False
        assert ThemeHeatScore.objects.count() == 0

    def test_sector_failure_isolated_no_partial_save(self):
        """build_components 예외 → 부분 저장 없이 해당 섹터 스킵(격리)."""
        self._mk_entity()

        def boom(e, s):
            raise RuntimeError("build failed")

        results = hb.compute_theme_heat(AS_OF, build_components=boom)
        assert results[0]["status"] == "error" and results[0]["stored"] is False
        assert ThemeHeatScore.objects.count() == 0  # 부분 저장 없음


@pytest.mark.django_db
class TestBeatRegistrationGuard:
    def test_reregister_is_noop(self):
        """register_chainsight_beats 재실행 → 중복 생성 없음(update_or_create 멱등)."""
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        call_command("register_chainsight_beats")
        n1 = PeriodicTask.objects.filter(name="chainsight-theme-heat-daily").count()
        call_command("register_chainsight_beats")
        n2 = PeriodicTask.objects.filter(name="chainsight-theme-heat-daily").count()
        assert n1 == 1 and n2 == 1  # 재등록 no-op
