"""SFI-I1 Part 1 — FMP 래퍼 forward 신호 메서드 파싱 테스트.

recon 프리플라이트 실측 필드(2026-08-01) 기준 fixture. 5 신규 메서드 + get_rating 오경로 교정.
mock = client._make_request 패치(HTTP 미발생) / get_rating = httpx.Client 패치.
"""
from unittest.mock import Mock, patch

import pytest

from packages.shared.api_request.providers.fmp.client import FMPClient
from packages.shared.stocks.services.fmp_fundamentals import FMPFundamentalsService


@pytest.fixture
def client():
    return FMPClient(api_key="test-key")


# ---- recon 실측 fixture (2026-08-01 AAPL) ----
RATINGS_SNAPSHOT = [{
    "symbol": "AAPL", "rating": "B", "overallScore": 3,
    "discountedCashFlowScore": 3, "returnOnEquityScore": 5,
    "returnOnAssetsScore": 5, "debtToEquityScore": 1,
    "priceToEarningsScore": 2, "priceToBookScore": 1,
}]
PT_CONSENSUS = [{
    "symbol": "AAPL", "targetHigh": 400, "targetLow": 245,
    "targetConsensus": 340.53, "targetMedian": 350,
}]
PT_SUMMARY = [{
    "symbol": "AAPL", "lastMonthCount": 5, "lastMonthAvgPriceTarget": 330.0,
    "lastQuarterCount": 12, "lastQuarterAvgPriceTarget": 320.0,
    "lastYearCount": 40, "lastYearAvgPriceTarget": 300.0,
    "allTimeCount": 100, "allTimeAvgPriceTarget": 280.0, "publishers": "[]",
}]
GRADES_CONSENSUS = [{
    "symbol": "AAPL", "strongBuy": 1, "buy": 70, "hold": 32,
    "sell": 8, "strongSell": 0, "consensus": "Buy",
}]
GRADES_HISTORICAL = [
    {"symbol": "AAPL", "date": "2025-07-01", "analystRatingsStrongBuy": 1,
     "analystRatingsBuy": 70, "analystRatingsHold": 32,
     "analystRatingsSell": 8, "analystRatingsStrongSell": 0},
    {"symbol": "AAPL", "date": "2025-06-01", "analystRatingsStrongBuy": 1,
     "analystRatingsBuy": 68, "analystRatingsHold": 33,
     "analystRatingsSell": 8, "analystRatingsStrongSell": 0},
]


class TestRatingsSnapshot:
    def test_parses_first_row(self, client):
        with patch.object(client, "_make_request", return_value=RATINGS_SNAPSHOT) as m:
            out = client.get_ratings_snapshot("aapl")
        assert out["rating"] == "B"
        assert out["overallScore"] == 3
        # 경로·심볼 대문자화 검증
        args, kwargs = m.call_args
        assert args[0] == "/stable/ratings-snapshot"
        assert args[1]["symbol"] == "AAPL"

    def test_empty_returns_none(self, client):
        with patch.object(client, "_make_request", return_value=[]):
            assert client.get_ratings_snapshot("AAPL") is None


class TestPriceTarget:
    def test_consensus_parses(self, client):
        with patch.object(client, "_make_request", return_value=PT_CONSENSUS) as m:
            out = client.get_price_target_consensus("AAPL")
        assert out["targetConsensus"] == 340.53
        assert out["targetHigh"] == 400 and out["targetLow"] == 245
        assert m.call_args[0][0] == "/stable/price-target-consensus"

    def test_summary_parses(self, client):
        with patch.object(client, "_make_request", return_value=PT_SUMMARY) as m:
            out = client.get_price_target_summary("AAPL")
        assert out["lastYearAvgPriceTarget"] == 300.0
        assert m.call_args[0][0] == "/stable/price-target-summary"

    def test_consensus_empty_none(self, client):
        with patch.object(client, "_make_request", return_value=[]):
            assert client.get_price_target_consensus("AAPL") is None


class TestGrades:
    def test_consensus_parses(self, client):
        with patch.object(client, "_make_request", return_value=GRADES_CONSENSUS) as m:
            out = client.get_grades_consensus("AAPL")
        assert out["consensus"] == "Buy"
        assert out["buy"] == 70 and out["hold"] == 32
        assert m.call_args[0][0] == "/stable/grades-consensus"

    def test_historical_returns_list(self, client):
        with patch.object(client, "_make_request", return_value=GRADES_HISTORICAL) as m:
            out = client.get_grades_historical("AAPL", limit=12)
        assert isinstance(out, list) and len(out) == 2
        assert out[0]["analystRatingsBuy"] == 70
        assert m.call_args[0][0] == "/stable/grades-historical"
        assert m.call_args[0][1]["limit"] == 12

    def test_historical_empty_returns_list(self, client):
        with patch.object(client, "_make_request", return_value=[]):
            assert client.get_grades_historical("AAPL") == []


class TestAnalystEstimatesExistsOnly:
    """B2: SFI는 estimates 신규 수집 안 함 — 기존 메서드 존재·annual 기본만 확인."""

    def test_method_exists_and_defaults_annual(self, client):
        assert hasattr(client, "get_analyst_estimates")
        with patch.object(client, "_make_request", return_value=[]) as m:
            client.get_analyst_estimates("AAPL")
        assert m.call_args[0][1]["period"] == "annual"


class TestGetRatingPathFix:
    """#80: get_rating이 /stable/rating(404) → /stable/ratings-snapshot 교정. 행위=None→값."""

    @patch("packages.shared.stocks.services.fmp_fundamentals.httpx.Client")
    def test_get_rating_uses_ratings_snapshot_and_returns_value(self, mock_cls):
        resp = Mock()
        resp.json.return_value = RATINGS_SNAPSHOT
        resp.raise_for_status.return_value = None
        ctx = mock_cls.return_value.__enter__.return_value
        ctx.get.return_value = resp

        svc = FMPFundamentalsService()
        svc.api_key = "test-key"  # settings 미설정 방어
        from django.core.cache import cache
        cache.delete("fmp:rating:AAPL")

        out = svc.get_rating("AAPL")
        assert out is not None            # None→값 (회귀 아님, 항상 None이던 것이 값)
        assert out["rating"] == "B"
        called_url = ctx.get.call_args[0][0]
        assert "ratings-snapshot" in called_url
        assert not called_url.endswith("/stable/rating")
