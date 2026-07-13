"""
C1 얇은 분기 가드 테스트 (TH-16-RATIFY, 결정28) — representative_series + c1_valuation_from_db.

커버: 정상 통과 / 얇은 최신분기 폴백 / 전부 얇음 결측 / 헬퍼 floor 산식.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.chain_sight.models import QuarterlyValuation
from apps.chain_sight.services.c1_valuation_service import c1_valuation_from_db
from apps.chain_sight.services.heat_components import representative_series


class TestRepresentativeSeries:
    def test_all_full_normal(self):
        # 전부 full(size ≥ floor) → current=last, history=prior (기존 동작 동형)
        vals = [10.0, 11.0, 12.0, 13.0]
        sizes = [50, 50, 50, 50]
        cur, hist, info = representative_series(vals, sizes, ratio=0.60)
        assert cur == 13.0 and hist == [10.0, 11.0, 12.0]
        assert info["floor"] == 30 and info["dropped"] == 0

    def test_thin_current_falls_back(self):
        # 최신 버킷 얇음(n=1) → 드롭, current=직전 full
        vals = [10.0, 11.0, 12.0, 99.0]   # 99=얇은 분기 비대표 median
        sizes = [50, 50, 50, 1]
        cur, hist, info = representative_series(vals, sizes, ratio=0.60)
        assert cur == 12.0                # 99.0 채택 안 됨
        assert hist == [10.0, 11.0]
        assert info["dropped"] == 1

    def test_all_thin_returns_none(self):
        cur, hist, info = representative_series([9.0, 9.5], [2, 3], ratio=0.60)
        # median(sizes)=2.5 → floor=ceil(1.5)=2 → 둘 다 통과? 진짜 결측 케이스 구성
        # (floor보다 작은 표본만) → 아래 케이스로 명시
        cur2, hist2, info2 = representative_series([9.0, 9.5, 9.9], [1, 1, 1], ratio=2.0)
        assert cur2 is None and hist2 == []


@pytest.mark.django_db
class TestC1ThinGuardIntegration:
    def _mk(self, sym, y, q, ev, rev):
        QuarterlyValuation.objects.create(
            symbol=sym, fiscal_date=date(y, q * 3, 28),
            enterprise_value=Decimal(str(ev)), revenue=Decimal(str(rev)),
        )

    def test_thin_latest_quarter_excluded(self):
        # 10개 full 분기(각 10종목, EV/Sales≈10) + 최신분기 1종목(EV/Sales=100 이상치)
        # → 가드 후 history 9개(≥min_n 8) 확보
        syms = [f"S{i}" for i in range(10)]
        fulls = [(2023, 3), (2023, 4), (2024, 1), (2024, 2), (2024, 3),
                 (2024, 4), (2025, 1), (2025, 2), (2025, 3), (2025, 4)]
        for qi, (y, q) in enumerate(fulls):
            for s in syms:
                self._mk(s, y, q, ev=100 + qi, rev=10)  # EV/Sales = 10~10.9
        # 최신분기(2026Q1) = 단 1종목, EV/Sales=100 (이상치)
        self._mk("S0", 2026, 1, ev=1000, rev=10)

        comp = c1_valuation_from_db(syms, date(2026, 6, 1))
        # 가드로 2026Q1(n=1) 제외 → current=2025Q4(정상), z 정상 범위(포화 아님)
        assert comp["z"] is not None
        assert comp["s"] < 0.95  # 100 이상치 median이면 s 포화(≈1.0)였을 것

    def test_thin_latest_quarter_missing_when_history_short(self):
        # full 분기 6개 + 얇은 최신 → 가드 후 history<8 → 결측(min_n 미달)
        syms = [f"S{i}" for i in range(10)]
        for y, q in [(2024, 3), (2024, 4), (2025, 1), (2025, 2), (2025, 3), (2025, 4)]:
            for s in syms:
                self._mk(s, y, q, ev=100, rev=10)
        self._mk("S0", 2026, 1, ev=1000, rev=10)
        comp = c1_valuation_from_db(syms, date(2026, 6, 1))
        assert comp["z"] is None  # 얇은 분기 제외 후 표본 부족
