"""AGENT-S1 — 점검 대상은 가이드 데이터(루브릭 단일 출처)에서 온다."""
from pathlib import Path

import pytest

from auto_agent_system.dogfood import targets


def test_guide_targets_are_loaded_from_guide_data():
    rows = targets.load_guide_targets()
    routes = {g.route for g in rows}
    assert routes == {"/", "/market-pulse-v2", "/chainsight", "/monitor", "/portfolio"}


def test_route_is_the_screen_route_not_next_action():
    """nextAction 안의 `route:`가 화면 route를 덮어쓰면 안 된다(first-wins)."""
    by_id = {g.id: g for g in targets.load_guide_targets()}
    assert by_id["dashboard.main"].route == "/"
    assert by_id["marketPulse.main"].route == "/market-pulse-v2"
    assert by_id["chainsight.main"].route == "/chainsight"


def test_every_screen_declares_anchors_and_is_confirmed():
    for g in targets.load_guide_targets():
        assert g.anchors, f"{g.id}: 앵커 0건"
        assert g.review_status == "confirmed", f"{g.id}: {g.review_status}"


def test_empty_guide_dir_raises_instead_of_silently_returning_nothing(tmp_path: Path):
    """형식이 바뀌어 0건이 되면 조용히 통과하지 말고 터져야 한다."""
    with pytest.raises(RuntimeError):
        targets.load_guide_targets(tmp_path)


def test_error_markers_have_no_short_tokens():
    """'500' 같은 부분 토큰은 tailwind 클래스·티커에 걸려 전건 오탐을 만든다."""
    for marker in targets.ERROR_MARKERS:
        assert len(marker) >= 12, f"너무 짧은 마커: {marker!r}"


def test_all_route_targets_includes_guide_hub_and_login():
    routes = {r for _, r, _ in targets.all_route_targets()}
    assert "/guide" in routes
    assert "/login" in routes
