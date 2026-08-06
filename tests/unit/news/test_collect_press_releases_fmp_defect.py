"""collect_press_releases_fmp 시가총액 정렬 defect 회귀 (NEWS-P0-FIX T2/S1).

배경(RECON-NEWS-P0): SP500Constituent에는 market_cap 필드 자체가 없어
`.order_by("-market_cap")`이 매 beat FieldError로 무음 전량 실패했다
(services/news/tasks.py 옛 :1093). Stock.market_capitalization 채움율이
STEP 0 실측 98.83%(≥80%) 이므로 SP500Constituent(활성)↔Stock을 심볼로 조인해
market_capitalization 내림차순 정렬하도록 수리했다.

이 테스트는 FieldError 재발 시 즉시 red 되는 형태 — 태스크를 실제로 호출해
FieldError(구 버그)가 다시 나면 실패한다.
"""
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.stocks.models import SP500Constituent, Stock
from services.news.tasks import collect_press_releases_fmp


def _make_sp500_and_stock(symbol, market_cap, is_active=True):
    SP500Constituent.objects.create(
        symbol=symbol,
        company_name=f"{symbol} Inc.",
        sector="Technology",
        is_active=is_active,
    )
    Stock.objects.create(symbol=symbol, market_capitalization=market_cap)


@pytest.mark.django_db
class TestCollectPressReleasesFmpDefect:
    def test_no_field_error_and_orders_by_market_capitalization_desc(self):
        _make_sp500_and_stock("AAA", 100)
        _make_sp500_and_stock("BBB", 300)
        _make_sp500_and_stock("CCC", 200)
        # 비활성 SP500 종목 — 결과에서 제외되어야 함
        _make_sp500_and_stock("DDD", 999, is_active=False)

        agg = MagicMock()
        agg.fetch_and_save_press_releases.return_value = {"saved": 1, "updated": 0}

        with patch(
            "services.news.services.aggregator.NewsAggregatorService",
            return_value=agg,
        ):
            # FieldError(구 버그)가 재발하면 여기서 예외가 터져 테스트가 red 된다.
            result = collect_press_releases_fmp.apply(kwargs={"max_symbols": 50}).get()

        called_symbols = [c.args[0] for c in agg.fetch_and_save_press_releases.call_args_list]
        assert called_symbols == ["BBB", "CCC", "AAA"]  # market_cap 내림차순
        assert "DDD" not in called_symbols
        assert result["saved"] == 3

    def test_respects_max_symbols_limit(self):
        for i in range(5):
            _make_sp500_and_stock(f"S{i}", 100 + i)

        agg = MagicMock()
        agg.fetch_and_save_press_releases.return_value = {"saved": 0, "updated": 0}

        with patch(
            "services.news.services.aggregator.NewsAggregatorService",
            return_value=agg,
        ):
            collect_press_releases_fmp.apply(kwargs={"max_symbols": 2}).get()

        assert agg.fetch_and_save_press_releases.call_count == 2

    def test_null_market_cap_excluded_not_errored(self):
        _make_sp500_and_stock("HASCAP", 500)
        # market_capitalization=None — 상위 랭킹에서 자연 제외(에러 아님)
        SP500Constituent.objects.create(
            symbol="NOCAP", company_name="NoCap Inc.", sector="Technology", is_active=True
        )
        Stock.objects.create(symbol="NOCAP", market_capitalization=None)

        agg = MagicMock()
        agg.fetch_and_save_press_releases.return_value = {"saved": 0, "updated": 0}

        with patch(
            "services.news.services.aggregator.NewsAggregatorService",
            return_value=agg,
        ):
            result = collect_press_releases_fmp.apply(kwargs={"max_symbols": 50}).get()

        called_symbols = [c.args[0] for c in agg.fetch_and_save_press_releases.call_args_list]
        assert called_symbols == ["HASCAP"]
        assert "NOCAP" not in called_symbols
        assert result["errors"] == 0
