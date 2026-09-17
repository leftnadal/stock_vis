"""ADDENDUM-MON-ALERT-DOWN-3A-0917-A — 변동성 비례 밴드 + 재발화 창.

D-NEAR-STOP-BUFFER 안 C. 기존 test_near_stop.py(고정 5% 계약 20건)는 무접촉 —
바닥값 5%가 유지되므로 두 파일의 계약이 충돌하지 않는다.
"""
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.monitor.models import Claim, Monitor
from apps.monitor.services.alerts import (
    build_digest,
    render_digest_html,
    render_digest_text,
)
from apps.monitor.services.price_zone import (
    NEAR_STOP_BUFFER,
    NEAR_STOP_CAP,
    NEAR_STOP_MULTIPLIER,
    NEAR_STOP_RECHECK_DAYS,
    is_near_stop,
)
from apps.monitor.services.scenario import (
    NEAR_STOP_WINDOW,
    near_stop_buffer,
    process_claim_scenario,
)

User = get_user_model()

AS_OF = date(2026, 9, 15)


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="near_buf_user", password="pw12345")


@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="TLN", stock_name="Talen Energy")


@pytest.fixture
def tln_monitor(owner, stock):
    return Monitor.objects.create(
        user=owner, scope="stock", target_ref="TLN", name="탈렌", current_state="active"
    )


@pytest.fixture
def hold_claim(tln_monitor):
    return Claim.objects.create(
        monitor=tln_monitor,
        assertion="보유 관리",
        scenario_type=Claim.ScenarioType.HOLD,
        purchase_price=Decimal("400.00"),
        target_price=Decimal("424.38"),
        stop_price=Decimal("271.20"),
        deadline=date(2026, 11, 17),
    )


@pytest.fixture
def make_prices(stock):
    """일간 변동률이 정확히 step인 종가열 n개를 as_of 이전 연속일에 적재."""

    def _make(n, step=0.04, start=100.0, end=AS_OF):
        c = start
        for i in range(n):
            d = end - timedelta(days=(n - 1 - i))
            from packages.shared.stocks.models import DailyPrice

            DailyPrice.objects.create(
                stock=stock, date=d,
                open_price=Decimal(str(round(c, 4))),
                high_price=Decimal(str(round(c * 1.01, 4))),
                low_price=Decimal(str(round(c * 0.99, 4))),
                close_price=Decimal(str(round(c, 4))),
                volume=1_000_000,
            )
            c *= (1.0 + step)

    return _make


# ── D-1 ~ D-3: near_stop_buffer ──────────────────────────────────────────────

@pytest.mark.django_db
class TestNearStopBuffer:
    def test_d1_high_volatility_scales_with_multiplier(self, make_prices):
        """D-1: 20거래일 이상 + 변동 1.5% → 배수×median (바닥값 초과·상한 미만)."""
        make_prices(NEAR_STOP_WINDOW + 1, step=0.015)
        buf = near_stop_buffer("TLN", AS_OF)
        assert buf == pytest.approx(NEAR_STOP_MULTIPLIER * 0.015, rel=1e-3)
        assert float(NEAR_STOP_BUFFER) < buf < float(NEAR_STOP_CAP)

    def test_d2_low_volatility_falls_back_to_floor(self, make_prices):
        """D-2: 저변동(0.5%) → 배수를 곱해도 바닥값 미만 → 바닥값."""
        make_prices(NEAR_STOP_WINDOW + 1, step=0.005)
        assert near_stop_buffer("TLN", AS_OF) == pytest.approx(float(NEAR_STOP_BUFFER))

    def test_d3_no_rows_falls_back(self, stock):
        """D-3: DailyPrice 0행 → 바닥값 폴백."""
        assert near_stop_buffer("TLN", AS_OF) == NEAR_STOP_BUFFER

    def test_d3_insufficient_rows_falls_back(self, make_prices):
        """D-3: 20행(수익률 19개) → 창 미달 → 바닥값 폴백."""
        make_prices(NEAR_STOP_WINDOW, step=0.04)
        assert near_stop_buffer("TLN", AS_OF) == NEAR_STOP_BUFFER

    def test_d3_cap_clamps_runaway_band(self, make_prices):
        """D-3: median 5% → 배수 4면 20%지만 상한 15%로 잘린다."""
        make_prices(NEAR_STOP_WINDOW + 1, step=0.05)
        raw = NEAR_STOP_MULTIPLIER * 0.05
        assert raw > float(NEAR_STOP_CAP)  # 전제: 상한이 실제로 개입하는 구간
        assert near_stop_buffer("TLN", AS_OF) == pytest.approx(float(NEAR_STOP_CAP))

    def test_d4_cap_inactive_below_threshold(self, make_prices):
        """D-4: median 3% → 12% 그대로(상한 미작동)."""
        make_prices(NEAR_STOP_WINDOW + 1, step=0.03)
        buf = near_stop_buffer("TLN", AS_OF)
        assert buf == pytest.approx(NEAR_STOP_MULTIPLIER * 0.03, rel=1e-3)
        assert buf < float(NEAR_STOP_CAP)

    def test_lead_time_is_multiplier_between_floor_and_cap(self, make_prices):
        """배수 = 리드타임 정의 — 밴드 ÷ median = 배수 (바닥·상한 미개입 구간)."""
        make_prices(NEAR_STOP_WINDOW + 1, step=0.02)
        assert near_stop_buffer("TLN", AS_OF) / 0.02 == pytest.approx(
            NEAR_STOP_MULTIPLIER, rel=1e-3
        )

    def test_unknown_symbol_falls_back(self, db):
        assert near_stop_buffer("NOSUCH", AS_OF) == NEAR_STOP_BUFFER

    def test_respects_as_of_cutoff(self, make_prices):
        """as_of 이후 행은 보지 않는다 — 과거 재현 가능성."""
        make_prices(NEAR_STOP_WINDOW + 1, step=0.04)
        assert near_stop_buffer("TLN", AS_OF - timedelta(days=90)) == NEAR_STOP_BUFFER


# ── D-4 ~ D-5: 재발화 창 ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecheckWindow:
    """가격 없음 → 버퍼는 바닥값 5% 고정. 재발화 창만 분리 검증."""

    IN_BAND = 282.15  # 손절 271.20 대비 +4.0% → 5% 밴드 안
    OUT_BAND = 320.00

    def _notified_at(self, claim, d):
        # beat 발화 시각(22:45 UTC = 18:45 ET)을 재현. Django 5에서 timezone.utc 제거됨.
        ts = datetime(d.year, d.month, d.day, 22, 45, tzinfo=dt_timezone.utc)
        Claim.objects.filter(pk=claim.pk).update(near_stop_notified_at=ts)
        claim.refresh_from_db()
        return ts

    def test_d4_no_refire_before_window(self, hold_claim):
        """D-4: 발화 후 4일 → 창 미달 → 무발화."""
        self._notified_at(hold_claim, AS_OF)
        events = process_claim_scenario(
            hold_claim, self.IN_BAND, AS_OF + timedelta(days=NEAR_STOP_RECHECK_DAYS - 1)
        )
        assert [e for e in events if e["type"] == "near_stop"] == []

    def test_d4_refires_at_window_with_flag(self, hold_claim):
        """D-4: 5일 경과 → 재발화, recheck=True."""
        self._notified_at(hold_claim, AS_OF)
        events = process_claim_scenario(
            hold_claim, self.IN_BAND, AS_OF + timedelta(days=NEAR_STOP_RECHECK_DAYS)
        )
        near = [e for e in events if e["type"] == "near_stop"]
        assert len(near) == 1
        assert near[0]["recheck"] is True
        assert near[0]["band_pct"] == pytest.approx(5.0)

    def test_d4_timestamp_advances_on_refire(self, hold_claim):
        """재발화 시 타임스탬프 갱신 → 다음 창이 그 시점부터 다시 센다."""
        old = self._notified_at(hold_claim, AS_OF)
        process_claim_scenario(
            hold_claim, self.IN_BAND, AS_OF + timedelta(days=NEAR_STOP_RECHECK_DAYS)
        )
        hold_claim.refresh_from_db()
        assert hold_claim.near_stop_notified_at > old

    def test_d5_exit_releases_then_first_fire_again(self, hold_claim):
        """D-5: 밴드 이탈 → 가드 None → 재진입 시 최초 발화(recheck=False)."""
        first = process_claim_scenario(hold_claim, self.IN_BAND, AS_OF)
        assert [e for e in first if e["type"] == "near_stop"][0]["recheck"] is False

        process_claim_scenario(hold_claim, self.OUT_BAND, AS_OF + timedelta(days=1))
        hold_claim.refresh_from_db()
        assert hold_claim.near_stop_notified_at is None

        again = process_claim_scenario(
            hold_claim, self.IN_BAND, AS_OF + timedelta(days=2)
        )
        near = [e for e in again if e["type"] == "near_stop"]
        assert len(near) == 1
        assert near[0]["recheck"] is False


# ── D-5: ET 정합 ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEtAlignment:
    """재발화 창 날짜 비교가 ET 기준인가. as_of=et_today()와 같은 축이어야 한다.

    UTC date 비교는 beat가 22:45 UTC일 때만 우연히 일치했다 — beat 시각은 코드가
    아니라 DB PeriodicTask에 있으므로(공통버그 #28) 그 결합을 끊는다.
    """

    IN_BAND = 282.15  # 가격 없음 → 밴드는 바닥값 5%, 손절 271.20 대비 필요 4.04%

    def _set(self, claim, ts):
        Claim.objects.filter(pk=claim.pk).update(near_stop_notified_at=ts)
        claim.refresh_from_db()

    def _fired(self, claim, as_of):
        ev = process_claim_scenario(claim, self.IN_BAND, as_of)
        return [e for e in ev if e["type"] == "near_stop"]

    def test_evening_utc_fires_on_fifth_et_day(self, hold_claim):
        """22:45 UTC = 같은 날 18:45 ET → ET 날짜 = D. 5일째 발화."""
        d = date(2026, 9, 15)
        self._set(hold_claim, datetime(2026, 9, 15, 22, 45, tzinfo=dt_timezone.utc))
        assert self._fired(hold_claim, d + timedelta(days=4)) == []
        assert len(self._fired(hold_claim, d + timedelta(days=5))) == 1

    def test_after_utc_midnight_still_fifth_et_day(self, hold_claim):
        """01:00 UTC = 전날 20:00 ET → ET 날짜 = D−1. 따라서 D+4에 이미 5일째.

        UTC date 비교였다면 D+5까지 기다렸을 케이스 — 여기서 갈린다.
        """
        self._set(hold_claim, datetime(2026, 9, 16, 1, 0, tzinfo=dt_timezone.utc))
        et_day = date(2026, 9, 15)  # = ET 기준 발송일
        assert self._fired(hold_claim, et_day + timedelta(days=4)) == []
        fired = self._fired(hold_claim, et_day + timedelta(days=5))
        assert len(fired) == 1
        assert fired[0]["recheck"] is True

    def test_utc_and_et_disagree_on_this_timestamp(self, hold_claim):
        """전제 확증: 01:00 UTC는 UTC date와 ET date가 실제로 다르다."""
        ts = datetime(2026, 9, 16, 1, 0, tzinfo=dt_timezone.utc)
        from apps.monitor.services.scenario import _ET

        assert ts.date() == date(2026, 9, 16)
        assert ts.astimezone(_ET).date() == date(2026, 9, 15)


# ── D-6: 렌더 ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRenderBand:
    def _digest(self, recheck, band=5.0):
        ev = [{
            "type": "near_stop", "claim_id": "x", "monitor_name": "탈렌",
            "target_ref": "TLN", "close": 282.15, "stop": 271.2,
            "to_stop_pct": -3.88, "band_pct": band, "recheck": recheck,
            "immediate": True,
        }]
        return build_digest(AS_OF, scenario_events=ev)

    def test_d6_text_shows_band(self):
        body = render_digest_text(self._digest(False))
        assert "(밴드 5.0%)" in body
        assert "재확인" not in body

    def test_d6_text_shows_recheck(self):
        body = render_digest_text(self._digest(True))
        assert "밴드 5.0%" in body
        assert "재확인" in body

    def test_d6_html_shows_band(self):
        html = render_digest_html(self._digest(False))
        assert "밴드 5.0%" in html
        assert "재확인" not in html

    def test_d6_html_shows_recheck(self):
        html = render_digest_html(self._digest(True))
        assert "밴드 5.0%" in html and "재확인" in html

    def test_d6_volatile_band_rendered(self):
        assert "(밴드 8.0%)" in render_digest_text(self._digest(False, band=8.0))


# ── D-7: 계약 — 09-15 실측 6종목 × 고정 median 스텁 ──────────────────────────

class TestFiringSetContract:
    """09-15 종가·손절 실측 + median 일간 변동률 고정 스텁 → 발화 집합 단언.

    고정 5%(안 B) 대비 변동성 비례(안 C)가 어떤 종목을 더/덜 잡는지 계약으로 고정.
    """

    # (심볼, 종가, 손절, median 일간 변동률 스텁)
    # 필요 버퍼는 **손절가 기준**이다 — 발화 조건이 close ≤ stop×(1+buffer)이므로
    # 필요값 = close/stop − 1. 종가 기준 거리로 나누면 틀린다(디렉터 정정 0917-B).
    ROWS = [
        ("TLN", 282.15, "271.20", 0.020),   # 밴드 8.0%  | 필요 4.04%  → 발화
        ("GEV", 882.81, "818.07", 0.045),   # 밴드 15.0%(상한) | 필요 7.91%  → 발화
        ("IONQ", 37.05, "34.09", 0.060),    # 밴드 15.0%(상한) | 필요 8.68%  → 발화
        ("GOOGL", 344.98, "291.38", 0.012), # 밴드 5.0%(바닥)  | 필요 18.40% → 무발화
        ("PLTR", 172.56, "101.29", 0.030),  # 밴드 12.0% | 필요 70.36% → 무발화
        ("IREN", 41.58, "23.98", 0.055),    # 밴드 15.0%(상한) | 필요 73.40% → 무발화
    ]

    def _buf(self, median):
        return min(
            float(NEAR_STOP_CAP),
            max(float(NEAR_STOP_BUFFER), NEAR_STOP_MULTIPLIER * median),
        )

    def test_required_buffer_is_stop_anchored(self):
        """필요 버퍼 = close/stop − 1 (손절가 기준). 발화 경계를 직접 고정한다."""
        for _, close, stop, _ in self.ROWS:
            need = close / float(stop) - 1.0
            assert is_near_stop(close, Decimal(stop), need * 1.001)
            assert not is_near_stop(close, Decimal(stop), need * 0.999)

    def test_fixed_five_percent_fires_only_tln(self):
        """안 B(고정 5%) 기준선 — 회귀 감시용."""
        got = [s for s, c, st, _ in self.ROWS if is_near_stop(c, Decimal(st))]
        assert got == ["TLN"]

    def test_volatility_proportional_fires_three(self):
        """안 C(배수 4·상한 15%) — 고변동 종목(GEV·IONQ)이 밴드 확대로 편입된다."""
        got = [
            s for s, c, st, m in self.ROWS
            if is_near_stop(c, Decimal(st), self._buf(m))
        ]
        assert got == ["TLN", "GEV", "IONQ"]

    def test_floor_never_narrows_below_five(self):
        """저변동이어도 밴드가 5% 아래로 좁아지지 않는다 — 바닥값 계약."""
        for _, _, _, m in self.ROWS:
            assert self._buf(m) >= float(NEAR_STOP_BUFFER)

    def test_band_is_multiplier_times_median_between_floor_and_cap(self):
        """바닥·상한이 개입하지 않는 구간에서만 밴드 = 배수 × median."""
        assert self._buf(0.02) == pytest.approx(NEAR_STOP_MULTIPLIER * 0.02)

    def test_cap_binds_above_threshold(self):
        """상한 개입 구간 — median 4.5%는 배수 4면 18%지만 15%로 잘린다."""
        assert NEAR_STOP_MULTIPLIER * 0.045 > float(NEAR_STOP_CAP)
        assert self._buf(0.045) == pytest.approx(float(NEAR_STOP_CAP))
