"""EODSIG-FRESH-GATE (C안) 테스트 — EOD 신호 beat 신선도 게이트.

갭(OBS-BRIEFING-0827 O1): 비SP500 감시등록 종목의 당일 가격이 EOD 신호 생성(18:30 ET)
보다 늦게(monitor refresh 18:45 ET) 도착 → 매일 EODSignal 누락. 게이트는 신호 계산 직전
ensure_price_freshness(apps.monitor)를 동적 lookup으로 재사용해 부재 심볼만 선보충한다.

커버:
  1. 단위 — 부재 심볼 → fetch 호출·행 생성 / fetch 실패·예외 → 해당 심볼만 격리·타 심볼 무영향 / 기존재 → fetch 미호출(멱등).
  2. 통합(beat 경로) — REAL ensure_price_freshness 시그니처를 태스크 스테이지 관통으로 검증
     (시그니처 불일치는 단위 mock으로 안 잡힌다는 교훈). SP500 1종 + 비SP500 1종 혼합.
픽스처는 고정 기준일 앵커만 사용(now()/today() 금지 — time-bomb 규칙).
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.monitor.models.monitor import Monitor
from packages.shared.stocks.models import (
    DailyPrice,
    EODSignal,
    SP500Constituent,
    Stock,
)
from packages.shared.stocks.services.eod_pipeline import EODPipeline
from packages.shared.stocks.services.stock_sync_service import StockSyncService

pytestmark = [pytest.mark.django_db, pytest.mark.unit]

ANCHOR = date(2026, 8, 27)  # 고정 기준일 — now() 금지
SYNC_PATH = (
    "packages.shared.stocks.services.stock_sync_service.StockSyncService.sync_prices"
)
User = get_user_model()


def _seed_prices(symbol, through, n=60):
    """symbol에 [through-n+1 .. through] 캘린더일 DailyPrice 시딩(테스트용, 주말 무관)."""
    rows = [
        DailyPrice(
            stock_id=symbol,
            date=through - timedelta(days=i),
            open_price=Decimal("100"),
            high_price=Decimal("105"),
            low_price=Decimal("99"),
            close_price=Decimal("102"),
            volume=2_000_000,
        )
        for i in range(n)
    ]
    DailyPrice.objects.bulk_create(rows)


def _seed_sp500(symbol="AAA", fresh_through=ANCHOR):
    Stock.objects.create(symbol=symbol, stock_name=f"{symbol} Corp")
    SP500Constituent.objects.create(
        symbol=symbol, company_name=f"{symbol} Corp", sector="Technology", is_active=True
    )
    _seed_prices(symbol, fresh_through)
    return symbol


def _seed_watch(symbol="BBB", price_through=ANCHOR - timedelta(days=1)):
    """비SP500 감시등록 종목. 기본 = ANCHOR 하루 전까지만 가격(=당일 부재/stale)."""
    user = User.objects.create_user(username=f"u_{symbol}", password="pw12345")
    Stock.objects.create(symbol=symbol, stock_name=f"{symbol} Corp")
    Monitor.objects.create(user=user, scope="stock", target_ref=symbol, name=symbol)
    _seed_prices(symbol, price_through)
    return symbol


def _mock_res(success=True, error=None):
    r = MagicMock()
    r.success = success
    r.error = error
    return r


def _fetch_creating_row(symbol, days=90, force=True):
    """성공 fetch 시뮬레이션 — 당일 DailyPrice 행을 만들고 성공 반환."""
    DailyPrice.objects.get_or_create(
        stock_id=symbol,
        date=ANCHOR,
        defaults=dict(
            open_price=Decimal("100"),
            high_price=Decimal("105"),
            low_price=Decimal("99"),
            close_price=Decimal("102"),
            volume=2_000_000,
        ),
    )
    return _mock_res(success=True)


# ── 1. 단위: 부재 심볼 → fetch 호출 + 행 생성, fresh 심볼은 미호출 ──────────────
def test_absent_symbol_fetched_and_row_created():
    _seed_sp500("AAA")  # fresh (ANCHOR 있음)
    _seed_watch("BBB")  # stale (ANCHOR 부재)
    with patch(SYNC_PATH, side_effect=_fetch_creating_row) as m:
        summary = EODPipeline()._run_freshness_gate(ANCHOR)
    called = [c.args[0] for c in m.call_args_list]
    assert "BBB" in called  # 부재 → fetch
    assert "AAA" not in called  # fresh → 미호출(멱등)
    assert "BBB" in summary["synced"]
    assert DailyPrice.objects.filter(stock_id="BBB", date=ANCHOR).exists()


# ── 2a. 단위: fetch 실패(success=False) → 해당 심볼만 격리, 예외 비전파 ─────────
def test_fetch_failure_isolated_no_raise():
    _seed_sp500("AAA")
    _seed_watch("BBB")
    with patch(SYNC_PATH, return_value=_mock_res(success=False, error="boom")):
        summary = EODPipeline()._run_freshness_gate(ANCHOR)  # 예외 없어야 함
    assert "BBB" in summary["failed"]
    assert "BBB" not in summary["synced"]
    # AAA는 fresh라 애초 시도 안 함 — 실패 목록에 없음(타 심볼 무영향)
    assert "AAA" not in summary["failed"]


# ── 2b. 단위: sync_prices가 예외를 던져도 게이트가 삼킴(태스크 보호 #65) ────────
def test_fetch_exception_swallowed():
    _seed_sp500("AAA")
    _seed_watch("BBB")
    with patch(SYNC_PATH, side_effect=RuntimeError("network down")):
        summary = EODPipeline()._run_freshness_gate(ANCHOR)  # raise 되면 실패
    assert "BBB" in summary["failed"]


# ── 3. 단위: 당일 가격 기존재 → fetch 미호출(추가 API 0) ────────────────────────
def test_no_fetch_when_all_fresh():
    _seed_sp500("AAA", fresh_through=ANCHOR)
    _seed_watch("BBB", price_through=ANCHOR)  # BBB도 ANCHOR 보유 → fresh
    with patch(SYNC_PATH) as m:
        EODPipeline()._run_freshness_gate(ANCHOR)
    m.assert_not_called()


# ── 4. 통합(beat 경로): 진입 스테이지→EODSignal 행. REAL ensure_price_freshness 관통 ──
def test_beat_path_nonsp500_gets_eodsignal():
    """혼합 유니버스(SP500 AAA + 비SP500 BBB). BBB는 당일 가격 부재로 시작 →
    게이트(REAL ensure_price_freshness, 시그니처 관통)가 mock fetch로 보충 →
    _stage_ingest 로드에 BBB 당일 행 포함 → 신호 생성·upsert로 EODSignal 행 생성.
    (뉴스 enrich·JSON bake 스테이지는 게이트 무관 — 범위 밖.)
    """
    from packages.shared.stocks.services.eod_signal_calculator import EODSignalCalculator
    from packages.shared.stocks.services.eod_signal_tagger import EODSignalTagger

    _seed_sp500("AAA")
    _seed_watch("BBB")  # 당일 부재
    assert not DailyPrice.objects.filter(stock_id="BBB", date=ANCHOR).exists()

    with patch(SYNC_PATH, side_effect=_fetch_creating_row):
        pipe = EODPipeline()
        raw_df, _quality = pipe._stage_ingest(ANCHOR)  # REAL 게이트 호출 포함
        today = set(raw_df[raw_df["date"] == ANCHOR]["symbol"])
        assert "AAA" in today and "BBB" in today  # 게이트 덕에 BBB 당일 로드됨
        # 관통: 신호 생성 → 태그 → DB upsert
        signals_df = EODSignalCalculator().calculate_batch(ANCHOR)
        tagged = EODSignalTagger().tag_signals(signals_df)
        pipe._stage_db_upsert(tagged, ANCHOR)

    assert EODSignal.objects.filter(stock__symbol="BBB", date=ANCHOR).exists()
    assert EODSignal.objects.filter(stock__symbol="AAA", date=ANCHOR).exists()
