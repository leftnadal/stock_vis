"""Slice 19c — 배치 엔진 v2 테스트 (dd/flow/신선도 — Part C 분).

Part D/E/F에서 다이얼·게이트·랭킹·레인·불변식 테스트를 확장한다.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.portfolio.models_my import PortfolioSnapshot, UserGoal
from apps.portfolio.services.snapshot import (
    _business_days,
    _flow_residual,
    compute_drawdown,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dd_user", password="x")


def _goal(user, window_start: date):
    """목표 생성 후 updated_at을 window_start로 백데이트(고점 창 = 그 이후 스냅샷)."""
    g = UserGoal.objects.create(
        user=user, target_return_pct=Decimal("10"), horizon_months=12
    )
    UserGoal.objects.filter(pk=g.pk).update(
        updated_at=timezone.make_aware(datetime(window_start.year, window_start.month, window_start.day))
    )
    return g


def _snap(user, d, total, flow="0", price_as_of=None, holdings=None):
    return PortfolioSnapshot.objects.create(
        user=user,
        date=d,
        total_krw=Decimal(str(total)),
        net_flow_krw=Decimal(str(flow)),
        price_as_of=price_as_of if price_as_of is not None else d,
        holdings_detail=holdings or [],
    )


# ---- _business_days ----


def test_business_days_weekend_excluded():
    assert _business_days(date(2026, 7, 10), date(2026, 7, 13)) == 1  # Fri→Mon
    assert _business_days(date(2026, 7, 13), date(2026, 7, 16)) == 3  # Mon→Thu
    assert _business_days(date(2026, 7, 13), date(2026, 7, 13)) == 0


# ---- dd 핵심 (DoD §6-4) ----


@pytest.mark.django_db
def test_dd_price_drop_3pct(user):
    """⑴ 가격 −3% → dd = 3% (flow 0)."""
    _goal(user, date(2026, 7, 1))
    _snap(user, date(2026, 7, 1), 1000)  # 고점
    _snap(user, date(2026, 7, 2), 970)  # 3% 하락
    r = compute_drawdown(user)
    assert r["dd"] == Decimal("0.03")
    assert r["is_new_high"] is False


@pytest.mark.django_db
def test_dd_withdrawal_unchanged(user):
    """⑵ 출금 → dd 불변(flow 조정으로 거짓 드로다운 0)."""
    _goal(user, date(2026, 7, 1))
    _snap(user, date(2026, 7, 1), 1000)  # 고점, dd 0
    _snap(user, date(2026, 7, 2), 900, flow="-100")  # 100 출금(가격변화 0)
    r = compute_drawdown(user)
    assert r["dd"] == Decimal("0")  # 출금은 성과 아님 → dd 불변


@pytest.mark.django_db
def test_dd_deposit_then_drop_measured_on_new_base(user):
    """⑶ 입금 후 가격 하락 → dd는 입금 반영된 고점 기준(고점 조정)."""
    _goal(user, date(2026, 7, 1))
    _snap(user, date(2026, 7, 1), 1000)  # 고점
    _snap(user, date(2026, 7, 2), 1100, flow="100")  # 100 입금 → 조정 고점 1100
    _snap(user, date(2026, 7, 3), 1067)  # 3% 하락(1100*0.97≈1067)
    r = compute_drawdown(user)
    # 조정 고점 1100 기준 (1100-1067)/1100 = 3%
    assert abs(r["dd"] - Decimal("0.03")) < Decimal("0.001")


@pytest.mark.django_db
def test_dd_new_high(user):
    """신고점 국면 = 현재 총자산 >= 조정 고점 → G 점등 신호."""
    _goal(user, date(2026, 7, 1))
    _snap(user, date(2026, 7, 1), 1000)
    _snap(user, date(2026, 7, 2), 1050)  # 신고점(가격 상승)
    r = compute_drawdown(user)
    assert r["dd"] == Decimal("0")
    assert r["is_new_high"] is True


# ---- flow 분해 (혼재 분리) ----


@pytest.mark.django_db
def test_flow_residual_mixed(user):
    """혼재: 가격 변화 + 매수를 flow/가격으로 분리. net_flow = 매수분만."""
    prev = _snap(
        user,
        date(2026, 7, 1),
        1000,
        holdings=[
            {"symbol": "AAA", "currency": "KRW", "shares": "10", "price": "100", "fx_rate": "1", "value_krw": "1000"}
        ],
    )
    # now: AAA 가격 100→110(가격효과 +100), 추가 5주 매수(매수=flow)
    ev = {
        "total_krw": Decimal("1650"),  # 15주 × 110
        "holdings_detail": [
            {"symbol": "AAA", "currency": "KRW", "shares": "15", "price": "110", "fx_rate": "1", "value_krw": "1650"}
        ],
    }
    flow = _flow_residual(prev, ev)
    # 가격효과 = 10주(전일) × (110−100) = 100. flow = (1650−1000) − 100 = 550(=5주×110)
    assert flow == Decimal("550")


@pytest.mark.django_db
def test_flow_residual_cold_start(user):
    """콜드 스타트(prev 없음) → flow 0."""
    ev = {"total_krw": Decimal("1000"), "holdings_detail": []}
    assert _flow_residual(None, ev) == Decimal("0")


# ---- 신선도 동결 ----


@pytest.mark.django_db
def test_dd_stale_price_frozen(user):
    """가격 나이 > 영업일 2일 → dd 직전 유효(fresh) 값 동결."""
    _goal(user, date(2026, 7, 1))
    _snap(user, date(2026, 7, 1), 1000)  # fresh
    _snap(user, date(2026, 7, 2), 970)  # fresh → dd 3%
    # d3(월요일) 스냅샷인데 가격 기준일이 6/25(2일 초과 과거) = stale
    _snap(user, date(2026, 7, 6), 900, price_as_of=date(2026, 6, 25))
    r = compute_drawdown(user)
    assert r["frozen"] is True
    assert r["dd"] == Decimal("0.03")  # 900(stale) 무시, 970(fresh) 기준 동결


# ---- 고점 리셋 (목표 변경 스코프) ----


@pytest.mark.django_db
def test_peak_reset_on_goal_change(user):
    """목표 변경(updated_at 전진) → 고점 창 리셋(그 이전 스냅샷 제외)."""
    _snap(user, date(2026, 6, 1), 2000)  # 리셋 전 옛 고점
    _snap(user, date(2026, 7, 1), 1000)
    _snap(user, date(2026, 7, 2), 950)
    _goal(user, date(2026, 7, 1))  # 창 시작 = 7/1 → 6/1 옛 고점 제외
    r = compute_drawdown(user)
    assert r["peak"] == Decimal("1000")  # 2000 아님
    assert r["dd"] == Decimal("0.05")  # (1000-950)/1000


# ---- 콜드 스타트 ----


@pytest.mark.django_db
def test_cold_start_single_snapshot(user):
    """스냅샷 1건(1일차) → dd 0, 신고점, window_days 1."""
    _goal(user, date(2026, 7, 1))
    _snap(user, date(2026, 7, 1), 1000)
    r = compute_drawdown(user)
    assert r["available"] is True
    assert r["dd"] == Decimal("0")
    assert r["is_new_high"] is True
    assert r["window_days"] == 1


@pytest.mark.django_db
def test_no_snapshots_unavailable(user):
    """스냅샷 0건 → available False (dd 0 안전값)."""
    _goal(user, date(2026, 7, 1))
    r = compute_drawdown(user)
    assert r["available"] is False
    assert r["dd"] == Decimal("0")
