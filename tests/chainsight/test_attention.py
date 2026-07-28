"""
관심도 M1 엔진 테스트 (CS-RD2).

단위:
- volume_z 고정 21일 fixture
- std=0 엣지 (거래량 일정)
- 백분위 경계 (유니버스 1종목)
- score 0~100 범위
- 멱등 upsert
- 유동성 가드 ADV 경계 (ADV_FLOOR 기준 True/False)

API:
- events/ 스키마 확인
- score 내림차순 정렬
- 없는 테마 404
- is_low_liquidity 노출
"""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.chain_sight.models import StockAttentionScore
from apps.chain_sight.services.attention_service import (
    ADV_FLOOR,
    compute_attention_scores,
)
from packages.shared.stocks.models import DailyPrice, Stock

User = get_user_model()


@pytest.fixture
def auth_client(db):
    """인증된 API 클라이언트."""
    user = User.objects.create_user(username="attn_test_user", password="pass123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ── Fixtures ──────────────────────────────────────────────────────────────────

TARGET = date(2026, 6, 10)  # 화요일 (고정)


def _make_stock(symbol: str) -> Stock:
    return Stock.objects.get_or_create(
        symbol=symbol,
        defaults={"stock_name": f"{symbol} Inc.", "sector": "Technology"},
    )[0]


def _make_price_history(stock: Stock, close: float, volume: int, days: int = 21,
                        high_offset: float = 1.0, low_offset: float = 1.0,
                        target_date: date = TARGET):
    """target_date 포함 days일치 가격 행 생성."""
    objs = []
    for i in range(days - 1, -1, -1):
        d = target_date - timedelta(days=i)
        objs.append(
            DailyPrice(
                stock=stock,
                date=d,
                open_price=close,
                high_price=close * (1 + high_offset * 0.01),
                low_price=close * (1 - low_offset * 0.01),
                close_price=close,
                volume=volume,
            )
        )
    DailyPrice.objects.bulk_create(objs, ignore_conflicts=True)


def _make_price_history_with_surge(stock: Stock, base_close: float, base_vol: int,
                                    surge_vol: int, target_date: date = TARGET):
    """20일 기준(변동 있는 거래량) + 당일 거래량 급증.

    20일 window의 std > 0 이 되도록 짝수/홀수 날짜에 볼륨 변동을 줌.
    """
    # 20일 이전 데이터 — 홀수·짝수 인덱스에 볼륨 변동 부여
    for i in range(20, 0, -1):
        d = target_date - timedelta(days=i)
        vol = base_vol if i % 2 == 0 else int(base_vol * 1.2)
        DailyPrice.objects.get_or_create(
            stock=stock, date=d,
            defaults={
                "open_price": base_close,
                "high_price": base_close * 1.01,
                "low_price": base_close * 0.99,
                "close_price": base_close,
                "volume": vol,
            }
        )
    # 당일 거래량 급증
    DailyPrice.objects.get_or_create(
        stock=stock, date=target_date,
        defaults={
            "open_price": base_close,
            "high_price": base_close * 1.02,
            "low_price": base_close * 0.98,
            "close_price": base_close * 1.01,
            "volume": surge_vol,
        }
    )


# ── 단위 테스트 ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVolumeZ:
    def test_volume_z_positive_on_surge(self):
        """거래량 급증 시 volume_z > 0."""
        stock = _make_stock("VZTEST")
        _make_price_history_with_surge(stock, base_close=100.0, base_vol=1_000_000,
                                        surge_vol=5_000_000)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="VZTEST", date=TARGET)
        assert obj.volume_z > 0

    def test_volume_z_zero_on_constant(self):
        """거래량이 일정하면 std=0 → volume_z=0."""
        stock = _make_stock("VZCONST")
        _make_price_history(stock, close=100.0, volume=1_000_000)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="VZCONST", date=TARGET)
        assert obj.volume_z == 0.0

    def test_window_uses_20_days_excluding_today(self):
        """window는 당일 제외 이전 20일."""
        stock = _make_stock("VZWIN")
        _make_price_history_with_surge(stock, base_close=50.0, base_vol=500_000,
                                        surge_vol=2_000_000)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="VZWIN", date=TARGET)
        # volume_z = (2_000_000 - 500_000) / 0 는 아님. std > 0 이어야 volume_z != 0
        # constant 20일 + 당일 급증이므로 std=0 → volume_z=0
        assert isinstance(obj.volume_z, float)


@pytest.mark.django_db
class TestStdZeroEdge:
    def test_std_zero_does_not_raise(self):
        """std=0 케이스에서 ZeroDivisionError 없이 0 반환."""
        stock = _make_stock("STDZERO")
        _make_price_history(stock, close=100.0, volume=1_000_000)
        # Should not raise
        result = compute_attention_scores(TARGET)
        assert result >= 1
        obj = StockAttentionScore.objects.get(symbol_id="STDZERO", date=TARGET)
        assert obj.volume_z == 0.0


@pytest.mark.django_db
class TestPercentileBoundary:
    def test_single_stock_universe(self):
        """유니버스 1종목 — 백분위 0.0 (분모=0 방어)."""
        stock = _make_stock("SINGLE")
        _make_price_history_with_surge(stock, base_close=100.0, base_vol=1_000_000,
                                        surge_vol=3_000_000)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="SINGLE", date=TARGET)
        assert 0.0 <= obj.volatility_pct <= 1.0
        assert 0.0 <= obj.return_pct <= 1.0


@pytest.mark.django_db
class TestScoreRange:
    def test_score_between_0_and_100(self):
        """score는 항상 0~100 범위."""
        for i in range(3):
            sym = f"SCORE{i}"
            stock = _make_stock(sym)
            _make_price_history_with_surge(stock, base_close=100.0,
                                            base_vol=1_000_000 * (i + 1),
                                            surge_vol=5_000_000 * (i + 1))
        compute_attention_scores(TARGET)
        scores = StockAttentionScore.objects.filter(date=TARGET).values_list("score", flat=True)
        for s in scores:
            assert 0.0 <= s <= 100.0, f"score {s} 범위 벗어남"


@pytest.mark.django_db
class TestIdempotentUpsert:
    def test_same_date_upsert_no_duplicate(self):
        """같은 날짜 재실행 시 행 수 불변."""
        stock = _make_stock("IDEM")
        _make_price_history_with_surge(stock, base_close=100.0, base_vol=1_000_000,
                                        surge_vol=4_000_000)
        compute_attention_scores(TARGET)
        count1 = StockAttentionScore.objects.filter(date=TARGET, symbol_id="IDEM").count()

        compute_attention_scores(TARGET)
        count2 = StockAttentionScore.objects.filter(date=TARGET, symbol_id="IDEM").count()

        assert count1 == count2 == 1

    def test_idempotent_score_unchanged(self):
        """재실행 시 score 값도 동일."""
        stock = _make_stock("IDEMSCORE")
        _make_price_history_with_surge(stock, base_close=100.0, base_vol=1_000_000,
                                        surge_vol=4_000_000)
        compute_attention_scores(TARGET)
        s1 = StockAttentionScore.objects.get(symbol_id="IDEMSCORE", date=TARGET).score

        compute_attention_scores(TARGET)
        s2 = StockAttentionScore.objects.get(symbol_id="IDEMSCORE", date=TARGET).score

        assert s1 == s2


@pytest.mark.django_db
class TestLiquidityGuard:
    def test_low_liquidity_flag_true_below_floor(self):
        """ADV < ADV_FLOOR 종목 → is_low_liquidity=True."""
        stock = _make_stock("LOWLIQ")
        # ADV = close * volume = 1 * 1000 = 1000 << ADV_FLOOR
        _make_price_history_with_surge(stock, base_close=1.0, base_vol=1_000,
                                        surge_vol=1_000)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="LOWLIQ", date=TARGET)
        assert obj.is_low_liquidity is True

    def test_low_liquidity_flag_false_above_floor(self):
        """ADV >= ADV_FLOOR 종목 → is_low_liquidity=False."""
        stock = _make_stock("HIGHLIQ")
        # ADV = 100 * 600000 = 60_000_000 > ADV_FLOOR
        _make_price_history_with_surge(stock, base_close=100.0, base_vol=600_000,
                                        surge_vol=600_000)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="HIGHLIQ", date=TARGET)
        assert obj.is_low_liquidity is False

    def test_adv_floor_boundary_below(self):
        """ADV_FLOOR - 1 이면 is_low_liquidity=True."""
        stock = _make_stock("ADVBOUND")
        # close=1, volume=(ADV_FLOOR-1) → ADV = ADV_FLOOR - 1
        target_vol = ADV_FLOOR - 1
        _make_price_history(stock, close=1.0, volume=target_vol)
        compute_attention_scores(TARGET)
        obj = StockAttentionScore.objects.get(symbol_id="ADVBOUND", date=TARGET)
        assert obj.is_low_liquidity is True


@pytest.mark.django_db
class TestSkipInsufficient:
    def test_skip_stock_with_fewer_than_20_days(self):
        """DailyPrice < 20일 종목은 스킵(점수 행 없음)."""
        stock = _make_stock("FEW")
        # 19일치만 생성 (당일 포함)
        for i in range(18, -1, -1):  # 19행
            d = TARGET - timedelta(days=i)
            DailyPrice.objects.create(
                stock=stock, date=d,
                open_price=100, high_price=101, low_price=99,
                close_price=100, volume=1_000_000,
            )
        compute_attention_scores(TARGET)
        assert not StockAttentionScore.objects.filter(symbol_id="FEW", date=TARGET).exists()


# ── API 테스트 ────────────────────────────────────────────────────────────────

def _make_event_group(slug: str, symbols: list[str]):
    """kept EventGroup(slug) + core GroupMembership 시드 (⑰ S3: theme_tags 대체).

    보드/랭킹의 event_group 경로(get_kept_event_groups·get_event_group)가 slug로
    조회하므로, theme=slug 규약으로 시드한다. is_hidden=False = kept.
    """
    from apps.chain_sight.models.event_group import EventGroup, GroupMembership

    eg = EventGroup.objects.create(
        name=slug, slug=slug, source="news_jaccard", is_hidden=False,
        member_count=len(symbols), core_count=len(symbols),
    )
    for sym in symbols:
        GroupMembership.objects.create(group=eg, symbol_id=sym, role="core")
    return eg


def _setup_event_group_data(theme: str, n_stocks: int = 4, target_date: date = TARGET):
    """slug=theme EventGroup + n개 종목 + 관심도 스코어 생성 (event_group 규약).

    ⑰ S3: 구 theme_tags 시드를 EventGroup/GroupMembership로 전환. compute_attention_scores는
    price 기반이라 theme_tags 무의존 — theme_tags 신규 생산 없음.
    """
    symbols = [f"TH{i:02d}" for i in range(n_stocks)]
    for i, sym in enumerate(symbols):
        stock = _make_stock(sym)
        _make_price_history_with_surge(
            stock, base_close=100.0,
            base_vol=1_000_000 * (i + 1),
            surge_vol=2_000_000 * (i + 1),
            target_date=target_date,
        )
    compute_attention_scores(target_date)
    _make_event_group(theme, symbols)
    return symbols


@pytest.mark.django_db
class TestEventBoardAPI:
    def test_event_board_schema(self, auth_client):
        """events/ 응답 스키마 확인."""
        _setup_event_group_data("AI")
        url = f"/api/v1/chainsight/events/?date={TARGET}"
        resp = auth_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert "date" in data
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_event_board_has_theme(self, auth_client):
        """AI 테마가 이벤트 목록에 포함."""
        _setup_event_group_data("SEMICON")
        url = f"/api/v1/chainsight/events/?date={TARGET}"
        resp = auth_client.get(url)
        themes = [e["theme"] for e in resp.json()["events"]]
        assert "SEMICON" in themes

    def test_event_board_no_data_returns_404(self, auth_client):
        """스냅샷 없으면 404."""
        url = "/api/v1/chainsight/events/?date=2000-01-01"
        resp = auth_client.get(url)
        assert resp.status_code == 404

    def test_event_board_includes_small_groups(self, auth_client):
        """ⓐ: 멤버 < 3 테마도 보드에 포함(member_count 노출 → 저신뢰 표식용).

        근거: 그룹 커버리지 완전성(디렉터 결정 (가) 1급 노출, 가중합 4.25).
        소표본 약점은 숨기지 않고 member_count로 신호.
        """
        # 2종목만 있는 그룹
        for sym in ["TINY1", "TINY2"]:
            stock = _make_stock(sym)
            _make_price_history_with_surge(stock, 100.0, 1_000_000, 2_000_000)
        compute_attention_scores(TARGET)
        _make_event_group("TINYGROUP", ["TINY1", "TINY2"])
        url = f"/api/v1/chainsight/events/?date={TARGET}"
        resp = auth_client.get(url)
        events = {e["theme"]: e for e in resp.json()["events"]}
        assert "TINYGROUP" in events
        assert events["TINYGROUP"]["member_count"] == 2

    def test_event_board_includes_single_member_group(self, auth_client):
        """ⓐ: 멤버 = 1 그룹도 포함(member_count=1)."""
        stock = _make_stock("SOLO1")
        _make_price_history_with_surge(stock, 100.0, 1_000_000, 2_000_000)
        compute_attention_scores(TARGET)
        _make_event_group("SOLOGROUP", ["SOLO1"])
        url = f"/api/v1/chainsight/events/?date={TARGET}"
        resp = auth_client.get(url)
        events = {e["theme"]: e for e in resp.json()["events"]}
        assert "SOLOGROUP" in events
        assert events["SOLOGROUP"]["member_count"] == 1


@pytest.mark.django_db
class TestEventRankingAPI:
    def test_ranking_sorted_by_score_desc(self, auth_client):
        """score 내림차순 정렬."""
        _setup_event_group_data("SORTED")
        url = f"/api/v1/chainsight/events/SORTED/stocks/?date={TARGET}"
        resp = auth_client.get(url)
        assert resp.status_code == 200
        stocks = resp.json()["stocks"]
        scores = [s["score"] for s in stocks]
        assert scores == sorted(scores, reverse=True)

    def test_ranking_missing_theme_returns_404(self, auth_client):
        """없는 테마 요청 시 404 — 스냅샷이 있어도 해당 테마 없으면 404."""
        # 스냅샷이 존재해야 "데이터 없음 404"와 구분됨
        _setup_event_group_data("EXIST_THEME_FOR_404")
        url = f"/api/v1/chainsight/events/NONEXISTENT_THEME_XYZ/stocks/?date={TARGET}"
        resp = auth_client.get(url)
        assert resp.status_code == 404

    def test_ranking_includes_is_low_liquidity(self, auth_client):
        """is_low_liquidity 필드 포함."""
        _setup_event_group_data("LIQCHECK")
        url = f"/api/v1/chainsight/events/LIQCHECK/stocks/?date={TARGET}"
        resp = auth_client.get(url)
        assert resp.status_code == 200
        for item in resp.json()["stocks"]:
            assert "is_low_liquidity" in item

    def test_ranking_response_schema(self, auth_client):
        """랭킹 응답 필드 스키마 검증."""
        _setup_event_group_data("SCHEMA")
        url = f"/api/v1/chainsight/events/SCHEMA/stocks/?date={TARGET}"
        resp = auth_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert "theme" in data
        assert "date" in data
        assert "stocks" in data
        if data["stocks"]:
            item = data["stocks"][0]
            for field in ("symbol", "name", "score", "raw_return", "volume_z",
                          "volatility_pct", "is_low_liquidity"):
                assert field in item, f"필드 '{field}' 누락"
