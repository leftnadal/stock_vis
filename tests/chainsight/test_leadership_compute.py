"""
주도주 지표 영속 서비스 테스트 (CS-M2 Slice 3).

소규모 합성 종목/테마로 compute → 영속 확인, 멱등 upsert.
test DB(자동 마이그레이션) 사용.
"""

import math
from datetime import date, timedelta

import pytest

from apps.chain_sight.models import CompanyChainProfile, StockLeadershipScore
from apps.chain_sight.services.leadership_compute import compute_leadership_scores
from packages.shared.stocks.models import DailyPrice, Stock

AS_OF = date(2026, 6, 12)


def _stock(sym: str) -> Stock:
    return Stock.objects.get_or_create(
        symbol=sym, defaults={"stock_name": f"{sym} Inc.", "sector": "Technology"}
    )[0]


def _make_prices(sym: str, n_days: int, drift: float = 0.005, base: float = 100.0):
    """as_of_date에서 역방향 n_days 영업일(달력일 근사) 종가 생성."""
    stock = _stock(sym)
    objs = []
    # 룩어헤드 차단 확인 위해 미래값도 일부 만들지 않음(as_of 이하만)
    for i in range(n_days):
        d = AS_OF - timedelta(days=(n_days - 1 - i))
        close = base * math.exp(drift * i)
        objs.append(
            DailyPrice(
                stock=stock, date=d,
                open_price=close, high_price=close * 1.01,
                low_price=close * 0.99, close_price=close, volume=1_000_000,
            )
        )
    DailyPrice.objects.bulk_create(objs, ignore_conflicts=True)


def _theme(sym: str, theme: str):
    CompanyChainProfile.objects.update_or_create(
        symbol_id=sym, defaults={"theme_tags": [theme]}
    )


@pytest.mark.django_db
class TestComputePersist:
    def test_compute_creates_rows(self):
        """3종목 테마 → 20 윈도우 행 생성 + 지표 채워짐."""
        for s in ("AA", "BB", "CC"):
            _make_prices(s, 30)
            _theme(s, "AI")
        rows = compute_leadership_scores(AS_OF)
        assert rows > 0
        # 20 윈도우는 30일이면 게이트 통과(>=16)
        w20 = StockLeadershipScore.objects.filter(theme="AI", window=20)
        assert w20.count() == 3
        obj = w20.get(stock_id="AA")
        assert obj.trend_quality is not None  # 직선 상승 → tq 산출
        assert obj.theme_beta is not None     # 테마 정족수 충족 → 베타 산출

    def test_thin_theme_t3_null_t2_present(self):
        """테마 멤버 < 3 → T3/베타 NULL, T2는 산출."""
        for s in ("X1", "X2"):  # 2종목만
            _make_prices(s, 30)
            _theme(s, "THIN")
        compute_leadership_scores(AS_OF)
        obj = StockLeadershipScore.objects.get(stock_id="X1", theme="THIN", window=20)
        assert obj.trend_quality is not None      # 테마무관 → 산출
        assert obj.theme_beta is None             # 정족수 미달 → NULL
        assert obj.theme_alpha is None

    def test_short_history_120_fallback(self):
        """120일 미달 종목 → 120 윈도우 is_fallback=True, 지표 NULL."""
        for s in ("S1", "S2", "S3"):
            _make_prices(s, 30)  # 120 미달
            _theme(s, "SHORT")
        compute_leadership_scores(AS_OF)
        obj120 = StockLeadershipScore.objects.get(stock_id="S1", theme="SHORT", window=120)
        assert obj120.is_fallback is True
        assert obj120.trend_quality is None  # 게이트 미달 → NULL
        obj20 = StockLeadershipScore.objects.get(stock_id="S1", theme="SHORT", window=20)
        assert obj20.is_fallback is False
        assert obj20.trend_quality is not None

    def test_idempotent_upsert(self):
        """재실행 시 행 수 불변(멱등 upsert)."""
        for s in ("M1", "M2", "M3"):
            _make_prices(s, 30)
            _theme(s, "IDEM")
        compute_leadership_scores(AS_OF)
        count1 = StockLeadershipScore.objects.count()
        compute_leadership_scores(AS_OF)
        count2 = StockLeadershipScore.objects.count()
        assert count1 == count2 > 0

    def test_no_data_returns_zero(self):
        """가격 데이터 없으면 0 (에러 아님)."""
        assert compute_leadership_scores(date(2000, 1, 1)) == 0


@pytest.mark.django_db
class TestBeatRegistrationMechanism:
    def test_dry_run_registers_nothing(self):
        """관리 명령 --dry-run은 PeriodicTask 생성하지 않음."""
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        before = PeriodicTask.objects.count()
        call_command("register_chainsight_beats", "--dry-run")
        after = PeriodicTask.objects.count()
        assert before == after

    def test_register_creates_both_beats(self):
        """등록 시 attention/leadership 두 beat 멱등 생성."""
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        call_command("register_chainsight_beats")
        names = set(PeriodicTask.objects.values_list("name", flat=True))
        assert "chainsight-attention-daily" in names
        assert "chainsight-leadership-daily" in names

        # 재실행 멱등
        call_command("register_chainsight_beats")
        assert PeriodicTask.objects.filter(
            name="chainsight-leadership-daily"
        ).count() == 1
