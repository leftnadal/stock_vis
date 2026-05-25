"""iron-trading /api/v1/iron-trading/daily-context 계약 테스트.

read-only API. 200/400/404/503 모두 커버.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


TRADING_DATE = date(2026, 5, 22)
ENDPOINT = "/api/v1/iron-trading/daily-context"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_us_stock(symbol: str, sector: str = "Technology", price: str = "100.00") -> "Stock":
    from stocks.models import Stock

    return Stock.objects.create(
        symbol=symbol,
        stock_name=f"{symbol} Inc.",
        exchange="NASDAQ",
        currency="USD",
        sector=sector,
        industry=f"{sector} sub",
        real_time_price=Decimal(price),
    )


def _seed_krw_stock(symbol: str = "005930.KS") -> "Stock":
    from stocks.models import Stock

    return Stock.objects.create(
        symbol=symbol,
        stock_name="Samsung Electronics",
        exchange="KRX",
        currency="KRW",
        sector="Technology",
        real_time_price=Decimal("70000"),
    )


def _seed_prices(stock, end_date: date, days: int = 65, base: float = 100.0):
    """가장 최근 종가가 가장 높도록 단조 상승 OHLCV를 생성."""
    from stocks.models import DailyPrice

    rows = []
    d = end_date - timedelta(days=days - 1)
    for i in range(days):
        price = Decimal(str(base + i * 0.5))
        rows.append(
            DailyPrice(
                stock=stock,
                date=d + timedelta(days=i),
                open_price=price - Decimal("0.5"),
                high_price=price + Decimal("0.5"),
                low_price=price - Decimal("1.0"),
                close_price=price,
                volume=1_000_000 + i * 10_000,
            )
        )
    DailyPrice.objects.bulk_create(rows)
    return rows


def _seed_eod_signal(stock, signal_date: date, composite: float, count: int = 3) -> "EODSignal":
    from stocks.models import EODSignal

    return EODSignal.objects.create(
        stock=stock,
        date=signal_date,
        signals=[{"id": "V1", "category": "volume"}] * count,
        tag_details={"primary": "V1"},
        signal_count=count,
        bullish_count=count,
        bearish_count=0,
        composite_score=composite,
        close_price=Decimal("130.00"),
        change_percent=1.5,
        volume=2_000_000,
        dollar_volume=Decimal("260000000.00"),
        sector=stock.sector or "",
        industry=stock.industry or "",
    )


@pytest.fixture
def api_client():
    return APIClient()


# ---------------------------------------------------------------------------
# 400 - Bad Request
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBadRequest:
    def test_missing_date_returns_400(self, api_client):
        resp = api_client.get(ENDPOINT)
        assert resp.status_code == 400
        body = resp.json()
        assert body["provider"] == "stock_vis"
        assert body["error"]["code"] == "missing_date"

    def test_invalid_date_format_returns_400(self, api_client):
        resp = api_client.get(ENDPOINT, {"date": "2026/05/22"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_date"

    def test_invalid_limit_returns_400(self, api_client):
        resp = api_client.get(ENDPOINT, {"date": "2026-05-22", "limit": "abc"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_limit"

    def test_limit_out_of_range_returns_400(self, api_client):
        resp = api_client.get(ENDPOINT, {"date": "2026-05-22", "limit": "0"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_limit"

    def test_unsupported_universe_returns_400(self, api_client):
        resp = api_client.get(ENDPOINT, {"date": "2026-05-22", "universe": "kr_core"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "unsupported_universe"


# ---------------------------------------------------------------------------
# 404 - Snapshot Not Found
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotFound:
    def test_no_data_returns_404(self, api_client):
        resp = api_client.get(ENDPOINT, {"date": "2099-01-01"})
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "snapshot_not_found"


# ---------------------------------------------------------------------------
# 503 - Snapshot Building
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSnapshotBuilding:
    def test_pipeline_running_returns_503(self, api_client):
        from stocks.models import PipelineLog

        PipelineLog.objects.create(
            date=TRADING_DATE,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "snapshot_not_ready"
        assert "retry_after_seconds" in body["error"]
        assert resp.headers.get("Retry-After") == "300"

    def test_no_us_candidates_returns_503(self, api_client):
        """KRW 종목만 있고 미국 가격이 없으면 후보 미성립으로 503."""
        krw = _seed_krw_stock()
        _seed_prices(krw, TRADING_DATE, days=30, base=70000)

        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "snapshot_not_ready"


# ---------------------------------------------------------------------------
# 200 - Happy Path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSuccessful:
    def test_returns_contract_shape(self, api_client):
        nvda = _seed_us_stock("NVDA", "Technology", "950.12")
        _seed_prices(nvda, TRADING_DATE, days=65, base=900.0)
        _seed_eod_signal(nvda, TRADING_DATE, composite=0.72)

        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        assert resp.status_code == 200
        body = resp.json()

        # top-level
        assert body["schema_version"] == "1.0"
        assert body["provider"] == "stock_vis"
        assert body["trading_date"] == "2026-05-22"
        assert body["market_timezone"] == "America/New_York"
        assert body["universe"] == "us_core"
        assert body["snapshot_id"].startswith("stockvis-us-2026-05-22-")

        # freshness
        assert body["freshness"]["status"] in {"fresh", "stale", "partial"}
        assert isinstance(body["freshness"]["warnings"], list)
        assert body["freshness"]["max_age_minutes"] == 1440

        # market_pulse (regime 없을 때도 기본값 보장)
        mp = body["market_pulse"]
        assert mp["regime_hint"]
        assert mp["summary"]
        assert isinstance(mp["risk_notes"], list)
        assert isinstance(mp["opportunity_notes"], list)

        # chain_sight 스키마 유지 (없어도 dict)
        assert "summary" in body["chain_sight"]
        assert isinstance(body["chain_sight"]["themes"], list)

        # candidate 검증
        assert len(body["candidates"]) == 1
        cand = body["candidates"][0]
        assert cand["symbol"] == "NVDA"
        assert cand["currency"] == "USD"
        assert cand["rank"] == 1
        assert cand["thesis"]
        assert isinstance(cand["risk_flags"], list)
        assert isinstance(cand["tags"], list)
        assert len(cand["ohlcv"]) >= 20
        # ohlcv는 문자열 직렬화
        first = cand["ohlcv"][0]
        for key in ("open", "high", "low", "close", "volume", "date"):
            assert isinstance(first[key], str)
        # signals
        sigs = cand["signals"]
        for key in (
            "momentum_20d",
            "momentum_60d",
            "sma20_distance_pct",
            "sma50_distance_pct",
            "volume_ratio_20d",
            "relative_strength_rank",
            "breakout_score",
            "pullback_quality",
        ):
            assert key in sigs
        assert sigs["relative_strength_rank"] == 1

    def test_us_only_filter_excludes_krw(self, api_client):
        nvda = _seed_us_stock("NVDA")
        _seed_prices(nvda, TRADING_DATE, days=30)
        _seed_eod_signal(nvda, TRADING_DATE, composite=0.50)

        krw = _seed_krw_stock()
        _seed_prices(krw, TRADING_DATE, days=30, base=70000)
        _seed_eod_signal(krw, TRADING_DATE, composite=0.95, count=5)  # 더 높은 점수지만 KRW

        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        assert resp.status_code == 200
        symbols = [c["symbol"] for c in resp.json()["candidates"]]
        assert "NVDA" in symbols
        assert "005930.KS" not in symbols

    def test_limit_respected(self, api_client):
        for i in range(5):
            sym = f"SYM{i}"
            s = _seed_us_stock(sym)
            _seed_prices(s, TRADING_DATE, days=25, base=50.0 + i)
            _seed_eod_signal(s, TRADING_DATE, composite=0.1 * i)

        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat(), "limit": "3"})
        assert resp.status_code == 200
        assert len(resp.json()["candidates"]) == 3

    def test_rank_descending_by_score(self, api_client):
        for i, comp in enumerate([0.1, 0.9, 0.5]):
            s = _seed_us_stock(f"R{i}")
            _seed_prices(s, TRADING_DATE, days=25, base=50.0 + i)
            _seed_eod_signal(s, TRADING_DATE, composite=comp)

        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        body = resp.json()
        ranks = [(c["symbol"], c["rank"], Decimal(c["score"])) for c in body["candidates"]]
        # rank 1이 가장 높은 score
        ranks_sorted_by_rank = sorted(ranks, key=lambda x: x[1])
        scores = [r[2] for r in ranks_sorted_by_rank]
        assert scores == sorted(scores, reverse=True)

    def test_fallback_to_daily_price_when_no_eod_signal(self, api_client):
        """EODSignal이 비어도 DailyPrice만으로 후보 구성 가능."""
        s = _seed_us_stock("AAPL")
        _seed_prices(s, TRADING_DATE, days=25, base=150.0)

        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        assert resp.status_code == 200
        cand = resp.json()["candidates"][0]
        assert cand["symbol"] == "AAPL"
        # composite_score 없으므로 0.5 (neutral)
        assert cand["score"] == "0.5000"

    def test_snapshot_id_is_deterministic(self, api_client):
        s = _seed_us_stock("NVDA")
        _seed_prices(s, TRADING_DATE, days=30)
        _seed_eod_signal(s, TRADING_DATE, composite=0.5)

        resp1 = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        resp2 = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        assert resp1.status_code == 200
        assert resp1.json()["snapshot_id"] == resp2.json()["snapshot_id"]

    def test_no_internal_orm_objects_leak(self, api_client):
        """응답에 내부 모델 필드명(snake_case로 노출되어선 안 되는 것)이 새지 않는지."""
        s = _seed_us_stock("NVDA")
        _seed_prices(s, TRADING_DATE, days=25)
        _seed_eod_signal(s, TRADING_DATE, composite=0.5)
        resp = api_client.get(ENDPOINT, {"date": TRADING_DATE.isoformat()})
        cand = resp.json()["candidates"][0]
        # 내부 EODSignal 필드명 (응답 계약에 없는 것) 누수 금지
        forbidden = {"composite_score", "dollar_volume", "tag_details", "stock_id", "news_context"}
        leaked = forbidden.intersection(cand.keys()) | forbidden.intersection(cand.get("signals", {}).keys())
        assert leaked == set()
