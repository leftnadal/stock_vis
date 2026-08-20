"""runtime_check.py 순수 판정 로직 단위 테스트 (RB-1 / D-RB-1).

고아·드리프트·정상 fixture로 판정을 고정한다. IO(subprocess)는 대상 아님 —
순수 함수만 검증(판정 로직 회귀 방지).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.runtime_check import (
    ERROR,
    OK,
    WARN,
    classify_drift,
    classify_launchd,
    classify_orphan,
    drift_age_from_history,
)


# ── ⑴ 고아 스윕 ──────────────────────────────────────────────────────────
class TestClassifyOrphan:
    def test_port_none_비대상(self):
        st, _ = classify_orphan(port=None, listener_pid=None, launchd_pid=100, listener_is_descendant_of_launchd=False)
        assert st == OK

    def test_리스너_없음_다운은_launchd검사_담당(self):
        st, _ = classify_orphan(port=3000, listener_pid=None, launchd_pid=100, listener_is_descendant_of_launchd=False)
        assert st == OK

    def test_리스너가_launchd_pid_자신_정상(self):
        # exec daphne: 리스너 pid == launchd pid
        st, _ = classify_orphan(port=18765, listener_pid=8083, launchd_pid=8083, listener_is_descendant_of_launchd=False)
        assert st == OK

    def test_리스너가_launchd_자손_정상(self):
        # npm 부모 → next 자식: 리스너는 launchd pid의 자손
        st, _ = classify_orphan(port=3000, listener_pid=31188, launchd_pid=31170, listener_is_descendant_of_launchd=True)
        assert st == OK

    def test_관리이탈_고아_포트점유_ORPHAN(self):
        # 고아(ppid→1, launchd 관리 밖)가 포트 점유 — 스테일 런타임 근인
        st, detail = classify_orphan(port=18765, listener_pid=63228, launchd_pid=8083, listener_is_descendant_of_launchd=False)
        assert st == ERROR
        assert "ORPHAN" in detail


# ── ⑵ 드리프트 ───────────────────────────────────────────────────────────
class TestClassifyDrift:
    def test_정합_behind0_OK(self):
        st, _ = classify_drift(behind=0, drift_age_hours=None)
        assert st == OK

    def test_최초감지_behind양수_age없음_OK(self):
        st, detail = classify_drift(behind=3, drift_age_hours=None)
        assert st == OK
        assert "DRIFT" in detail

    def test_24h_미만_지속_OK_활성세션정상(self):
        st, _ = classify_drift(behind=5, drift_age_hours=6.0)
        assert st == OK

    def test_24h_이상_지속_WARN(self):
        st, detail = classify_drift(behind=5, drift_age_hours=30.0)
        assert st == WARN
        assert "동기 필요" in detail

    def test_경계_정확히_24h_WARN(self):
        st, _ = classify_drift(behind=1, drift_age_hours=24.0)
        assert st == WARN


# ── ⑶ launchd 상태 ───────────────────────────────────────────────────────
class TestClassifyLaunchd:
    def test_미로드_ERROR(self):
        st, _ = classify_launchd(loaded=False, has_pid=False)
        assert st == ERROR

    def test_로드_미구동_WARN(self):
        st, _ = classify_launchd(loaded=True, has_pid=False)
        assert st == WARN

    def test_로드_구동_OK(self):
        st, _ = classify_launchd(loaded=True, has_pid=True)
        assert st == OK


# ── 드리프트 지속시간 산출 (로그 이력 파싱 로직) ──────────────────────────
class TestDriftAgeFromHistory:
    NOW = datetime(2026, 8, 21, 12, 0, 0, tzinfo=timezone.utc)

    def test_이력없음_None(self):
        assert drift_age_from_history([], self.NOW) is None

    def test_현재_정합_None(self):
        hist = [((self.NOW - timedelta(hours=5)).isoformat(), 3), (self.NOW.isoformat(), 0)]
        assert drift_age_from_history(hist, self.NOW) is None

    def test_연속_드리프트_시작시점부터_계산(self):
        start = self.NOW - timedelta(hours=30)
        hist = [
            (start.isoformat(), 2),
            ((self.NOW - timedelta(hours=10)).isoformat(), 4),
            (self.NOW.isoformat(), 5),
        ]
        age = drift_age_from_history(hist, self.NOW)
        assert age is not None and abs(age - 30.0) < 0.1

    def test_중간_정합이_구간_리셋(self):
        # behind==0이 중간에 있으면 그 이후부터만 센다
        hist = [
            ((self.NOW - timedelta(hours=40)).isoformat(), 3),  # 옛 드리프트
            ((self.NOW - timedelta(hours=20)).isoformat(), 0),  # 정합(리셋)
            ((self.NOW - timedelta(hours=5)).isoformat(), 2),   # 새 드리프트 시작
            (self.NOW.isoformat(), 2),
        ]
        age = drift_age_from_history(hist, self.NOW)
        assert age is not None and abs(age - 5.0) < 0.1

    def test_최근_드리프트_24h경계_WARN_통합(self):
        # drift_age >= 24h → classify_drift가 WARN 내는지 통합 확인
        start = self.NOW - timedelta(hours=25)
        hist = [(start.isoformat(), 1), (self.NOW.isoformat(), 1)]
        age = drift_age_from_history(hist, self.NOW)
        st, _ = classify_drift(1, age)
        assert st == WARN
