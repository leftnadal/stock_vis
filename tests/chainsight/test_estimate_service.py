"""
C8 원장 스냅샷 서비스 테스트 (TH-3, 설계서 §5.3 · §6.6).

검증:
- fiscal_year 추출 + 당기·차기 2행 선택.
- 필드 매핑(epsAvg→eps_avg 등) + 멱등 upsert.
- 데이터 없음 처리 + 종목 실패 격리.
"""

from datetime import date

import pytest

from apps.chain_sight.models import EstimateSnapshot
from apps.chain_sight.services import estimate_service as es


class _FakeClient:
    def __init__(self, by_symbol=None, raise_on=None):
        self._by_symbol = by_symbol or {}
        self._raise_on = raise_on or set()

    def get_analyst_estimates(self, symbol, period="annual", limit=10):
        if symbol.upper() in self._raise_on:
            raise RuntimeError("boom")
        return self._by_symbol.get(symbol.upper(), [])


def _row(year, eps_avg, eps_high=None, eps_low=None, n=10, rev=None):
    return {
        "symbol": "AAA",
        "date": f"{year}-12-31",
        "epsAvg": eps_avg,
        "epsHigh": eps_high,
        "epsLow": eps_low,
        "numAnalystsEps": n,
        "revenueAvg": rev,
    }


class TestSelection:
    def test_fiscal_year_extraction(self):
        assert es._fiscal_year({"date": "2027-09-27"}) == 2027
        assert es._fiscal_year({"date": ""}) is None

    def test_selects_current_and_next_two(self):
        rows = [_row(2026, 5), _row(2027, 6), _row(2028, 7), _row(2029, 8)]
        picked = es.select_current_and_next(rows, as_of_year=2026)
        assert [es._fiscal_year(r) for r in picked] == [2026, 2027]

    def test_selects_nearest_future_when_no_current(self):
        """FMP 가 미래연도만 줄 때(예 2027~) as_of 이상 최소 2개."""
        rows = [_row(2027, 6), _row(2028, 7), _row(2029, 8)]
        picked = es.select_current_and_next(rows, as_of_year=2026)
        assert [es._fiscal_year(r) for r in picked] == [2027, 2028]


@pytest.mark.django_db
class TestSnapshot:
    def test_snapshot_symbol_maps_fields_and_two_rows(self):
        client = _FakeClient(by_symbol={"AAA": [
            _row(2026, 5.5, 6.0, 5.0, n=12, rev=1000),
            _row(2027, 6.5, 7.0, 6.0, n=14, rev=1200),
        ]})
        res = es.snapshot_symbol(client, "AAA", date(2026, 7, 10))
        assert res["created"] == 2 and res["rows"] == 2
        snap = EstimateSnapshot.objects.get(symbol="AAA", fiscal_year=2026)
        assert float(snap.eps_avg) == 5.5
        assert float(snap.eps_high) == 6.0
        assert snap.num_analysts_eps == 12
        assert float(snap.revenue_avg) == 1000
        assert snap.snapshot_date == date(2026, 7, 10)

    def test_idempotent_reupsert(self):
        client = _FakeClient(by_symbol={"AAA": [_row(2026, 5.5), _row(2027, 6.5)]})
        es.snapshot_symbol(client, "AAA", date(2026, 7, 10))
        res2 = es.snapshot_symbol(client, "AAA", date(2026, 7, 10))
        assert res2["created"] == 0 and res2["updated"] == 2
        assert EstimateSnapshot.objects.filter(symbol="AAA").count() == 2

    def test_no_data(self):
        res = es.snapshot_symbol(_FakeClient(), "NONE", date(2026, 7, 10))
        assert res["rows"] == 0

    def test_batch_isolates_symbol_errors(self):
        client = _FakeClient(
            by_symbol={"AAA": [_row(2026, 5.5), _row(2027, 6.5)]},
            raise_on={"BAD"},
        )
        agg = es.snapshot_estimates_for_symbols(client, ["AAA", "BAD"], date(2026, 7, 10))
        assert agg["symbols"] == 2
        assert agg["created"] == 2
        assert agg["errors"] == 1  # BAD 격리, AAA 정상
