"""SFI-I1 Part 2 — AnalystSignalSnapshot 모델 + writer 테스트.

D-I1-2 append 전용(동일 심볼 재수집=행 증가) / 유령필드 미러(analyst_target_price + rating*5,
forward_pe 제외 = FORWARD-PE-DEFER) / 부분 실패 격리.
"""
from decimal import Decimal

import pytest

from packages.shared.stocks.models import AnalystSignalSnapshot, Stock
from packages.shared.stocks.services.analyst_signal_writer import (
    capture_symbol,
    capture_symbols,
)


class FakeClient:
    """4 신호 엔드포인트 mock. fail 집합의 심볼은 예외."""

    def __init__(self, fail=(), empty=()):
        self.fail = set(fail)
        self.empty = set(empty)

    def _guard(self, s):
        if s.upper() in self.fail:
            raise RuntimeError(f"boom {s}")

    def get_ratings_snapshot(self, s):
        self._guard(s)
        if s.upper() in self.empty:
            return None
        return {"symbol": s.upper(), "rating": "B", "overallScore": 3}

    def get_price_target_consensus(self, s):
        self._guard(s)
        if s.upper() in self.empty:
            return None
        return {"symbol": s.upper(), "targetHigh": 400, "targetLow": 245,
                "targetConsensus": 340.53, "targetMedian": 350}

    def get_grades_consensus(self, s):
        self._guard(s)
        if s.upper() in self.empty:
            return None
        return {"symbol": s.upper(), "strongBuy": 1, "buy": 70, "hold": 32,
                "sell": 8, "strongSell": 0, "consensus": "Buy"}

    def get_grades_historical(self, s, limit=12):
        self._guard(s)
        if s.upper() in self.empty:
            return []
        return [{"date": "2025-07-01", "analystRatingsBuy": 70,
                 "analystRatingsHold": 32}]


@pytest.mark.django_db
class TestModelAppendOnly:
    def test_same_symbol_recollect_adds_rows(self):
        c = FakeClient()
        capture_symbol(c, "AAPL")
        capture_symbol(c, "AAPL")
        assert AnalystSignalSnapshot.objects.filter(symbol="AAPL").count() == 2

    def test_snapshot_payload_fields(self):
        c = FakeClient()
        capture_symbol(c, "AAPL")
        snap = AnalystSignalSnapshot.objects.get(symbol="AAPL")
        assert snap.target_consensus == Decimal("340.53")
        assert snap.target_high == Decimal("400")
        assert snap.grade_buy == 70 and snap.grade_hold == 32
        assert snap.grade_consensus == "Buy"
        assert snap.rating == "B" and snap.overall_score == 3
        assert isinstance(snap.grades_historical, list) and snap.grades_historical
        assert snap.source == "fmp"


@pytest.mark.django_db
class TestGhostMirror:
    def test_mirror_updates_stock_ghost_fields(self):
        Stock.objects.create(symbol="AAPL", stock_name="Apple")
        c = FakeClient()
        res = capture_symbol(c, "AAPL")
        st = Stock.objects.get(symbol="AAPL")
        assert st.analyst_target_price == Decimal("340.53")
        assert st.analyst_rating_strong_buy == 1
        assert st.analyst_rating_buy == 70
        assert st.analyst_rating_hold == 32
        assert st.analyst_rating_sell == 8
        assert st.analyst_rating_strong_sell == 0
        assert res["mirrored"] is True
        # forward_pe 제외(FORWARD-PE-DEFER) — 미러 대상 아님
        assert st.forward_pe is None

    def test_mirror_skipped_when_no_stock_row(self):
        c = FakeClient()
        res = capture_symbol(c, "TLN")  # Stock 행 없음
        assert AnalystSignalSnapshot.objects.filter(symbol="TLN").count() == 1
        assert res["mirrored"] is False  # 에러 없이 스냅샷만


@pytest.mark.django_db
class TestBatchIsolation:
    def test_one_symbol_failure_does_not_abort_others(self):
        c = FakeClient(fail=["GEV"])
        summary = capture_symbols(c, ["AAPL", "GEV", "TLN"])
        assert AnalystSignalSnapshot.objects.filter(symbol="AAPL").count() == 1
        assert AnalystSignalSnapshot.objects.filter(symbol="TLN").count() == 1
        assert AnalystSignalSnapshot.objects.filter(symbol="GEV").count() == 0
        assert summary["captured"] == 2
        assert summary["failed"] == 1
        assert "GEV" in summary["errors"]

    def test_all_empty_signals_skip_row(self):
        c = FakeClient(empty=["XE"])
        res = capture_symbol(c, "XE")
        assert res["created"] == 0
        assert AnalystSignalSnapshot.objects.filter(symbol="XE").count() == 0
