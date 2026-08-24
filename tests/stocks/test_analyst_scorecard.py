"""D1-SCOREBOARD Part 1 — 애널리스트 성적판 (build_scorecard 순수 함수 + read API).

compute-on-read: DB 쓰기 0. 기존 score_tier1 집계 무접촉(행위보존) + 동일 순수 코어
재사용. 커버: 상태 3종(scored/pending/unscoreable) 분기, 집계 산식(board·symbol),
0-5 실측 엣지(유지 신호·무목표가), 캐시 키 회전, API 봉투·인증·h 검증.
"""
from datetime import date, datetime, timedelta
from datetime import timezone as dt_tz
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from packages.shared.stocks.models import (
    AnalystSignalSnapshot,
    DailyPrice,
    Stock,
    StockSplit,
)
from packages.shared.stocks.services import analyst_scoring as sc

User = get_user_model()
URL = "/api/v1/coach/analyst-scorecard/"
AS_OF = date(2026, 8, 19)
START = date(2026, 8, 1)


# ── 픽스처 헬퍼 ──
def _stock(sym):
    return Stock.objects.filter(symbol=sym).first() or Stock.objects.create(symbol=sym)


def _bars(sym, start, closes):
    """연속 거래일 bar 생성(resolve_realized는 인덱스 기반 → 요일 무관)."""
    st = _stock(sym)
    for i, c in enumerate(closes):
        d = Decimal(str(c))
        DailyPrice.objects.create(
            stock=st, date=start + timedelta(days=i),
            open_price=d, high_price=d, low_price=d, close_price=d, volume=0,
        )
    return st


def _sig(sym, cap_date, target, spot):
    """AnalystSignalSnapshot 1건. captured_at은 auto_now_add → update로 앵커."""
    s = AnalystSignalSnapshot.objects.create(
        symbol=sym,
        target_consensus=Decimal(str(target)) if target is not None else None,
        spot_at_capture=Decimal(str(spot)) if spot is not None else None,
    )
    dt = datetime(cap_date.year, cap_date.month, cap_date.day, 12, 0, tzinfo=dt_tz.utc)
    AnalystSignalSnapshot.objects.filter(pk=s.pk).update(captured_at=dt)
    return s


def _one(payload, sym):
    return next(s for s in payload["symbols"] if s["symbol"] == sym)


# ============================================================
# build_scorecard — 상태 분기 + 판정
# ============================================================
@pytest.mark.django_db
class TestScorecardStatus:
    def test_scored_hit(self):
        # 상승 전망(100→110) · 실현 115 → 방향 적중 hit, tp=150%.
        _bars("AAA", START, [100, 101, 102, 115, 116])
        _sig("AAA", START, target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        sig = _one(p, "AAA")["signals"][0]
        assert sig["status"] == "scored"
        assert sig["direction"] == "up"
        assert sig["realized"]["verdict"] == "hit"
        assert sig["realized"]["close"] == 115.0
        assert sig["realized"]["return_pct"] == 15.0
        assert sig["realized"]["target_progress_pct"] == 150.0
        assert sig["maturity_date"] == (START + timedelta(days=3)).isoformat()

    def test_scored_miss(self):
        # 상승 전망(100→110)이나 실현 하락 90 → miss.
        _bars("BBB", START, [100, 99, 95, 90, 88])
        _sig("BBB", START, target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        sig = _one(p, "BBB")["signals"][0]
        assert sig["realized"]["verdict"] == "miss"
        assert sig["realized"]["return_pct"] == -10.0

    def test_pending_immature(self):
        # 최근 포착 + h 미도달 → pending, d-day 양수.
        _bars("PEND", date(2026, 8, 17), [100, 101, 102])
        _sig("PEND", date(2026, 8, 17), target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=21)
        sig = _one(p, "PEND")["signals"][0]
        assert sig["status"] == "pending"
        assert sig["realized"] is None
        assert sig["pending_d_day"] is not None and sig["pending_d_day"] > 0

    def test_unscoreable_corporate_action(self):
        # 예측~만기 구간 내 분할 → 원시 close 오염 → unscoreable.
        st = _bars("SPLT", START, [100, 101, 102, 115, 116])
        StockSplit.objects.create(stock=st, date=START + timedelta(days=2),
                                  numerator=2, denominator=1)
        _sig("SPLT", START, target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        sig = _one(p, "SPLT")["signals"][0]
        assert sig["status"] == "unscoreable"
        assert sig["unscoreable_reason"] == "corporate_action"

    def test_unscoreable_no_data(self):
        # bar 없는 종목(pinned spot) → no_data.
        _sig("NODATA", START, target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        sig = _one(p, "NODATA")["signals"][0]
        assert sig["status"] == "unscoreable"
        assert sig["unscoreable_reason"] == "no_data"


# ============================================================
# 0-5 실측 엣지 — 유지 신호 · 무목표가
# ============================================================
@pytest.mark.django_db
class TestScorecardEdges:
    def test_hold_signal_excluded_from_direction(self):
        # target==spot(유지, 방향 flat): scored이나 방향 적중 분모에서 제외(0-5 ①).
        _bars("HOLD", START, [100, 101, 102, 105, 106])
        _sig("HOLD", START, target=100, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        sym = _one(p, "HOLD")
        sig = sym["signals"][0]
        assert sig["direction"] == "flat"
        assert sig["status"] == "scored"
        assert sig["realized"]["verdict"] == "flat"
        assert sym["hit"] is None  # 방향 표본 0 → hit 봉투 null
        assert p["board"]["direction_hit"]["total"] == 0

    def test_missing_target_excluded_from_progress(self):
        # target None(무목표가): scored·수익률 계산되나 진행률·방향 제외(0-5 ②).
        _bars("NOTGT", START, [100, 101, 102, 110, 111])
        _sig("NOTGT", START, target=None, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        sym = _one(p, "NOTGT")
        sig = sym["signals"][0]
        assert sig["direction"] is None
        assert sig["status"] == "scored"
        assert sig["realized"]["return_pct"] == 10.0
        assert sig["realized"]["target_progress_pct"] is None
        assert sym["avg_target_progress"] is None
        assert p["board"]["avg_target_progress"] is None


# ============================================================
# 집계 — board · symbol
# ============================================================
@pytest.mark.django_db
class TestScorecardAggregation:
    def test_board_and_symbol_counts(self):
        _bars("HIT", START, [100, 101, 102, 120, 121])   # up hit
        _sig("HIT", START, target=110, spot=100)
        _bars("MISS", START, [100, 99, 95, 90, 88])      # up miss
        _sig("MISS", START, target=110, spot=100)
        _bars("WAIT", date(2026, 8, 18), [100, 101])     # pending
        _sig("WAIT", date(2026, 8, 18), target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        b = p["board"]
        assert b["sample_n"] == 2  # scored(HIT, MISS)
        assert b["direction_hit"] == {"hits": 1, "total": 2}
        assert b["significance_threshold"] == 60
        assert p["horizon"] == 3
        # symbol별 counts
        assert _one(p, "HIT")["counts"] == {"scored": 1, "pending": 0, "unscoreable": 0}
        assert _one(p, "WAIT")["counts"] == {"scored": 0, "pending": 1, "unscoreable": 0}

    def test_ic_null_reason_on_small_sample(self):
        # 주간 코호트 표본 부족 → cross_sectional_ic null + 사유.
        _bars("ICX", START, [100, 101, 102, 110, 111])
        _sig("ICX", START, target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        assert p["board"]["cross_sectional_ic"] is None
        assert p["board"]["cross_sectional_ic_reason"]

    def test_reproduction_header_present(self):
        _bars("REP", START, [100, 101, 102, 110])
        _sig("REP", START, target=110, spot=100)
        p = sc.build_scorecard(AS_OF, h=3)
        r = p["reproduction"]
        assert r["as_of"] == AS_OF.isoformat()
        assert r["scoring_version"] == sc.SCORING_VERSION
        assert "input_rows" in r and "splits_input_rows" in r


# ============================================================
# GATE 1a — command 산출 byte-IDENTICAL (기존 집계 무접촉)
# ============================================================
@pytest.mark.django_db
class TestScoreTier1Unchanged:
    def test_score_tier1_untouched_by_new_code(self):
        # 신규 build_scorecard가 score_tier1 산출을 오염시키지 않음(같은 순수 코어 공유).
        _bars("AAPL", START, [100, 101, 102, 115])
        _sig("AAPL", START, target=110, spot=100)
        before = sc.score_tier1(AS_OF)
        sc.build_scorecard(AS_OF, h=3)  # 부작용 없어야 함
        after = sc.score_tier1(AS_OF)
        assert before == after


# ============================================================
# 캐시 키 회전
# ============================================================
@pytest.mark.django_db
class TestCacheKey:
    def test_key_rotates_on_new_data(self):
        from apps.portfolio.api.scorecard import scorecard_cache_key

        _bars("KEY", START, [100, 101])
        _sig("KEY", START, target=110, spot=100)
        k1 = scorecard_cache_key(21)
        # 새 DailyPrice(더 늦은 날짜) → max date 이동 → 키 회전.
        DailyPrice.objects.create(
            stock=_stock("KEY"), date=date(2026, 8, 20),
            open_price=Decimal("103"), high_price=Decimal("103"),
            low_price=Decimal("103"), close_price=Decimal("103"), volume=0,
        )
        k2 = scorecard_cache_key(21)
        assert k1 != k2
        # 지평 변경도 키 회전.
        assert scorecard_cache_key(21) != scorecard_cache_key(63)


# ============================================================
# read API — 봉투 · 인증 · h 검증
# ============================================================
@pytest.mark.django_db
class TestScorecardAPI:
    @pytest.fixture
    def auth_client(self):
        u = User.objects.create_user(username="scb-user")
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_requires_auth(self):
        r = APIClient().get(URL)
        assert r.status_code in (401, 403)

    def test_envelope_and_computed_at(self, auth_client):
        _bars("ENV", START, [100, 101, 102, 115])
        _sig("ENV", START, target=110, spot=100)
        r = auth_client.get(URL + "?h=3")
        assert r.status_code == 200
        d = r.json()
        assert d["horizon"] == 3
        assert {"as_of", "horizon", "reproduction", "board", "symbols"} <= set(d)
        assert d["reproduction"]["computed_at"]  # 뷰 주입

    def test_default_horizon_21(self, auth_client):
        r = auth_client.get(URL)
        assert r.status_code == 200
        assert r.json()["horizon"] == 21

    def test_invalid_h_rejected(self, auth_client):
        assert auth_client.get(URL + "?h=abc").status_code == 400
        assert auth_client.get(URL + "?h=0").status_code == 400
        assert auth_client.get(URL + "?h=9999").status_code == 400
