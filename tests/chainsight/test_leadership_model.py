"""
StockLeadershipScore 모델 테스트 (CS-M2 Slice 2).

- round-trip 저장/조회
- (stock, theme, window) 다중행 허용
- 지표 필드 NULL 허용(게이트 미달)
- unique_together (stock, theme, window, as_of_date)
"""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.chain_sight.models import StockLeadershipScore
from packages.shared.stocks.models import Stock

AS_OF = date(2026, 6, 12)


def _stock(sym: str) -> Stock:
    return Stock.objects.get_or_create(
        symbol=sym, defaults={"stock_name": f"{sym} Inc.", "sector": "Technology"}
    )[0]


@pytest.mark.django_db
class TestRoundTrip:
    def test_save_and_read(self):
        _stock("LEAD1")
        StockLeadershipScore.objects.create(
            stock_id="LEAD1", theme="AI", window=20, as_of_date=AS_OF,
            trend_quality=2.5, theme_alpha=0.1, theme_beta=1.3,
            up_capture=120.0, down_capture=80.0, capture_spread=40.0,
            obs_count=20, is_fallback=False,
        )
        obj = StockLeadershipScore.objects.get(
            stock_id="LEAD1", theme="AI", window=20, as_of_date=AS_OF
        )
        assert obj.trend_quality == pytest.approx(2.5)
        assert obj.theme_beta == pytest.approx(1.3)
        assert obj.capture_spread == pytest.approx(40.0)
        assert obj.obs_count == 20
        assert obj.is_fallback is False


@pytest.mark.django_db
class TestMultiRow:
    def test_same_stock_theme_multiple_windows(self):
        """(stock, theme) 동일하되 window 다르면 다중행 허용."""
        _stock("LEAD2")
        for w in (20, 120):
            StockLeadershipScore.objects.create(
                stock_id="LEAD2", theme="AI", window=w, as_of_date=AS_OF,
                trend_quality=1.0, obs_count=w,
            )
        assert StockLeadershipScore.objects.filter(
            stock_id="LEAD2", theme="AI"
        ).count() == 2

    def test_same_stock_multiple_themes(self):
        """한 종목이 여러 테마에 속하면 테마별 행 생성."""
        _stock("LEAD3")
        for theme in ("AI", "SEMI"):
            StockLeadershipScore.objects.create(
                stock_id="LEAD3", theme=theme, window=20, as_of_date=AS_OF,
                trend_quality=1.0, obs_count=20,
            )
        assert StockLeadershipScore.objects.filter(stock_id="LEAD3").count() == 2


@pytest.mark.django_db
class TestNullFields:
    def test_all_indicator_fields_nullable(self):
        """게이트 미달 — 모든 지표 NULL 저장 가능(에러 아님)."""
        _stock("LEADNULL")
        obj = StockLeadershipScore.objects.create(
            stock_id="LEADNULL", theme="THIN", window=120, as_of_date=AS_OF,
            trend_quality=None, theme_alpha=None, theme_beta=None,
            up_capture=None, down_capture=None, capture_spread=None,
            obs_count=0, is_fallback=True,
        )
        obj.refresh_from_db()
        assert obj.trend_quality is None
        assert obj.theme_alpha is None
        assert obj.theme_beta is None
        assert obj.up_capture is None
        assert obj.capture_spread is None
        assert obj.is_fallback is True


@pytest.mark.django_db
class TestUniqueTogether:
    def test_duplicate_key_raises(self):
        """동일 (stock, theme, window, as_of_date) 중복 → IntegrityError."""
        _stock("LEADUNIQ")
        StockLeadershipScore.objects.create(
            stock_id="LEADUNIQ", theme="AI", window=20, as_of_date=AS_OF,
            trend_quality=1.0, obs_count=20,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                StockLeadershipScore.objects.create(
                    stock_id="LEADUNIQ", theme="AI", window=20, as_of_date=AS_OF,
                    trend_quality=2.0, obs_count=20,
                )
