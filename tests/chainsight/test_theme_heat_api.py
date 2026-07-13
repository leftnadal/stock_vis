"""
Theme Heat API 테스트 (TH-15, 결정23B/24C/25③) — E1 버튼바 / E2 카드.

게이트: A1 최신행 선택·원장 일치 / A2 driver 합 100%(delta·level) / A3 accumulating days /
A4 blocked(universe_stale) / 인증 / band_display / eta_days 게이트.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.chain_sight.models import HeatEntity, ThemeHeatScore, ThemeNewsVolume
from apps.chain_sight.services.heat_api_service import (
    band_display,
    build_card,
    compute_driver,
    eta_days,
)
from apps.chain_sight.services.heat_history_markers import crossing_marker


def _sector(ref_id):
    return HeatEntity.objects.get(kind="sector", ref_id=ref_id)


def _score(ref_id, d, score, status="warning", components=None):
    return ThemeHeatScore.objects.create(
        theme=_sector(ref_id), date=d, score=score, status=status,
        components=components or {}, evidence={},
    )


def _comp(z, s, **extra):
    return {"z": z, "s": s, **extra}


def _auth_client():
    u = get_user_model().objects.create_user(username="t_heat", password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


# ────────────────────────── 순수 함수 ──────────────────────────
class TestBandDisplay:
    def test_mapping(self):
        assert band_display("cool") == "냉각"
        assert band_display("warning") == "가열"
        assert band_display("overheated") == "과열"
        assert band_display(None) is None


class TestDriver:
    # 3성분 present, C4~C8 결측(present_weight = 0.18+0.18+0.14 = 0.50)
    def _comps(self, s1, s2, s3):
        return {"C1": _comp(0.5, s1), "C2": _comp(0.5, s2), "C3": _comp(0.5, s3, z_mode="time_series")}

    def test_up_direction_sum_100(self):  # B1 up
        today = self._comps(0.9, 0.6, 0.7)
        prev = self._comps(0.5, 0.6, 0.5)   # C1 +, C3 + (양 증분)
        driver, shares = compute_driver(today, prev, delta_1d=3)
        assert driver["direction"] == "up" and driver["basis"] == "delta"
        assert abs(sum(shares.values()) - 100.0) < 0.1  # A2/B1

    def test_down_direction_sum_100(self):  # B1 down (신설)
        today = self._comps(0.4, 0.6, 0.4)
        prev = self._comps(0.9, 0.6, 0.7)   # C1 −, C3 − (음 증분)
        driver, shares = compute_driver(today, prev, delta_1d=-3)
        assert driver["direction"] == "down" and driver["basis"] == "delta"
        assert abs(sum(shares.values()) - 100.0) < 0.1  # B1

    def test_none_direction_level(self):  # B1 none (전일 부재)
        today = self._comps(0.9, 0.6, 0.7)
        driver, shares = compute_driver(today, None)
        assert driver["direction"] == "none" and driver["basis"] == "level"
        assert abs(sum(shares.values()) - 100.0) < 0.1

    def test_degenerate_keeps_direction(self):  # 퇴화: delta>0인데 양증분 없음 → level 폴백 + direction 유지
        today = self._comps(0.4, 0.5, 0.4)
        prev = self._comps(0.9, 0.6, 0.7)   # 전 성분 하락(양증분 0)인데 delta_1d>0 강제
        driver, shares = compute_driver(today, prev, delta_1d=1)
        assert driver["direction"] == "up" and driver["basis"] == "level"
        assert abs(sum(shares.values()) - 100.0) < 0.1


# ────────────────────────── A1 최신행 선택 + 원장 일치 ──────────────────────────
@pytest.mark.django_db
class TestLatestRowSelection:
    def test_0712_selected_over_0710(self):
        # 07-10(67)·07-12(65) 공존 → 07-12 선택(A1)
        comps = {"C1": _comp(0.5, 0.6), "C2": _comp(0.5, 0.6), "C3": _comp(0.5, 0.6, z_mode="time_series")}
        _score("Financial Services", date(2026, 7, 10), 67, components=comps)
        _score("Financial Services", date(2026, 7, 12), 65, components=comps)
        card = build_card("Financial Services")
        assert card["as_of"] == "2026-07-12"
        assert card["score"] == 65  # 원장 영속값 그대로(재계산 없음)
        assert card["delta_1d"] == -2  # 65 - 67
        assert card["history"]["values"] == [67, 65]  # date 오름차순

    def test_e1_score_matches_ledger(self):
        comps = {"C1": _comp(0.5, 0.6), "C2": _comp(0.5, 0.6), "C3": _comp(0.5, 0.6)}
        _score("Technology", date(2026, 7, 12), 58, components=comps)
        client = _auth_client()
        resp = client.get("/api/v1/chainsight/theme-heat/")
        assert resp.status_code == 200
        tech = next(t for t in resp.json()["themes"] if t["theme"] == "Technology")
        assert tech["status"] == "computed" and tech["score"] == 58
        assert tech["band_display"] == "가열"


# ────────────────────────── 결정29 전환일 driver 보류 ──────────────────────────
class TestCrossingMarker:
    def test_crosses_guard_marker(self):
        # 07-10 → 07-12 구간이 07-12 개정 마커를 가로지름
        m = crossing_marker(date(2026, 7, 10), date(2026, 7, 12))
        assert m and m["kind"] == "c1_thin_quarter_guard"

    def test_after_marker_no_cross(self):
        # 07-12 → 07-13 구간엔 (07-12, 07-13] 마커 없음 → 정상
        assert crossing_marker(date(2026, 7, 12), date(2026, 7, 13)) is None

    def test_no_prior_no_cross(self):
        assert crossing_marker(None, date(2026, 7, 12)) is None


@pytest.mark.django_db
class TestDriverHold:
    def _c(self, s):
        return {"C1": _comp(0.5, s), "C2": _comp(0.5, 0.6), "C3": _comp(0.5, 0.6, z_mode="time_series")}

    def test_hold_across_marker(self):
        # prev 07-10, latest 07-12 → 마커 가로지름 → driver 보류, 온도·delta 노출
        _score("Technology", date(2026, 7, 10), 67, components=self._c(0.9))
        _score("Technology", date(2026, 7, 12), 55, components=self._c(0.5))
        card = build_card("Technology")
        assert card["score"] == 55 and card["delta_1d"] == -12  # 온도·delta 노출
        assert card["driver"]["held"] is True
        assert card["driver"]["reason"] == "methodology_revision"
        assert "direction" not in card["driver"]  # direction/basis/percent 미표시

    def test_normal_after_marker(self):
        # prev 07-12, latest 07-13 → 마커 미가로지름 → 정상 driver
        _score("Technology", date(2026, 7, 12), 55, components=self._c(0.5))
        _score("Technology", date(2026, 7, 13), 57, components=self._c(0.7))
        card = build_card("Technology")
        assert card["driver"]["held"] is False
        assert card["driver"]["direction"] == "up"  # 정상 재개


# ────────────────────────── A3 accumulating days ──────────────────────────
@pytest.mark.django_db
class TestAccumulatingDays:
    def test_days_match_news_volume(self):
        e = _sector("Healthcare")
        for i in range(1, 8):  # 7 days
            ThemeNewsVolume.objects.create(theme=e, date=date(2026, 6, i), mention_count=3)
        card = build_card("Healthcare")
        assert card["status"] == "accumulating"
        assert card["score"] is None
        assert card["days"] == 7  # ThemeNewsVolume 실측
        assert card["days_required"] == 26


# ────────────────────────── A4 blocked (universe_stale) ──────────────────────────
@pytest.mark.django_db
class TestBlocked:
    def test_stale_marks_blocked_with_value(self):
        comps = {
            "C1": _comp(0.5, 0.6), "C2": _comp(0.5, 0.6), "C3": _comp(0.5, 0.6),
            "universe_stale": True, "universe_as_of": "2026-05-01",
        }
        _score("Energy", date(2026, 7, 12), 55, components=comps)
        card = build_card("Energy")
        # 값+사유 동봉(은닉 아님): score 는 정상 반환 + blocked 부여
        assert card["score"] == 55
        assert card["blocked"]["reason"] == "universe_stale"
        assert card["blocked"]["since"] == "2026-05-01"
        assert card["blocked"]["days_stale"] == (date(2026, 7, 12) - date(2026, 5, 1)).days


# ────────────────────────── 인증 ──────────────────────────
@pytest.mark.django_db
class TestAuth:
    def test_bar_requires_auth(self):
        assert APIClient().get("/api/v1/chainsight/theme-heat/").status_code in (401, 403)

    def test_card_requires_auth(self):
        assert APIClient().get("/api/v1/chainsight/theme-heat/Technology/").status_code in (401, 403)

    def test_card_unknown_theme_404(self):
        client = _auth_client()
        assert client.get("/api/v1/chainsight/theme-heat/Nonsense/").status_code == 404


# ────────────────────────── eta_days 게이트 ──────────────────────────
@pytest.mark.django_db
class TestEtaDays:
    def test_stable_accumulation_yields_eta(self):
        # 최근 14일 매일 mention → CV=0 < 0.3 → eta 산출
        e = _sector("Utilities")
        for i in range(14):
            ThemeNewsVolume.objects.create(theme=e, date=date(2026, 7, i + 1), mention_count=2)
        eta = eta_days("Utilities", current_days=14, as_of=date(2026, 7, 14))
        assert eta == 26 - 14  # rate=1.0 → ceil(12/1)=12

    def test_sparse_accumulation_no_eta(self):
        # 14일 중 3일만 → CV 높음 → None
        e = _sector("Real Estate")
        for i in (1, 6, 12):
            ThemeNewsVolume.objects.create(theme=e, date=date(2026, 7, i), mention_count=2)
        assert eta_days("Real Estate", current_days=3, as_of=date(2026, 7, 14)) is None
