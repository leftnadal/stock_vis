"""
Theme Heat 데이터 모델 테스트 (TH-1, 설계서 §6.0~§6.6).

검증:
- 마이그레이션 시드: HeatEntity kind=sector 11행 / kind=theme 0행 (잠금장치 2)
- ThemeEtfMap §6.4 초기 시드 존재 (검수 미완)
- HeatEntity 3필드 잠금장치 (잠금장치 1 — 도메인 필드 초과 금지)
- 7모델 각 생성·조회 (최소 1건)
- unique 제약: dedup_key / unique_together
- EstimateSnapshot unique_together = (symbol, snapshot_date, fiscal_year) 정합
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.chain_sight.models import (
    EstimateSnapshot,
    HeatEntity,
    InsiderTransactionRecord,
    ThemeDemandScore,
    ThemeEtfMap,
    ThemeFilingCount,
    ThemeHeatScore,
)

GICS_SECTORS = {
    "Technology",
    "Healthcare",
    "Financial Services",
    "Consumer Cyclical",
    "Industrials",
    "Energy",
    "Communication Services",
    "Real Estate",
    "Utilities",
    "Basic Materials",
    "Consumer Defensive",
}


# ─────────────────────────── 마이그레이션 시드 ───────────────────────────
@pytest.mark.django_db
class TestHeatEntitySeed:
    def test_sector_11_theme_0(self):
        """잠금장치 2: kind=sector 11행만, kind=theme 행 없음."""
        assert HeatEntity.objects.filter(kind="sector").count() == 11
        assert HeatEntity.objects.filter(kind="theme").count() == 0

    def test_sector_ref_ids_are_gics(self):
        refs = set(
            HeatEntity.objects.filter(kind="sector").values_list("ref_id", flat=True)
        )
        assert refs == GICS_SECTORS

    def test_sector_policy_static(self):
        assert (
            HeatEntity.objects.filter(kind="sector")
            .exclude(constituent_policy="static")
            .count()
            == 0
        )

    def test_etf_map_seed_present(self):
        """§6.4 초기 시드 (검수 미완). Technology 에 primary/leveraged 존재."""
        assert ThemeEtfMap.objects.count() == 9
        tech = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        assert tech.etf_maps.filter(role="primary").exists()
        assert tech.etf_maps.filter(role="leveraged", leverage_factor=3).exists()

    def test_etf_map_seed_inactive(self):
        """§6.4 v1.2.1: 테마 ETF 9행은 active=False (레인 개방 대기)."""
        assert ThemeEtfMap.objects.filter(active=True).count() == 0
        assert ThemeEtfMap.objects.filter(active=False).count() == 9


# ─────────────────────────── 잠금장치 1 (3필드) ───────────────────────────
@pytest.mark.django_db
class TestHeatEntityLock:
    def test_exactly_three_domain_fields(self):
        """잠금장치 1: 도메인 필드는 kind/ref_id/constituent_policy 3개 초과 금지."""
        local = {f.name for f in HeatEntity._meta.local_fields}
        assert local == {"id", "kind", "ref_id", "constituent_policy"}

    def test_kind_ref_unique(self):
        HeatEntity.objects.create(
            kind="sector", ref_id="XTEST", constituent_policy="static"
        )
        with pytest.raises(IntegrityError):
            HeatEntity.objects.create(
                kind="sector", ref_id="XTEST", constituent_policy="static"
            )


# ─────────────────────────── 7모델 생성·조회 ───────────────────────────
@pytest.mark.django_db
class TestModelsCreateRead:
    def _sector(self):
        return HeatEntity.objects.get(kind="sector", ref_id="Technology")

    def test_heat_entity(self):
        assert self._sector().pk is not None

    def test_theme_heat_score(self):
        s = ThemeHeatScore.objects.create(
            theme=self._sector(),
            date=date(2026, 7, 6),
            score=72,
            status=ThemeHeatScore.STATUS_OVERHEATED,
            components={"C1": {"z": 1.2, "s": 0.77, "raw": 30.0, "missing_reason": None}},
            evidence={"top": ["C2a", "C1"]},
        )
        got = ThemeHeatScore.objects.get(pk=s.pk)
        assert got.score == 72 and got.status == "overheated"
        assert got.components["C1"]["z"] == 1.2

    def test_theme_demand_score_not_computed(self):
        d = ThemeDemandScore.objects.create(
            theme=self._sector(),
            date=date(2026, 7, 3),
            score=None,
            status=ThemeDemandScore.STATUS_NOT_COMPUTED,
        )
        assert ThemeDemandScore.objects.get(pk=d.pk).score is None

    def test_insider_record(self):
        r = InsiderTransactionRecord.objects.create(
            symbol="NVDA",
            reporting_cik="0001199039",
            company_cik="0001045810",
            filing_date=date(2026, 6, 29),
            transaction_date=date(2026, 6, 25),
            transaction_type="S-Sale",
            securities_transacted=Decimal("1211"),
            price=Decimal("308.6300"),
            type_of_owner="director",
            direct_or_indirect="D",
            acq_or_disp="D",
            sec_url="https://www.sec.gov/Archives/edgar/data/1045810/x-index.htm",
            raw={"symbol": "NVDA"},
            dedup_key="nvda-1",
        )
        assert InsiderTransactionRecord.objects.get(dedup_key="nvda-1").symbol == "NVDA"

    def test_insider_blank_transaction_type_preserved(self):
        """전건 보존: transaction_type 공란도 적재 가능 (필터는 집계 계층, §5.1)."""
        r = InsiderTransactionRecord.objects.create(
            symbol="AAPL",
            filing_date=date(2026, 6, 17),
            transaction_date=date(2026, 6, 15),
            transaction_type="",
            dedup_key="aapl-blank",
        )
        assert r.transaction_type == ""

    def test_theme_etf_map(self):
        m = ThemeEtfMap.objects.create(
            theme=HeatEntity.objects.get(kind="sector", ref_id="Utilities"),
            etf_symbol="XLU",
            role=ThemeEtfMap.ROLE_PRIMARY,
        )
        assert m.leverage_factor == 1 and m.active is True

    def test_theme_filing_count(self):
        f = ThemeFilingCount.objects.create(
            symbol="ENTA",
            filing_date=date(2026, 7, 2),
            form_type="424B5",
            dedup_key="enta-424b5-1",
        )
        assert ThemeFilingCount.objects.get(dedup_key="enta-424b5-1").source == "fmp"

    def test_estimate_snapshot(self):
        e = EstimateSnapshot.objects.create(
            symbol="AAPL",
            snapshot_date=date(2026, 7, 3),
            fiscal_year=2026,
            eps_avg=Decimal("8.7550"),
            num_analysts_eps=31,
            revenue_avg=Decimal("420000000000.00"),
        )
        assert EstimateSnapshot.objects.get(pk=e.pk).num_analysts_eps == 31


# ─────────────────────────── unique 제약 ───────────────────────────
@pytest.mark.django_db
class TestUniqueConstraints:
    def test_insider_dedup_key_unique(self):
        InsiderTransactionRecord.objects.create(
            symbol="X", filing_date=date(2026, 1, 1), transaction_date=date(2026, 1, 1),
            dedup_key="dup",
        )
        with pytest.raises(IntegrityError):
            InsiderTransactionRecord.objects.create(
                symbol="Y", filing_date=date(2026, 1, 2), transaction_date=date(2026, 1, 2),
                dedup_key="dup",
            )

    def test_filing_dedup_key_unique(self):
        ThemeFilingCount.objects.create(
            filing_date=date(2026, 1, 1), form_type="424B5", dedup_key="fdup"
        )
        with pytest.raises(IntegrityError):
            ThemeFilingCount.objects.create(
                filing_date=date(2026, 1, 2), form_type="424B5", dedup_key="fdup"
            )

    def test_heat_score_unique_together(self):
        theme = HeatEntity.objects.get(kind="sector", ref_id="Energy")
        ThemeHeatScore.objects.create(
            theme=theme, date=date(2026, 7, 6), score=50, status="warning"
        )
        with pytest.raises(IntegrityError):
            ThemeHeatScore.objects.create(
                theme=theme, date=date(2026, 7, 6), score=60, status="warning"
            )

    def test_estimate_snapshot_fiscal_year_distinguishes(self):
        """정합: (symbol, snapshot_date) 동일 + fiscal_year 상이 = 허용 (당기·차기)."""
        EstimateSnapshot.objects.create(
            symbol="MSFT", snapshot_date=date(2026, 7, 3), fiscal_year=2026
        )
        # 차기연도 = OK
        EstimateSnapshot.objects.create(
            symbol="MSFT", snapshot_date=date(2026, 7, 3), fiscal_year=2027
        )
        assert EstimateSnapshot.objects.filter(symbol="MSFT").count() == 2
        # 동일 triple = 충돌
        with pytest.raises(IntegrityError):
            EstimateSnapshot.objects.create(
                symbol="MSFT", snapshot_date=date(2026, 7, 3), fiscal_year=2027
            )
