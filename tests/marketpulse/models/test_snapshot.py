"""PR-A3 재해석 — 카드 스냅샷 3개 모델 제약·validator·통합 검증.

원본 PR-A3 지시서 §5.1(T1~T11), §5.3(T18~T19) 적용 + ConcentrationSnapshot
clean() validator 검증 추가.

§5.2(T12~T17) 마이그레이션 단계별 테스트는 적용 불가 — PR-A3 모델 3개가
marketpulse 0001_initial에 통합되어 있어 0002/0003/0004 분리 마이그레이션이
존재하지 않음. forward/reverse 멱등성은 PR-A2 검증에서 통과 확인.
"""
from __future__ import annotations

from datetime import date as dt_date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import models as dj_models
from django.db.models import ProtectedError
from django.utils import timezone


@pytest.fixture
def tech_index(db):
    """단일 GICS TECH 그룹 MarketIndex."""
    from macro.models.indicators import MarketIndex
    return MarketIndex.objects.create(
        symbol='XLK_A3T',
        name='Tech SPDR (test)',
        sector_group=MarketIndex.SectorGroup.TECH,
    )


@pytest.mark.django_db
class TestBreadthSnapshot:
    """§5.1 T1~T3 — BreadthSnapshot 제약."""

    def _make(self, **overrides):
        from marketpulse.models.snapshot import BreadthSnapshot
        defaults = {
            'date': dt_date(2026, 5, 11),
            'snapshot_time': timezone.now(),
        }
        defaults.update(overrides)
        return BreadthSnapshot.objects.create(**defaults)

    def test_universe_choices_t1(self):
        """T1: universe SPY/QQQ/DIA 3개 + default=SPY."""
        from marketpulse.models.snapshot import BreadthSnapshot
        choices = dict(BreadthSnapshot.Universe.choices)
        assert set(choices.keys()) == {'SPY', 'QQQ', 'DIA'}
        field = BreadthSnapshot._meta.get_field('universe')
        assert field.default == BreadthSnapshot.Universe.SPY

    def test_unique_date_universe_t2(self):
        """T2: (date, universe) unique."""
        self._make(universe='SPY')
        with pytest.raises(IntegrityError):
            self._make(universe='SPY')

    def test_different_universe_same_date_ok(self):
        """같은 date, 다른 universe는 unique 제약 통과."""
        self._make(universe='SPY')
        self._make(universe='QQQ')

    def test_is_finalized_default_t3(self):
        """T3: is_finalized=False, finalized_at=None."""
        b = self._make()
        assert b.is_finalized is False
        assert b.finalized_at is None


@pytest.mark.django_db
class TestSectorFlowSnapshot:
    """§5.1 T4~T6 — SectorFlowSnapshot 제약."""

    def _make(self, market_index, **overrides):
        from marketpulse.models.snapshot import SectorFlowSnapshot
        defaults = {
            'date': dt_date(2026, 5, 11),
            'snapshot_time': timezone.now(),
            'market_index': market_index,
        }
        defaults.update(overrides)
        return SectorFlowSnapshot.objects.create(**defaults)

    def test_unique_date_market_index_t4(self, tech_index):
        """T4: (date, market_index) unique."""
        self._make(tech_index)
        with pytest.raises(IntegrityError):
            self._make(tech_index)

    def test_fk_protect_t5(self, tech_index):
        """T5 (D8): MarketIndex 삭제 시 ProtectedError."""
        self._make(tech_index)
        with pytest.raises(ProtectedError):
            tech_index.delete()

    def test_long_format_11_etfs_t6(self, db):
        """T6: 11 GICS 섹터 ETF 같은 date에 11 row INSERT (long-format)."""
        from macro.models.indicators import MarketIndex
        from marketpulse.models.snapshot import SectorFlowSnapshot
        sectors = [
            ('XLF_A3T', MarketIndex.SectorGroup.FINANCIALS),
            ('XLK_A3T2', MarketIndex.SectorGroup.TECH),
            ('XLV_A3T', MarketIndex.SectorGroup.HEALTHCARE),
            ('XLY_A3T', MarketIndex.SectorGroup.CONSUMER_DISC),
            ('XLP_A3T', MarketIndex.SectorGroup.CONSUMER_STAPLES),
            ('XLE_A3T', MarketIndex.SectorGroup.ENERGY),
            ('XLI_A3T', MarketIndex.SectorGroup.INDUSTRIALS),
            ('XLB_A3T', MarketIndex.SectorGroup.MATERIALS),
            ('XLU_A3T', MarketIndex.SectorGroup.UTILITIES),
            ('XLRE_A3T', MarketIndex.SectorGroup.REAL_ESTATE),
            ('XLC_A3T', MarketIndex.SectorGroup.COMMUNICATION),
        ]
        d = dt_date(2026, 5, 11)
        now = timezone.now()
        for rank, (sym, grp) in enumerate(sectors, start=1):
            mi = MarketIndex.objects.create(symbol=sym, name=sym, sector_group=grp)
            SectorFlowSnapshot.objects.create(
                date=d, snapshot_time=now, market_index=mi, rank_in_universe=rank,
            )
        assert SectorFlowSnapshot.objects.filter(date=d).count() == 11


@pytest.mark.django_db
class TestConcentrationSnapshot:
    """§5.1 T7~T8 + clean() validator."""

    def _make(self, **overrides):
        from marketpulse.models.snapshot import ConcentrationSnapshot
        defaults = {
            'date': dt_date(2026, 5, 11),
            'snapshot_time': timezone.now(),
            'universe': 'SPY',
        }
        defaults.update(overrides)
        return ConcentrationSnapshot.objects.create(**defaults)

    def test_unique_date_universe_t7(self):
        """T7: (date, universe) unique."""
        self._make(universe='SPY')
        with pytest.raises(IntegrityError):
            self._make(universe='SPY')

    def test_top_holdings_json_t8(self):
        """T8: top_holdings list[dict] 저장·조회 (지시서 top_contributors → 구현 top_holdings)."""
        holdings = [
            {'symbol': 'AAPL', 'weight': 0.07},
            {'symbol': 'MSFT', 'weight': 0.065},
        ]
        c = self._make(top_holdings=holdings)
        c.refresh_from_db()
        assert c.top_holdings[0]['symbol'] == 'AAPL'
        assert c.top_holdings[1]['weight'] == 0.065

    def test_top_holdings_default_empty_list(self):
        c = self._make()
        assert c.top_holdings == []

    def test_clean_top5_le_top10(self):
        """clean(): top5_weight > top10_weight ValidationError."""
        from marketpulse.models.snapshot import ConcentrationSnapshot
        c = ConcentrationSnapshot(
            date=dt_date(2026, 5, 11), snapshot_time=timezone.now(),
            top5_weight=Decimal('0.5'), top10_weight=Decimal('0.3'),
        )
        with pytest.raises(ValidationError) as exc:
            c.clean()
        assert 'top5_weight' in exc.value.message_dict

    def test_clean_top10_le_one(self):
        """clean(): top10_weight > 1.0 ValidationError."""
        from marketpulse.models.snapshot import ConcentrationSnapshot
        c = ConcentrationSnapshot(
            date=dt_date(2026, 5, 11), snapshot_time=timezone.now(),
            top5_weight=Decimal('0.5'), top10_weight=Decimal('1.5'),
        )
        with pytest.raises(ValidationError) as exc:
            c.clean()
        assert 'top10_weight' in exc.value.message_dict

    def test_clean_hhi_in_unit_range(self):
        """clean(): hhi ∉ [0, 1.0] ValidationError."""
        from marketpulse.models.snapshot import ConcentrationSnapshot
        c = ConcentrationSnapshot(
            date=dt_date(2026, 5, 11), snapshot_time=timezone.now(),
            top5_weight=Decimal('0.3'), top10_weight=Decimal('0.5'),
            hhi=Decimal('1.5'),
        )
        with pytest.raises(ValidationError) as exc:
            c.clean()
        assert 'hhi' in exc.value.message_dict

    def test_clean_valid_passes(self):
        """clean(): 정상 값은 통과."""
        from marketpulse.models.snapshot import ConcentrationSnapshot
        c = ConcentrationSnapshot(
            date=dt_date(2026, 5, 11), snapshot_time=timezone.now(),
            top5_weight=Decimal('0.2'), top10_weight=Decimal('0.35'),
            hhi=Decimal('0.018'),
        )
        c.clean()  # raises = fail


@pytest.mark.django_db
class TestSnapshotConsistency:
    """§5.1 T9~T11 — 3개 모델 공통 일관성."""

    def _models(self):
        from marketpulse.models.snapshot import (
            BreadthSnapshot,
            ConcentrationSnapshot,
            SectorFlowSnapshot,
        )
        return [BreadthSnapshot, SectorFlowSnapshot, ConcentrationSnapshot]

    def test_is_finalized_consistency_t9(self):
        """T9: 3개 모두 is_finalized=BooleanField(default=False) + finalized_at=DateTimeField(null=True)."""
        for M in self._models():
            is_fin = M._meta.get_field('is_finalized')
            fin_at = M._meta.get_field('finalized_at')
            assert isinstance(is_fin, dj_models.BooleanField), f"{M.__name__}.is_finalized type"
            assert isinstance(fin_at, dj_models.DateTimeField), f"{M.__name__}.finalized_at type"
            assert is_fin.default is False, f"{M.__name__}.is_finalized default"
            assert fin_at.null is True, f"{M.__name__}.finalized_at nullable"

    def test_str_defined_t10(self, tech_index):
        """T10: 3개 모델 __str__ 정상 호출."""
        from marketpulse.models.snapshot import (
            BreadthSnapshot,
            ConcentrationSnapshot,
            SectorFlowSnapshot,
        )
        now = timezone.now()
        d = dt_date(2026, 5, 11)
        instances = [
            BreadthSnapshot.objects.create(date=d, snapshot_time=now),
            SectorFlowSnapshot.objects.create(date=d, snapshot_time=now, market_index=tech_index),
            ConcentrationSnapshot.objects.create(date=d, snapshot_time=now),
        ]
        for instance in instances:
            rendered = str(instance)
            assert isinstance(rendered, str) and rendered

    def test_meta_ordering_t11(self):
        """T11: 3개 모두 Meta.ordering 정의."""
        for M in self._models():
            assert M._meta.ordering, f"{M.__name__}.Meta.ordering empty"


@pytest.mark.django_db
class TestIntegrationA3:
    """§5.3 T19 — A2 모델과 공존 (T18은 T6과 중복이라 생략)."""

    def test_regime_and_breadth_same_date_t19(self):
        """T19: 같은 date에 RegimeSnapshot + BreadthSnapshot 공존."""
        from marketpulse.models.regime import RegimeSnapshot
        from marketpulse.models.snapshot import BreadthSnapshot
        d = dt_date(2026, 5, 11)
        now = timezone.now()
        RegimeSnapshot.objects.create(
            date=d, snapshot_time=now,
            regime=RegimeSnapshot.Regime.BULL_EXPANSION,
        )
        BreadthSnapshot.objects.create(date=d, snapshot_time=now)
        assert RegimeSnapshot.objects.filter(date=d).exists()
        assert BreadthSnapshot.objects.filter(date=d).exists()
