"""3-A 손절 접근 경고 — 순수 판정 · 1회 가드 · 다이제스트 배선.

zone 축 무접촉(D-HOLD-DECISIONS 2: resolve_zone·PriceZone enum 불변)을 전제로,
손절 접근을 별개 축으로 검증한다. 실제 사고 맥락: hold 모드에서 매입가 아래가
ENTRY 한 칸이라 손절 3.9% 앞인 종목에 알림이 나갈 경로가 없었다(2026-09-17).
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.monitor.models import Claim, Monitor
from apps.monitor.services.alerts import (
    build_digest,
    render_digest_html,
    render_digest_subject,
    render_digest_text,
)
from apps.monitor.services.price_zone import (
    NEAR_STOP_BUFFER,
    is_near_stop,
    resolve_zone,
)
from apps.monitor.services.scenario import process_claim_scenario

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="near_stop_user", password="pw12345")


@pytest.fixture
def tln_monitor(owner):
    return Monitor.objects.create(
        user=owner, scope="stock", target_ref="TLN", name="탈렌", current_state="active"
    )


@pytest.fixture
def hold_claim(tln_monitor):
    """실사고 형상 — 매입 400, 목표 424.38, 손절 271.20 (TLN 2026-09-15)."""
    return Claim.objects.create(
        monitor=tln_monitor,
        assertion="보유 관리",
        scenario_type=Claim.ScenarioType.HOLD,
        purchase_price=Decimal("400.00"),
        target_price=Decimal("424.38"),
        stop_price=Decimal("271.20"),
        deadline=date(2026, 11, 17),
    )


# ── 순수 판정 ────────────────────────────────────────────────────────────────

class TestIsNearStop:
    def test_buffer_is_five_percent(self):
        assert NEAR_STOP_BUFFER == Decimal("0.05")

    def test_inside_band(self):
        # 손절 100 → 105까지가 밴드
        assert is_near_stop(104.9, Decimal("100")) is True

    def test_exact_boundary_included(self):
        assert is_near_stop(105.0, Decimal("100")) is True

    def test_outside_band(self):
        assert is_near_stop(105.01, Decimal("100")) is False

    def test_already_exited_is_not_near(self):
        """손절선을 넘었으면 접근이 아니라 이탈 — EXITED zone 소관."""
        assert is_near_stop(100.0, Decimal("100")) is False
        assert is_near_stop(99.0, Decimal("100")) is False

    def test_none_inputs(self):
        assert is_near_stop(None, Decimal("100")) is False
        assert is_near_stop(100.0, None) is False

    def test_nonpositive_stop(self):
        assert is_near_stop(10.0, Decimal("0")) is False

    def test_real_positions_2026_09_15(self):
        """실측 6종목 중 5% 임계로 TLN만 잡혀야 한다."""
        rows = [  # (종가, 손절, 잡히는가)
            ("TLN", 282.15, "271.20", True),    # -3.9%
            ("GEV", 882.81, "818.07", False),   # -7.3%
            ("IONQ", 37.05, "34.09", False),    # -8.0%
            ("GOOGL", 344.98, "291.38", False), # -15.5%
            ("PLTR", 172.56, "101.29", False),  # -41.3%
            ("IREN", 41.58, "23.98", False),    # -42.3%
        ]
        got = [sym for sym, c, s, _ in rows if is_near_stop(c, Decimal(s))]
        assert got == ["TLN"]


# ── zone 축 무접촉 ───────────────────────────────────────────────────────────

class TestZoneAxisUntouched:
    def test_near_stop_close_still_resolves_to_entry(self):
        """손절 접근 구간의 종가라도 zone은 여전히 ENTRY — 기존 수학 불변."""
        z = resolve_zone(
            282.15, Decimal("400.00"), Decimal("424.38"), Decimal("271.20")
        )
        assert z == Claim.PriceZone.ENTRY


# ── 1회 가드 / 해제 ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOnceGuard:
    def test_emits_once_on_entry(self, hold_claim):
        events = process_claim_scenario(hold_claim, 282.15, date(2026, 9, 15))
        near = [e for e in events if e["type"] == "near_stop"]
        assert len(near) == 1
        e = near[0]
        assert e["immediate"] is True
        assert e["target_ref"] == "TLN"
        assert e["stop"] == pytest.approx(271.20)
        assert e["to_stop_pct"] == pytest.approx(-3.88, abs=0.05)
        hold_claim.refresh_from_db()
        assert hold_claim.near_stop_notified_at is not None

    def test_does_not_repeat_next_day(self, hold_claim):
        process_claim_scenario(hold_claim, 282.15, date(2026, 9, 15))
        hold_claim.refresh_from_db()
        events = process_claim_scenario(hold_claim, 280.00, date(2026, 9, 16))
        assert [e for e in events if e["type"] == "near_stop"] == []

    def test_guard_released_on_recovery(self, hold_claim):
        process_claim_scenario(hold_claim, 282.15, date(2026, 9, 15))
        hold_claim.refresh_from_db()
        # 밴드 밖으로 회복 → 가드 해제
        process_claim_scenario(hold_claim, 320.00, date(2026, 9, 16))
        hold_claim.refresh_from_db()
        assert hold_claim.near_stop_notified_at is None
        # 재진입 → 다시 1회 발화
        events = process_claim_scenario(hold_claim, 281.00, date(2026, 9, 17))
        assert len([e for e in events if e["type"] == "near_stop"]) == 1

    def test_no_event_when_far_from_stop(self, hold_claim):
        events = process_claim_scenario(hold_claim, 400.00, date(2026, 9, 15))
        assert [e for e in events if e["type"] == "near_stop"] == []

    def test_no_event_without_stop_price(self, tln_monitor):
        c = Claim.objects.create(
            monitor=tln_monitor, assertion="가격 없는 구 가설",
            scenario_type=Claim.ScenarioType.HOLD,
        )
        events = process_claim_scenario(c, 282.15, date(2026, 9, 15))
        assert [e for e in events if e["type"] == "near_stop"] == []

    def test_breach_releases_guard_and_zone_takes_over(self, hold_claim):
        """손절선을 넘으면 near_stop 가드는 풀리고 EXITED zone 전이가 알린다."""
        process_claim_scenario(hold_claim, 282.15, date(2026, 9, 15))
        hold_claim.refresh_from_db()
        events = process_claim_scenario(hold_claim, 265.00, date(2026, 9, 16))
        hold_claim.refresh_from_db()
        assert hold_claim.near_stop_notified_at is None
        zone_ev = [e for e in events if e["type"] == "zone"]
        assert len(zone_ev) == 1
        assert zone_ev[0]["to_zone"] == Claim.PriceZone.EXITED
        assert zone_ev[0]["immediate"] is True


# ── 다이제스트 배선 ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDigestWiring:
    @pytest.fixture
    def near_event(self):
        return [{
            "type": "near_stop",
            "claim_id": "x",
            "monitor_name": "탈렌",
            "target_ref": "TLN",
            "close": 282.15,
            "stop": 271.20,
            "to_stop_pct": -3.88,
            "immediate": True,
        }]

    def test_near_stop_alone_makes_content(self, near_event):
        """다른 변동이 0건이어도 손절 접근만으로 메일이 나가야 한다."""
        d = build_digest(date(2026, 9, 15), scenario_events=near_event)
        assert d["has_content"] is True
        assert len(d["near_stops"]) == 1
        assert d["near_stops"][0]["target_ref"] == "TLN"

    def test_empty_digest_still_no_content(self):
        d = build_digest(date(2026, 9, 15), scenario_events=[])
        assert d["has_content"] is False
        assert d["near_stops"] == []

    def test_subject_leads_with_near_stop(self, near_event):
        d = build_digest(date(2026, 9, 15), scenario_events=near_event)
        subj = render_digest_subject(d)
        assert "손절 접근 1건" in subj
        assert subj.index("손절 접근") < len(subj)

    def test_text_body_has_section(self, near_event):
        d = build_digest(date(2026, 9, 15), scenario_events=near_event)
        body = render_digest_text(d)
        assert "■ 손절 접근 (즉시)" in body
        assert "TLN" in body
        assert "-3.9%" in body

    def test_html_body_has_section(self, near_event):
        d = build_digest(date(2026, 9, 15), scenario_events=near_event)
        html = render_digest_html(d)
        assert "손절 접근 (즉시)" in html
        assert "TLN" in html
        assert "-3.9%" in html
