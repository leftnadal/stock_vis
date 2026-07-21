"""HOLD-P1 보유 모드 (BE) 검증 — 앵커 치환·zone_display 재구간화·알림 분기·suggest·validate.

additive-only. resolve_zone 무접촉(앵커만 모드별 선택), coherence 순수함수 재사용.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.monitor.models import Claim, Monitor
from apps.monitor.services import closure, coherence
from apps.monitor.services.price_zone import (
    NEAR_TARGET_BUFFER,
    is_immediate_zone_alert,
    resolve_zone,
    zone_anchor,
)
from apps.monitor.services.scenario import process_claim_scenario

User = get_user_model()


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def owner(db):
    return User.objects.create_user(username="hold_user", password="pw12345")


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
        defaults = dict(monitor=aapl_monitor, assertion="보유 관리")
        defaults.update(kwargs)
        return Claim.objects.create(**defaults)

    return _make


@pytest.fixture
def daily_prices(stock_aapl):
    from packages.shared.stocks.models import DailyPrice

    def _make(n, close_fn=lambda i: 100.0 + i, high_gap=1.0):
        for i in range(n):
            d = date.today() - timedelta(days=(n - 1 - i))
            c = close_fn(i)
            DailyPrice.objects.create(
                stock=stock_aapl, date=d,
                open_price=Decimal(str(c)), high_price=Decimal(str(c + high_gap)),
                low_price=Decimal(str(c - high_gap)), close_price=Decimal(str(c)),
                volume=1_000_000,
            )

    return _make


# ── 앵커 치환 (hold=매입가, 그 외=진입가) ─────────────────────────────────────

@pytest.mark.django_db
class TestZoneAnchor:
    def test_hold_uses_purchase(self, make_claim):
        c = make_claim(
            scenario_type=Claim.ScenarioType.HOLD,
            purchase_price=Decimal("100"), entry_price=None,
            target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        assert zone_anchor(c) == Decimal("100")

    def test_new_entry_uses_entry(self, make_claim):
        c = make_claim(
            scenario_type=Claim.ScenarioType.NEW_ENTRY,
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        assert zone_anchor(c) == Decimal("100")

    def test_stored_zone_uses_purchase_anchor(self, make_claim):
        """hold 저장 zone은 매입가 앵커로 5버킷 산출(수학 동일)."""
        c = make_claim(
            scenario_type=Claim.ScenarioType.HOLD,
            purchase_price=Decimal("100"), entry_price=None,
            target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        # close=95 → stop<close≤purchase → ENTRY 버킷(앵커=매입가)
        assert resolve_zone(95.0, zone_anchor(c), c.target_price, c.stop_price) == Claim.PriceZone.ENTRY


# ── is_immediate_zone_alert 모드 인지 ─────────────────────────────────────────

def test_immediate_alert_mode_aware():
    # new_entry(기본): ENTRY·EXITED 즉시
    assert is_immediate_zone_alert(Claim.PriceZone.ENTRY) is True
    assert is_immediate_zone_alert(Claim.PriceZone.OVERHEATED) is False
    # hold: OVERHEATED(목표 도달)·EXITED 즉시, ENTRY 억제
    assert is_immediate_zone_alert(Claim.PriceZone.OVERHEATED, mode=Claim.ScenarioType.HOLD) is True
    assert is_immediate_zone_alert(Claim.PriceZone.EXITED, mode=Claim.ScenarioType.HOLD) is True
    assert is_immediate_zone_alert(Claim.PriceZone.ENTRY, mode=Claim.ScenarioType.HOLD) is False


# ── 알림 분기 3 (process_claim_scenario) ──────────────────────────────────────

@pytest.mark.django_db
class TestHoldScenarioProcessing:
    def _hold(self, make_claim, **kw):
        base = dict(
            scenario_type=Claim.ScenarioType.HOLD,
            purchase_price=Decimal("100"), entry_price=None,
            target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        base.update(kw)
        return make_claim(**base)

    def test_entry_zone_no_entry_reached_and_digest(self, make_claim):
        """hold: 보유 구간(ENTRY 버킷) 진입 = entry_reached_at 미기록 + 즉시 아님(다이제스트)."""
        c = self._hold(make_claim)
        events = process_claim_scenario(c, close=95.0, as_of=date.today())
        c.refresh_from_db()
        assert c.entry_reached_at is None  # 진입 개념 없음
        assert len(events) == 1
        assert events[0]["to_zone"] == Claim.PriceZone.ENTRY
        assert events[0]["immediate"] is False  # 다이제스트

    def test_target_reached_immediate(self, make_claim):
        c = self._hold(make_claim)
        events = process_claim_scenario(c, close=125.0, as_of=date.today())
        assert events[0]["to_zone"] == Claim.PriceZone.OVERHEATED
        assert events[0]["immediate"] is True  # 목표 도달 즉시

    def test_exit_immediate(self, make_claim):
        c = self._hold(make_claim)
        events = process_claim_scenario(c, close=85.0, as_of=date.today())
        assert events[0]["to_zone"] == Claim.PriceZone.EXITED
        assert events[0]["immediate"] is True  # 손절 이탈 즉시

    def test_hold_expiry_no_expired_verdict(self, make_claim):
        """hold 만료 = 알림 1회 + proposed_verdict은 EXPIRED 아님(점수 밴드 유지)."""
        c = self._hold(make_claim, deadline=date.today() - timedelta(days=1))
        events = process_claim_scenario(c, close=110.0, as_of=date.today())
        c.refresh_from_db()
        expiry = [e for e in events if e["type"] == "expiry"]
        assert len(expiry) == 1
        assert c.proposed_verdict is not None
        assert c.proposed_verdict != Claim.ProposedVerdict.EXPIRED  # 점수 밴드 제안
        # 2회차 = 가드로 무발화
        events2 = process_claim_scenario(c, close=110.0, as_of=date.today())
        assert [e for e in events2 if e["type"] == "expiry"] == []

    def test_new_entry_expiry_sets_expired(self, make_claim):
        """대조: 신규 매수 만료(진입 미도달 = entry_reached_at None)는 EXPIRED 제안.

        close=110(관망 — 진입 구간 밖)이라 entry_reached_at 미기록 → 만료 조건 성립.
        """
        c = make_claim(
            scenario_type=Claim.ScenarioType.NEW_ENTRY,
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90"),
            deadline=date.today() - timedelta(days=1),
        )
        events = process_claim_scenario(c, close=110.0, as_of=date.today())
        c.refresh_from_db()
        assert c.entry_reached_at is None
        assert c.proposed_verdict == Claim.ProposedVerdict.EXPIRED
        assert any(e["type"] == "expiry" for e in events)


# ── is_expired_scenario / is_hold_deadline_passed ─────────────────────────────

@pytest.mark.django_db
def test_expired_scenario_excludes_hold(make_claim):
    hold = make_claim(
        scenario_type=Claim.ScenarioType.HOLD, purchase_price=Decimal("100"),
        target_price=Decimal("120"), stop_price=Decimal("90"),
        deadline=date.today() - timedelta(days=1),
    )
    assert closure.is_expired_scenario(hold, date.today()) is False
    assert closure.is_hold_deadline_passed(hold, date.today()) is True


# ── zone_display hold 재구간화 (익절 접근 경계 포함) ──────────────────────────

@pytest.mark.django_db
class TestHoldZoneDisplay:
    def _display(self, make_claim, close):
        from apps.monitor.api.serializers import build_zone_display

        c = make_claim(
            scenario_type=Claim.ScenarioType.HOLD, purchase_price=Decimal("100"),
            entry_price=None, target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        return build_zone_display(c, zone_anchor(c), close)

    def test_hold_labels(self, make_claim):
        assert self._display(make_claim, 85.0)["label"] == "이탈"
        assert self._display(make_claim, 105.0)["label"] == "보유"
        assert self._display(make_claim, 125.0)["label"] == "목표 도달"

    def test_near_target_boundary(self, make_claim):
        # 익절 접근 임계 = round(target×(1-buffer), 4) = 116.4 (경계 포함)
        near = round(120.0 * (1.0 - float(NEAR_TARGET_BUFFER)), 4)  # 116.4
        assert self._display(make_claim, near)["label"] == "익절 접근"
        assert self._display(make_claim, near - 0.01)["label"] == "보유"

    def test_hold_meta_complete(self, make_claim):
        d = self._display(make_claim, 110.0)
        assert d["mode"] == "hold"
        assert d["mode_label"] == "보유 관리"
        assert d["pnl_pct"] == pytest.approx(10.0)  # (110-100)/100
        assert d["anchor_fraction"] is not None  # 매입가 마커
        # ticks에 '매입가' 라벨(하드코딩 제거 소스), rows에 '익절 접근'
        assert any(t["label"] == "매입가" for t in d["ticks"])
        assert any(r["label"] == "익절 접근" for r in d["rows"])
        assert len(d["bands"]) == 4

    def test_new_entry_display_unchanged(self, make_claim):
        from apps.monitor.api.serializers import build_zone_display

        c = make_claim(
            scenario_type=Claim.ScenarioType.NEW_ENTRY,
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        d = build_zone_display(c, zone_anchor(c), 95.0)
        assert d["mode_label"] == "신규 매수"
        assert d["pnl_pct"] is None
        assert d["anchor_fraction"] is None
        assert len(d["bands"]) == 5
        assert any(t["label"] == "진입" for t in d["ticks"])
        assert d["boundaries"]["approach_ceiling"] == pytest.approx(103.0)


# ── suggest hold (수익/손실 손절 분기 + 본전 회복 N주 검산) ────────────────────

@pytest.mark.django_db
class TestSuggestHold:
    def test_profit_stop_is_breakeven(self, daily_prices):
        from apps.monitor.services.scenario_suggest import suggest_hold_scenario

        daily_prices(70, close_fn=lambda i: 100.0 + i)  # 최신 close ≈ 169
        r = suggest_hold_scenario("AAPL", purchase_price="120")  # 수익 중(close>purchase)
        assert r["available"] and r["in_profit"] is True
        assert r["stop_suggest"] == pytest.approx(120.0)  # 본전 승격
        assert r["breakeven_weeks"] is None  # 수익 중이면 없음
        assert "entry_suggest" not in r  # 매입가·진입가는 절대 제안 안 함

    def test_loss_stop_atr_and_breakeven(self, daily_prices):
        from apps.monitor.services.scenario_suggest import suggest_hold_scenario

        daily_prices(70, close_fn=lambda i: 100.0 + i)  # 최신 close ≈ 169 (sigma 산출 가능)
        r = suggest_hold_scenario("AAPL", purchase_price="200")  # 손실 중(close<purchase)
        assert r["available"] and r["in_profit"] is False
        assert r["stop_suggest"] < r["close"]  # ATR 손절은 현재가 아래
        # 본전 회복 N주 = coherence.horizon_for_target(close, purchase, σ)로 검산(단일 출처 재사용 증거)
        sigma = coherence.daily_sigma("AAPL")
        expected_days = coherence.horizon_for_target(r["close"], 200.0, sigma)
        assert expected_days is not None
        assert r["breakeven_weeks"] == round(expected_days / 7)
        assert "entry_suggest" not in r  # 매입가 제안 안 함


# ── validate 필수 세트 (serializer) ──────────────────────────────────────────

@pytest.mark.django_db
class TestHoldValidate:
    def _ser(self, monitor, **data):
        from apps.monitor.api.serializers import ClaimSerializer

        base = {"monitor": str(monitor.id), "assertion": "보유", "scenario_type": "hold"}
        base.update(data)
        return ClaimSerializer(data=base)

    def test_hold_missing_required(self, aapl_monitor):
        s = self._ser(aapl_monitor, purchase_price="100")  # 나머지 결측
        assert not s.is_valid()
        for f in ("purchase_date", "target_price", "stop_price", "deadline"):
            assert f in s.errors

    def test_hold_valid(self, aapl_monitor):
        s = self._ser(
            aapl_monitor,
            purchase_price="100", purchase_date=str(date.today()),
            target_price="120", stop_price="90",
            deadline=str(date.today() + timedelta(days=30)),
        )
        assert s.is_valid(), s.errors

    def test_hold_stop_above_purchase_allowed(self, aapl_monitor):
        """본전 승격 — 손절이 매입가 위(stop>purchase)여도 stop<target이면 통과."""
        s = self._ser(
            aapl_monitor,
            purchase_price="100", purchase_date=str(date.today()),
            target_price="120", stop_price="110",  # stop>purchase
            deadline=str(date.today() + timedelta(days=30)),
        )
        assert s.is_valid(), s.errors

    def test_hold_stop_ge_target_rejected(self, aapl_monitor):
        s = self._ser(
            aapl_monitor,
            purchase_price="100", purchase_date=str(date.today()),
            target_price="120", stop_price="125",  # stop>target
            deadline=str(date.today() + timedelta(days=30)),
        )
        assert not s.is_valid()
        assert "stop_price" in s.errors


# ── 마이그레이션 무해: 기존 default = new_entry ───────────────────────────────

@pytest.mark.django_db
def test_default_scenario_type_new_entry(make_claim):
    c = make_claim(entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90"))
    assert c.scenario_type == Claim.ScenarioType.NEW_ENTRY
    assert c.purchase_price is None and c.purchase_date is None


# ── beat 경로 통합 회귀: refresh_monitor → process_monitor_scenarios 배선 ──────

@pytest.mark.django_db
class TestRefreshBeatIntegration:
    """refresh_monitor(수동 커맨드 + Celery beat 공유 단일 서비스 함수) 통합 회귀.

    HOLD-P1 이전엔 `process_monitor_scenarios(monitor, as_of_date=as_of)` kwargs 오타로 이 경로가
    try/except 밖 TypeError로 전건 크래시 → refresh beat의 scenario 처리 무발화(last_price_zone
    전부 None 근본 원인, common-bugs #62). 기존 테스트는 build_digest에 수동 events만 주입해
    이 배선을 커버 못 했다. 본 테스트가 kwargs 정합을 못박아 재발을 차단한다.
    """

    def test_refresh_processes_scenarios_and_records_zone(
        self, aapl_monitor, make_claim, daily_prices
    ):
        from apps.monitor.services.pipeline import refresh_monitor

        daily_prices(30, close_fn=lambda i: 100.0 + i)  # 최신 close ≈ 129 → target 120 초과 = OVERHEATED
        claim = make_claim(
            scenario_type=Claim.ScenarioType.NEW_ENTRY,
            entry_price=Decimal("100"), target_price=Decimal("120"), stop_price=Decimal("90"),
        )
        assert claim.last_price_zone is None

        # 버그(as_of_date=) 재발 시 이 호출에서 TypeError → 테스트 실패로 즉시 검출.
        result = refresh_monitor(aapl_monitor)

        assert "scenario_events" in result  # 배선 정상(예외 없이 이벤트 목록 반환)
        claim.refresh_from_db()
        # 전이가 실제로 기록됨 = scenario 처리 경로가 refresh 안에서 작동했다는 증거
        assert claim.last_price_zone == Claim.PriceZone.OVERHEATED
