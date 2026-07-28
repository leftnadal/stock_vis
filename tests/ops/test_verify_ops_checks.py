"""OPS-WORKTREE-ISOLATION Phase 3 — verify section D 순수 점검 함수 테스트 (django 무의존).

각 항목의 정상/ALERT/skip 분기를 mock 입력으로. verify 코어 무영향(WARN 상한) 계약 검증.
실행: pytest tests/ops/test_verify_ops_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "lib"))
import ops_verify_checks as ovc  # noqa: E402


class TestWorkerTreeDrift:
    def test_tip_match_ok(self):
        assert ovc.check_worker_tree_drift("abc123", "abc123", True)[0] == "ok"

    def test_behind_but_ancestor_is_info_not_warn(self):
        # 정상 lag(main 상시 전진) — 오탐 방지 핵심
        sev, msg = ovc.check_worker_tree_drift("aaa", "bbb", True)
        assert sev == "info" and "정상 lag" in msg

    def test_diverged_is_warn(self):
        sev, msg = ovc.check_worker_tree_drift("aaa", "bbb", False)
        assert sev == "warn" and "diverged" in msg

    def test_unknown_is_skip(self):
        assert ovc.check_worker_tree_drift(None, "bbb", None)[0] == "skip"
        assert ovc.check_worker_tree_drift("aaa", None, None)[0] == "skip"


class TestStaleMarkers:
    def test_none_ok(self):
        assert ovc.check_stale_markers([])[0] == "ok"

    def test_stale_warn(self):
        sev, msg = ovc.check_stale_markers([("/x/sv-foo", 25)])
        assert sev == "warn" and "sv-foo" in msg

    def test_scan_fail_skip(self):
        assert ovc.check_stale_markers(None)[0] == "skip"


class TestCodeVersion:
    def test_process_newer_ok(self):
        # 워커 기동(200) > HEAD 커밋(100) = 최신 코드 서빙
        assert ovc.check_code_version(200, 100)[0] == "ok"

    def test_head_newer_warn(self):
        # HEAD 커밋(200) > 워커 기동(100) = 헌 코드 서빙(재기동 누락)
        sev, msg = ovc.check_code_version(100, 200)
        assert sev == "warn" and "재기동 누락" in msg

    def test_unknown_skip(self):
        assert ovc.check_code_version(None, 200)[0] == "skip"
        assert ovc.check_code_version(100, None)[0] == "skip"


class TestContract:
    def test_no_warn_never_fail(self):
        # 계약: section D는 FAIL을 만들지 않는다 — severity에 "fail" 없음
        for sev, _ in [
            ovc.check_worker_tree_drift("a", "b", False),
            ovc.check_stale_markers([("/x", 99)]),
            ovc.check_code_version(1, 2),
        ]:
            assert sev in ("ok", "info", "warn", "skip")

    def test_run_all_shape(self):
        # run_all은 라이브 I/O이나 예외 없이 3튜플 리스트 반환(각 (sev,msg))
        res = ovc.run_all(2_000_000_000)
        assert len(res) == 3
        assert all(len(t) == 2 and t[0] in ("ok", "info", "warn", "skip") for t in res)
