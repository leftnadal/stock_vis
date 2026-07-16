"""TIMING-P1 의미 피벗 (BE) 검증 — 가격 구간축·S계열·verdict 만료 (D-TIMING-DECISIONS-5).

행위보존은 기존 135 테스트가 담당. 여기서는 additive 신규 로직만 검증한다.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.monitor.models import Claim, Monitor
from apps.monitor.services import closure
from apps.monitor.services.price_zone import (
    APPROACH_BUFFER,
    is_immediate_zone_alert,
    resolve_zone,
)
from apps.monitor.services.technical import (
    bounded_linear_score,
    compute_technical_series,
    ingest_technical_for_indicator,
    score_indicator_dispatch,
)

User = get_user_model()


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def owner(db):
    return User.objects.create_user(username="timing_user", password="pw12345")


@pytest.fixture
def stock_aapl(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="AAPL", stock_name="Apple Inc.")


@pytest.fixture
def aapl_monitor(owner, stock_aapl):
    return Monitor.objects.create(
        user=owner, scope="stock", target_ref="AAPL", name="애플", current_state="active"
    )


@pytest.fixture
def make_claim(aapl_monitor):
    def _make(**kwargs):
        defaults = dict(monitor=aapl_monitor, assertion="3개월 내 반등")
        defaults.update(kwargs)
        return Claim.objects.create(**defaults)

    return _make


@pytest.fixture
def daily_prices(stock_aapl):
    """AAPL DailyPrice 시계열 생성. closes/highs 지정 가능."""
    from packages.shared.stocks.models import DailyPrice

    def _make(n, close_fn=lambda i: 100.0 + i, high_gap=1.0, volume_fn=lambda i: 1_000_000):
        for i in range(n):
            d = date.today() - timedelta(days=(n - 1 - i))
            c = close_fn(i)
            DailyPrice.objects.create(
                stock=stock_aapl, date=d,
                open_price=Decimal(str(c)), high_price=Decimal(str(c + high_gap)),
                low_price=Decimal(str(c - high_gap)), close_price=Decimal(str(c)),
                volume=int(volume_fn(i)),
            )

    return _make


# ── §4 resolve_zone 경계 5구간 + null ────────────────────────────────────────

@pytest.mark.django_db
class TestResolveZone:
    # entry=100, target=120, stop=90, 접근 상한 = 100×1.03 = 103
    E, T, S = Decimal("100"), Decimal("120"), Decimal("90")

    def test_exited(self):
        assert resolve_zone(90.0, self.E, self.T, self.S) == Claim.PriceZone.EXITED
        assert resolve_zone(85.0, self.E, self.T, self.S) == Claim.PriceZone.EXITED

    def test_entry(self):
        assert resolve_zone(95.0, self.E, self.T, self.S) == Claim.PriceZone.ENTRY
        assert resolve_zone(100.0, self.E, self.T, self.S) == Claim.PriceZone.ENTRY

    def test_approach(self):
        assert resolve_zone(102.0, self.E, self.T, self.S) == Claim.PriceZone.APPROACH
        assert resolve_zone(103.0, self.E, self.T, self.S) == Claim.PriceZone.APPROACH

    def test_waiting(self):
        assert resolve_zone(110.0, self.E, self.T, self.S) == Claim.PriceZone.WAITING
        assert resolve_zone(103.01, self.E, self.T, self.S) == Claim.PriceZone.WAITING

    def test_overheated(self):
        assert resolve_zone(120.0, self.E, self.T, self.S) == Claim.PriceZone.OVERHEATED
        assert resolve_zone(130.0, self.E, self.T, self.S) == Claim.PriceZone.OVERHEATED

    def test_null_any_missing(self):
        assert resolve_zone(100.0, None, self.T, self.S) is None
        assert resolve_zone(None, self.E, self.T, self.S) is None
        assert resolve_zone(100.0, self.E, None, self.S) is None
        assert resolve_zone(100.0, self.E, self.T, None) is None

    def test_approach_buffer_constant(self):
        assert APPROACH_BUFFER == Decimal("0.03")


def test_immediate_zone_alert_routing():
    assert is_immediate_zone_alert(Claim.PriceZone.ENTRY) is True
    assert is_immediate_zone_alert(Claim.PriceZone.EXITED) is True
    assert is_immediate_zone_alert(Claim.PriceZone.APPROACH) is False
    assert is_immediate_zone_alert(Claim.PriceZone.WAITING) is False
    assert is_immediate_zone_alert(Claim.PriceZone.OVERHEATED) is False


# ── §3 bounded 스코어링 매핑 ──────────────────────────────────────────────────

def test_bounded_linear_score_proximity():
    # high_52w_proximity ∈ [0,1] → [-1,1]
    assert bounded_linear_score(1.0, "high_52w_proximity", "positive") == 1.0
    assert bounded_linear_score(0.0, "high_52w_proximity", "positive") == -1.0
    assert bounded_linear_score(0.5, "high_52w_proximity", "positive") == 0.0


def test_bounded_linear_score_rsi_and_direction():
    # rsi14 ∈ [0,100]
    assert bounded_linear_score(100.0, "rsi14", "positive") == 1.0
    assert bounded_linear_score(50.0, "rsi14", "positive") == 0.0
    # negative direction 반전
    assert bounded_linear_score(100.0, "rsi14", "negative") == -1.0


@pytest.mark.django_db
class TestScoreDispatch:
    def _ind(self, monitor, source_key, direction="positive", **kw):
        return monitor.indicators.create(
            name=source_key, indicator_type="technical",
            support_direction=direction, source_key=source_key, **kw
        )

    def test_bounded_routes_to_linear(self, aapl_monitor):
        from apps.monitor.models import IndicatorReading

        ind = self._ind(aapl_monitor, "high_52w_proximity")
        IndicatorReading.objects.create(
            indicator=ind, value=1.0, asof=timezone.now(), validation_status="ok"
        )
        res = score_indicator_dispatch(ind)
        assert res.get("scoring_mode") == "bounded"
        assert res["score"] == 1.0  # 신고가 근접 → 최대

    def test_zscore_falls_through(self, aapl_monitor):
        # source_key 없는 custom 지표 → 기존 robust-Z 경로(dispatch가 통과)
        ind = aapl_monitor.indicators.create(
            name="custom", indicator_type="custom", support_direction="positive"
        )
        res = score_indicator_dispatch(ind)
        assert "scoring_mode" not in res  # bounded 아님
        assert res["is_sufficient"] is False  # 판독 없음


# ── §3 compute_technical_series (요구 행수 충족/미달) ─────────────────────────

def _series_inputs(n, close_fn=lambda i: 100.0 + i):
    dates = [date.today() - timedelta(days=(n - 1 - i)) for i in range(n)]
    closes = [close_fn(i) for i in range(n)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    vols = [1_000_000.0 for _ in range(n)]
    opens = list(closes)
    return dates, opens, highs, lows, closes, vols


def test_compute_sma200_gap_sufficient():
    d, o, h, low, c, v = _series_inputs(260)
    out = compute_technical_series("sma200_gap", d, o, h, low, c, v)
    assert len(out) == 61  # 260 - 199
    # 상승 추세 → 종가가 200SMA 위 → 양수 괴리
    assert out[-1][1] > 0


def test_compute_sma200_gap_insufficient():
    d, o, h, low, c, v = _series_inputs(50)  # < 200
    out = compute_technical_series("sma200_gap", d, o, h, low, c, v)
    assert out == []


def test_compute_momentum_12_1():
    d, o, h, low, c, v = _series_inputs(300)
    out = compute_technical_series("momentum_12_1", d, o, h, low, c, v)
    assert len(out) == 48  # 300 - 252
    assert out[-1][1] > 0  # 상승 → 양의 모멘텀


def test_compute_high_52w_proximity_bounded():
    d, o, h, low, c, v = _series_inputs(260)
    out = compute_technical_series("high_52w_proximity", d, o, h, low, c, v)
    for _, val in out:
        assert 0.0 < val <= 1.0  # 유계


def test_compute_volume_ratio():
    d, o, h, low, c, v = _series_inputs(30)
    v = [1_000_000.0] * 29 + [2_000_000.0]
    out = compute_technical_series("volume_ratio", d, o, h, low, c, v)
    assert out[-1][1] > 1.0  # 마지막 거래량 급증


def test_compute_rsi_and_macd_produce_values():
    d, o, h, low, c, v = _series_inputs(60)
    rsi = compute_technical_series("rsi14", d, o, h, low, c, v)
    macd = compute_technical_series("macd_histogram", d, o, h, low, c, v)
    assert rsi and all(0 <= val <= 100 for _, val in rsi)
    assert macd  # 값 생성


# ── §3 신규 ingest 경로 ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIngestTechnical:
    def test_sufficient_history_stores_readings(self, aapl_monitor, daily_prices):
        daily_prices(260)
        ind = aapl_monitor.indicators.create(
            name="200일선 괴리율", indicator_type="technical",
            source_key="sma200_gap", support_direction="positive",
        )
        res = ingest_technical_for_indicator(ind)
        assert res["status"] == "ok"
        assert res["ingested"] == 61
        assert ind.readings.count() == 61

    def test_insufficient_history_no_readings(self, aapl_monitor, daily_prices):
        daily_prices(50)  # 200SMA 불가
        ind = aapl_monitor.indicators.create(
            name="200일선 괴리율", indicator_type="technical",
            source_key="sma200_gap", support_direction="positive",
        )
        res = ingest_technical_for_indicator(ind)
        assert res["status"] == "insufficient_history"
        assert ind.readings.count() == 0

    def test_non_technical_indicator_skipped(self, aapl_monitor, daily_prices):
        daily_prices(260)
        ind = aapl_monitor.indicators.create(
            name="EOD 종합", indicator_type="market_data",
            source_key="eod_composite", support_direction="positive",
        )
        res = ingest_technical_for_indicator(ind)
        assert res["status"] == "skip_not_technical"


# ── §5 propose_verdict 만료 분기 + is_expired_scenario ───────────────────────

def test_propose_verdict_expiry_branch():
    assert closure.propose_verdict(0.5, expired=True) == Claim.ProposedVerdict.EXPIRED
    assert closure.propose_verdict(-0.9, expired=True) == Claim.ProposedVerdict.EXPIRED
    # expired=False → 기존 밴드 불변
    assert closure.propose_verdict(0.5) == Claim.ProposedVerdict.VALIDATED
    assert closure.propose_verdict(-0.5) == Claim.ProposedVerdict.INVALIDATED
    assert closure.propose_verdict(0.0) == Claim.ProposedVerdict.PARTIAL


@pytest.mark.django_db
class TestExpiredScenario:
    def test_expired_when_deadline_passed_and_not_reached(self, make_claim):
        yesterday = date.today() - timedelta(days=1)
        claim = make_claim(entry_price=Decimal("100"), deadline=yesterday)
        assert closure.is_expired_scenario(claim, date.today()) is True

    def test_not_expired_if_entry_reached(self, make_claim):
        yesterday = date.today() - timedelta(days=1)
        claim = make_claim(
            entry_price=Decimal("100"), deadline=yesterday,
            entry_reached_at=timezone.now(),
        )
        assert closure.is_expired_scenario(claim, date.today()) is False

    def test_not_expired_without_price(self, make_claim):
        # 구 가설(가격 없음) → 만료 대상 아님
        yesterday = date.today() - timedelta(days=1)
        claim = make_claim(deadline=yesterday)
        assert closure.is_expired_scenario(claim, date.today()) is False

    def test_not_expired_before_deadline(self, make_claim):
        tomorrow = date.today() + timedelta(days=1)
        claim = make_claim(entry_price=Decimal("100"), deadline=tomorrow)
        assert closure.is_expired_scenario(claim, date.today()) is False


# ── §4 scenario 처리: zone 전이 · entry_reached_at 1회 · 만료 제안 가드 ───────

@pytest.mark.django_db
class TestProcessScenario:
    def _claim(self, make_claim):
        return make_claim(
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90")
        )

    def test_zone_transition_event_and_persist(self, make_claim):
        from apps.monitor.services.scenario import process_claim_scenario

        claim = self._claim(make_claim)
        events = process_claim_scenario(claim, close=95.0, as_of=date.today())
        claim.refresh_from_db()
        assert claim.last_price_zone == Claim.PriceZone.ENTRY
        assert len(events) == 1 and events[0]["to_zone"] == Claim.PriceZone.ENTRY
        assert events[0]["immediate"] is True

    def test_entry_reached_at_recorded_once(self, make_claim):
        from apps.monitor.services.scenario import process_claim_scenario

        claim = self._claim(make_claim)
        process_claim_scenario(claim, close=95.0, as_of=date.today())
        claim.refresh_from_db()
        first = claim.entry_reached_at
        assert first is not None
        # 재진입해도 시각 불변(1회성)
        process_claim_scenario(claim, close=98.0, as_of=date.today())
        claim.refresh_from_db()
        assert claim.entry_reached_at == first

    def test_no_event_when_zone_unchanged(self, make_claim):
        from apps.monitor.services.scenario import process_claim_scenario

        claim = self._claim(make_claim)
        process_claim_scenario(claim, close=95.0, as_of=date.today())
        events = process_claim_scenario(claim, close=96.0, as_of=date.today())  # 여전히 ENTRY
        assert events == []

    def test_expiry_suggestion_once_with_guard(self, make_claim):
        from apps.monitor.services.scenario import process_claim_scenario

        yesterday = date.today() - timedelta(days=1)
        claim = make_claim(
            entry_price=Decimal("100"), target_price=Decimal("120"),
            stop_price=Decimal("90"), deadline=yesterday,
        )
        # 진입 미도달(close가 stop 아래 → EXITED, entry_reached_at 안 붙음) 상태로 만료
        events = process_claim_scenario(claim, close=80.0, as_of=date.today())
        claim.refresh_from_db()
        assert claim.proposed_verdict == Claim.ProposedVerdict.EXPIRED
        assert any(e["type"] == "expiry" for e in events)
        # 재실행 → 가드로 만료 이벤트 재발화 없음
        events2 = process_claim_scenario(claim, close=80.0, as_of=date.today())
        assert not any(e["type"] == "expiry" for e in events2)


# ── 마이그레이션 null 무해성 + close payload 손익 ────────────────────────────

@pytest.mark.django_db
class TestNullHarmlessAndPayload:
    def test_old_claim_null_price_fields(self, make_claim):
        # 가격 없는 구 가설 — 전부 null, zone None
        claim = make_claim()
        assert claim.entry_price is None
        assert claim.last_price_zone is None
        assert resolve_zone(100.0, claim.entry_price, claim.target_price, claim.stop_price) is None

    def test_close_payload_includes_scenario_pnl(self, make_claim, stock_aapl):
        from packages.shared.stocks.models import EODSignal

        # 마감일 종가 = EODSignal 우선. entry=100, 종가=110 → +10%
        EODSignal.objects.create(
            stock=stock_aapl, date=date.today(), close_price=Decimal("110"),
            composite_score=0.0, change_percent=0.0, dollar_volume=0,
        )
        claim = make_claim(
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90")
        )
        closed = closure.close_claim(
            claim, final_verdict=Claim.Outcome.VALIDATED, user=claim.monitor.user
        )
        payload = closed.closure_snapshot.payload
        assert "scenario" in payload
        assert payload["scenario"]["pnl_pct"] == pytest.approx(10.0, abs=0.01)


# ── 다이제스트 zone/만료 섹션 분류 ───────────────────────────────────────────

@pytest.mark.django_db
def test_digest_categorizes_scenario_events():
    from apps.monitor.services.alerts import build_digest

    events = [
        {"type": "zone", "monitor_name": "A", "target_ref": "AAA", "from_zone": None,
         "to_zone": Claim.PriceZone.ENTRY, "immediate": True, "close": 95.0},
        {"type": "zone", "monitor_name": "B", "target_ref": "BBB", "from_zone": Claim.PriceZone.WAITING,
         "to_zone": Claim.PriceZone.APPROACH, "immediate": False, "close": 102.0},
        {"type": "expiry", "monitor_name": "C", "target_ref": "CCC", "deadline": "2026-07-15"},
    ]
    digest = build_digest(date.today(), scenario_events=events)
    assert len(digest["zone_immediate"]) == 1
    assert len(digest["zone_digest"]) == 1
    assert len(digest["expiries"]) == 1
    assert digest["has_content"] is True
    assert digest["zone_immediate"][0]["to_label"] == "진입 구간"


# ── §6 시리얼라이저 zone_display (BE 완결 표시 메타) ─────────────────────────

@pytest.mark.django_db
class TestClaimSerializerZone:
    def test_zone_display_with_prices(self, make_claim, stock_aapl):
        from packages.shared.stocks.models import EODSignal

        from apps.monitor.api.serializers import ClaimSerializer

        EODSignal.objects.create(
            stock=stock_aapl, date=date.today(), close_price=Decimal("95"),
            composite_score=0.0, change_percent=0.0, dollar_volume=0,
        )
        claim = make_claim(
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90")
        )
        data = ClaimSerializer(claim).data
        assert data["entry_price"] == "100.0000"
        zd = data["zone_display"]
        assert zd["zone"] == Claim.PriceZone.ENTRY  # 종가 95 ∈ (90,100]
        assert zd["label"] == "진입 구간"
        assert zd["boundaries"]["approach_ceiling"] == pytest.approx(103.0)

    def test_zone_display_null_without_prices(self, make_claim):
        from apps.monitor.api.serializers import ClaimSerializer

        claim = make_claim()  # 가격 없음
        data = ClaimSerializer(claim).data
        assert data["zone_display"] is None
        assert data["entry_price"] is None
