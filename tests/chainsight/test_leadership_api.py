"""
주도주 지표 API 확장 테스트 (CS-M2 Slice 4).

- 응답 스키마에 주도주 지표 필드 추가
- 기존 M1 필드 보존(RD3 회귀 0)
- window 파라미터(기본 20, 잘못된 값 폴백)
- 보드(EventBoardItemSerializer) 미변경
"""

import math
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.chain_sight.models import CompanyChainProfile
from apps.chain_sight.services.attention_service import compute_attention_scores
from apps.chain_sight.services.leadership_compute import compute_leadership_scores
from packages.shared.stocks.models import DailyPrice, Stock

User = get_user_model()
AS_OF = date(2026, 6, 12)

# M1 불변 필드 — RD3 회귀 0 보증 대상
M1_FIELDS = (
    "symbol", "name", "score", "raw_return",
    "volume_z", "volatility_pct", "is_low_liquidity",
)
M2_FIELDS = (
    "trend_quality", "theme_alpha", "theme_beta",
    "up_capture", "down_capture", "capture_spread", "is_fallback",
)


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="lead_api_user", password="pass123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _stock(sym: str) -> Stock:
    return Stock.objects.get_or_create(
        symbol=sym, defaults={"stock_name": f"{sym} Inc.", "sector": "Technology"}
    )[0]


def _make_prices(sym: str, n_days: int = 30, drift: float = 0.005):
    stock = _stock(sym)
    objs = []
    for i in range(n_days):
        d = AS_OF - timedelta(days=(n_days - 1 - i))
        close = 100.0 * math.exp(drift * i)
        objs.append(
            DailyPrice(
                stock=stock, date=d,
                open_price=close, high_price=close * 1.02,
                low_price=close * 0.98, close_price=close, volume=1_000_000 * (i % 5 + 1),
            )
        )
    DailyPrice.objects.bulk_create(objs, ignore_conflicts=True)


def _setup(theme: str, n: int = 4):
    syms = [f"L{i:02d}" for i in range(n)]
    for s in syms:
        _make_prices(s)
        CompanyChainProfile.objects.update_or_create(
            symbol_id=s, defaults={"theme_tags": [theme]}
        )
    compute_attention_scores(AS_OF)
    compute_leadership_scores(AS_OF)
    return syms


@pytest.mark.django_db
class TestRankingLeadershipFields:
    def test_m2_fields_present(self, auth_client):
        """랭킹 응답에 주도주 지표 필드 노출."""
        _setup("AILEAD")
        resp = auth_client.get(f"/api/v1/chainsight/events/AILEAD/stocks/?date={AS_OF}")
        assert resp.status_code == 200
        item = resp.json()["stocks"][0]
        for f in M2_FIELDS:
            assert f in item, f"M2 필드 '{f}' 누락"

    def test_m1_fields_preserved(self, auth_client):
        """기존 M1 필드 전부 보존 — RD3 회귀 0."""
        _setup("PRESERVE")
        resp = auth_client.get(f"/api/v1/chainsight/events/PRESERVE/stocks/?date={AS_OF}")
        item = resp.json()["stocks"][0]
        for f in M1_FIELDS:
            assert f in item, f"M1 필드 '{f}' 누락(회귀)"

    def test_trend_quality_populated(self, auth_client):
        """직선 상승 + 테마 정족수 → trend_quality·theme_beta 채워짐."""
        _setup("POP")
        resp = auth_client.get(f"/api/v1/chainsight/events/POP/stocks/?date={AS_OF}")
        items = resp.json()["stocks"]
        assert any(it["trend_quality"] is not None for it in items)
        assert any(it["theme_beta"] is not None for it in items)


@pytest.mark.django_db
class TestWindowParam:
    def test_default_window_is_20(self, auth_client):
        _setup("WDEF")
        resp = auth_client.get(f"/api/v1/chainsight/events/WDEF/stocks/?date={AS_OF}")
        assert resp.json()["window"] == 20

    def test_explicit_window_120(self, auth_client):
        _setup("W120")
        resp = auth_client.get(
            f"/api/v1/chainsight/events/W120/stocks/?date={AS_OF}&window=120"
        )
        assert resp.json()["window"] == 120
        # 120 윈도우는 30일 데이터 → 게이트 미달 NULL이지만 키는 노출
        item = resp.json()["stocks"][0]
        assert "trend_quality" in item

    def test_invalid_window_falls_back_to_20(self, auth_client):
        _setup("WBAD")
        resp = auth_client.get(
            f"/api/v1/chainsight/events/WBAD/stocks/?date={AS_OF}&window=999"
        )
        assert resp.json()["window"] == 20

    def test_nonint_window_falls_back(self, auth_client):
        _setup("WNAN")
        resp = auth_client.get(
            f"/api/v1/chainsight/events/WNAN/stocks/?date={AS_OF}&window=abc"
        )
        assert resp.json()["window"] == 20


@pytest.mark.django_db
class TestBoardUnchanged:
    def test_event_board_schema_unchanged(self, auth_client):
        """보드 응답에 M2 필드가 새지 않음(EventBoardItemSerializer 미변경)."""
        _setup("BOARDCHK")
        resp = auth_client.get(f"/api/v1/chainsight/events/?date={AS_OF}")
        assert resp.status_code == 200
        events = resp.json()["events"]
        if events:
            board_item = events[0]
            for f in M2_FIELDS:
                assert f not in board_item, f"보드에 M2 필드 '{f}' 누출"
            # 기존 보드 필드 존재
            for f in ("theme", "member_count", "avg_score"):
                assert f in board_item
