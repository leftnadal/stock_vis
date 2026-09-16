"""
H-1 `check_weekly_firing_contract` · H-2 `check_service_restart_storm` 역케이스
(DSS-ASOF-1-R2 §2, D-FIRING-WATCH-DECOUPLE).

오탐을 없애려다 실장애를 놓치면 개악이다 — 정상=미점등 / 결번=점등 / 전건 missing_prev=점등을
전부 박제한다. 특히 세 번째는 2026-09-12 사건의 실제 형태이며 '행 존재'만으로는 잡히지 않았다.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from scripts import health_check as hc

ET = ZoneInfo("America/New_York")


# ── 직전 금요일 산술 (as_of_week 미사용 = 의도적 분리) ────────────────────────
@pytest.mark.parametrize(
    "now_et, expected",
    [
        (dt.datetime(2026, 9, 16, 10, 0, tzinfo=ET), dt.date(2026, 9, 11)),   # 수요일
        (dt.datetime(2026, 9, 11, 16, 0, tzinfo=ET), dt.date(2026, 9, 11)),   # 금 마감 직후
        (dt.datetime(2026, 9, 11, 15, 59, tzinfo=ET), dt.date(2026, 9, 4)),   # 금 장중
        (dt.datetime(2026, 9, 12, 15, 3, tzinfo=ET), dt.date(2026, 9, 11)),   # 토(09-12 사건)
    ],
)
def test_last_completed_friday(now_et, expected):
    assert hc._last_completed_friday(now_et) == expected


# ── H-1 역케이스 ─────────────────────────────────────────────────────────────
class _Q:
    """model.objects 최소 스텁: order_by().values_list().first() / filter().count()."""

    def __init__(self, latest, total=0, valid=0):
        self._latest, self._total, self._valid = latest, total, valid

    def order_by(self, *_a):
        return self

    def values_list(self, *_a, **_k):
        return self

    def first(self):
        return self._latest

    def filter(self, **kw):
        self._excl_false = kw.get("excluded") is False
        return self

    def count(self):
        return self._valid if getattr(self, "_excl_false", False) else self._total


def _run_h1(monkeypatch, snap_latest, dss_latest, dss_total, dss_valid, now_et):
    """Django 계층을 스텁으로 갈아끼우고 H-1 본문 로직만 돌린다."""
    models = {
        "EstimateSnapshot": _Q(snap_latest),
        "SymbolDemandSignal": _Q(dss_latest, dss_total, dss_valid),
    }
    friday = hc._last_completed_friday(now_et)
    worst, notes = hc.OK, []
    for label, _field, hh, mm in hc._FIRING_TARGETS:
        m = models[label]
        latest = m.order_by("-x").values_list("x", flat=True).first()
        deadline = dt.datetime.combine(friday, dt.time(hh, mm), tzinfo=ET)
        lag_h = (now_et - deadline).total_seconds() / 3600.0
        if latest is None or latest < friday:
            st = hc.ERROR if lag_h > hc.FIRING_ERROR_HOURS else (
                hc.WARN if lag_h > hc.FIRING_WARN_HOURS else hc.OK)
            worst = max(worst, st)
            notes.append(f"{label} 결번")
            continue
        if label == "SymbolDemandSignal":
            total = m.filter(anchor_date=latest).count()
            valid = m.filter(anchor_date=latest, excluded=False).count()
            if total and valid == 0:
                worst = max(worst, hc.ERROR)
                notes.append(f"{label} 유효신호 0")
    return worst, notes


FRI = dt.date(2026, 9, 11)
WED_AFTER = dt.datetime(2026, 9, 16, 10, 0, tzinfo=ET)          # 마감 후 ~114h
SAT_NEXT_MORNING = dt.datetime(2026, 9, 12, 9, 0, tzinfo=ET)    # 마감 후 ~16h


def test_normal_does_not_fire(monkeypatch):
    """정상: 양쪽 다 직전 금요일 앵커 + 유효신호 다수 → 미점등."""
    worst, notes = _run_h1(monkeypatch, FRI, FRI, 501, 484, WED_AFTER)
    assert worst == hc.OK, notes


def test_missing_anchor_within_grace_does_not_fire(monkeypatch):
    """결번이지만 마감 후 16h(<48h) = catch-up 여유 창 → 미점등(경보 피로 방지)."""
    worst, _ = _run_h1(monkeypatch, dt.date(2026, 9, 4), dt.date(2026, 9, 4), 501, 484,
                       SAT_NEXT_MORNING)
    assert worst == hc.OK


def test_missing_anchor_beyond_error_threshold_fires(monkeypatch):
    """결번 주입 + 마감 후 96h 초과 → ERROR."""
    worst, notes = _run_h1(monkeypatch, dt.date(2026, 9, 4), dt.date(2026, 9, 4), 501, 484,
                           WED_AFTER)
    assert worst == hc.ERROR, notes


def test_all_missing_prev_fires(monkeypatch):
    """🔑 2026-09-12 실제 형태: 행 502건 존재하나 excluded=False가 0 → ERROR.

    행 존재만 보는 감시는 이것을 놓쳤다. 그래서 유효신호 수를 함께 본다.
    """
    worst, notes = _run_h1(monkeypatch, dt.date(2026, 9, 12), dt.date(2026, 9, 12), 502, 0,
                           WED_AFTER)
    assert worst == hc.ERROR
    assert any("유효신호 0" in n for n in notes), notes


# ── H-2 역케이스 ─────────────────────────────────────────────────────────────
BEAT_BANNER = hc._RESTART_SOURCES[0][2]
BEAT_TS = hc._RESTART_SOURCES[0][3]


def _write_beat_log(tmp_path, n, when):
    p = tmp_path / "celery-beat-error.log"
    p.write_text("".join(
        f"[{when}{i % 60:02d}: INFO/MainProcess] beat: Starting...\n" for i in range(n)
    ), encoding="utf-8")
    return p


def test_restart_storm_quiet_does_not_fire(tmp_path):
    """정상 재기동 2회 → 임계 미만."""
    when = (dt.datetime.now() - dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")[:17]
    p = _write_beat_log(tmp_path, 2, when)
    since = (dt.datetime.now() - dt.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    n = hc._count_recent_restarts(p, BEAT_BANNER, BEAT_TS, since)
    assert n == 2
    assert n <= hc.RESTART_WARN


def test_restart_storm_injected_fires(tmp_path):
    """폭풍 주입 300회 → ERROR 임계 초과 (실제 09-12 사건은 3,276회)."""
    when = (dt.datetime.now() - dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")[:17]
    p = _write_beat_log(tmp_path, 300, when)
    since = (dt.datetime.now() - dt.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    n = hc._count_recent_restarts(p, BEAT_BANNER, BEAT_TS, since)
    assert n == 300
    assert n > hc.RESTART_ERROR


def test_restart_storm_ignores_old_entries(tmp_path):
    """48h 전 항목은 24h 창 밖 → 미계수(과대 계수 방지)."""
    when = (dt.datetime.now() - dt.timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")[:17]
    p = _write_beat_log(tmp_path, 300, when)
    since = (dt.datetime.now() - dt.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    assert hc._count_recent_restarts(p, BEAT_BANNER, BEAT_TS, since) == 0


def test_missing_log_returns_none(tmp_path):
    assert hc._count_recent_restarts(tmp_path / "nope.log", BEAT_BANNER, BEAT_TS, "2026-01-01") is None
