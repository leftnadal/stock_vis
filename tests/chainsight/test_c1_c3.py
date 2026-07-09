"""
C1 밸류에이션 + C3 내러티브 배선 테스트 (TH-10, 결정15·16) — 설계 앵커 §2 · §3 게이트.

커버:
- C1: 픽스처 수기 z 대조 / 분기<8 결측 / no_symbols / 분기 라벨 정합(revenue≤0 제외)
- C3: 매칭 정규화·완전 일치 / 집계 멱등 / 게이트 3분기 / beat 중복 가드
- 조립기: _NOT_WIRED 빈 튜플
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.chain_sight.models import HeatEntity, QuarterlyValuation, ThemeNewsVolume
from apps.chain_sight.services import heat_beat as hb
from apps.chain_sight.services.c1_valuation_service import c1_valuation_from_db
from apps.chain_sight.services.c3_narrative_service import (
    aggregate_theme_news_volume,
    c3_narrative_from_db,
)

AS_OF = date(2026, 7, 9)


# ────────────────────────────── C1 ──────────────────────────────
@pytest.mark.django_db
class TestC1Valuation:
    def test_no_symbols(self):
        assert c1_valuation_from_db([], AS_OF)["missing_reason"] == "c1_no_symbols"

    def test_insufficient_below_min(self):
        # 4분기만 → min_n(8) 미달 → 결측
        for i, q in enumerate([(2025, 3), (2025, 6), (2025, 9), (2025, 12)]):
            QuarterlyValuation.objects.create(
                symbol="AAA", fiscal_date=date(q[0], q[1], 28),
                enterprise_value=Decimal("100"), revenue=Decimal("10"),
            )
        c = c1_valuation_from_db(["AAA"], AS_OF)
        assert c["z"] is None and c["missing_reason"]

    def test_manual_z_fixture(self):
        # 9분기 EV/Sales = [10,11,12,13,14,15,16,17](history) + 20(current). revenue=1 → ev_sales=ev.
        vals = [10, 11, 12, 13, 14, 15, 16, 17, 20]
        base = [(2024, 3), (2024, 6), (2024, 9), (2024, 12),
                (2025, 3), (2025, 6), (2025, 9), (2025, 12), (2026, 3)]
        for (y, m), v in zip(base, vals):
            QuarterlyValuation.objects.create(
                symbol="AAA", fiscal_date=date(y, m, 28),
                enterprise_value=Decimal(str(v)), revenue=Decimal("1"),
            )
        c = c1_valuation_from_db(["AAA"], AS_OF, min_n=8)
        # 수기: history [10..17] mean=13.5 var=42/8=5.25 std=2.2913 → z=(20-13.5)/2.2913=2.837
        assert c["missing_reason"] is None
        assert c["z"] == pytest.approx(2.837, abs=0.01)
        assert c["raw"] == pytest.approx(20.0)

    def test_revenue_nonpositive_excluded(self):
        # revenue 0 분기는 ev_sales None → 유효 분기에서 제외 (라벨 정합)
        for (y, m) in [(2024, 3), (2024, 6), (2024, 9)]:
            QuarterlyValuation.objects.create(
                symbol="AAA", fiscal_date=date(y, m, 28),
                enterprise_value=Decimal("100"), revenue=Decimal("0"),
            )
        c = c1_valuation_from_db(["AAA"], AS_OF)
        assert c["missing_reason"] == "c1_no_valuation"


# ────────────────────────────── C3 집계·매칭 ──────────────────────────────
def _mk_news(d, term_lists):
    from services.news.models import DailyNewsKeyword

    keywords = [{"search_terms_en": terms} for terms in term_lists]
    DailyNewsKeyword.objects.create(date=d, keywords=keywords, total_news_count=1)


@pytest.mark.django_db
class TestC3Aggregation:
    def test_exact_match_normalized(self):
        # 'AI'·'cloud'(Technology) 완전 일치 2 / 'ai ruling'(부분) 매칭 안 됨
        _mk_news(date(2026, 6, 1), [["AI", "cloud", "ai ruling"]])
        aggregate_theme_news_volume()
        tech = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        tnv = ThemeNewsVolume.objects.get(theme=tech, date=date(2026, 6, 1))
        assert tnv.mention_count == 2  # ai + cloud (ai ruling 제외)

    def test_sector_name_mapping(self):
        # 'bank'(Financials) → HeatEntity 'Financial Services'
        _mk_news(date(2026, 6, 2), [["bank"]])
        aggregate_theme_news_volume()
        fin = HeatEntity.objects.get(kind="sector", ref_id="Financial Services")
        assert ThemeNewsVolume.objects.filter(theme=fin, date=date(2026, 6, 2)).exists()

    def test_idempotent(self):
        _mk_news(date(2026, 6, 3), [["ai"]])
        aggregate_theme_news_volume()
        aggregate_theme_news_volume()
        tech = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        assert ThemeNewsVolume.objects.filter(theme=tech, date=date(2026, 6, 3)).count() == 1


# ────────────────────────────── C3 게이트 ──────────────────────────────
def _mk_volume(entity, n, count_fn, start):
    ThemeNewsVolume.objects.bulk_create([
        ThemeNewsVolume(theme=entity, date=start + timedelta(days=i), mention_count=count_fn(i))
        for i in range(n)
    ])


@pytest.mark.django_db
class TestC3Gate:
    def _tech(self):
        return HeatEntity.objects.get(kind="sector", ref_id="Technology")

    def test_insufficient_below_26(self):
        _mk_volume(self._tech(), 10, lambda i: 5, date(2026, 1, 1))
        c = c3_narrative_from_db(self._tech(), date(2026, 1, 10))
        assert c["missing_reason"] == "c3_insufficient_history" and c["z_mode"] is None

    def test_expanding_26_to_60(self):
        _mk_volume(self._tech(), 40, lambda i: 5 + i % 3, date(2026, 1, 1))
        c = c3_narrative_from_db(self._tech(), date(2026, 1, 1) + timedelta(days=39))
        assert c["z_mode"] == "time_series_expanding" and c["z"] is not None

    def test_full_above_60(self):
        _mk_volume(self._tech(), 70, lambda i: 5 + i % 3, date(2026, 1, 1))
        c = c3_narrative_from_db(self._tech(), date(2026, 1, 1) + timedelta(days=69))
        assert c["z_mode"] == "time_series" and c["z"] is not None


# ────────────────────────────── beat + 조립기 ──────────────────────────────
@pytest.mark.django_db
class TestC3BeatAndAssembly:
    def test_aggregate_beat_reregister_noop(self):
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        call_command("register_chainsight_beats")
        n1 = PeriodicTask.objects.filter(name="chainsight-aggregate-theme-news").count()
        call_command("register_chainsight_beats")
        n2 = PeriodicTask.objects.filter(name="chainsight-aggregate-theme-news").count()
        assert n1 == 1 and n2 == 1

    def test_not_wired_empty(self):
        assert hb._NOT_WIRED == ()

    def test_c1_c3_in_components(self):
        e = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        comp = hb._real_sector_components(e, [], AS_OF, {})
        assert "C1" in comp and "C3" in comp
