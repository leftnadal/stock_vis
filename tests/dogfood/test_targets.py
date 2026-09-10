"""AGENT-S1 — 점검 대상은 가이드 데이터(루브릭 단일 출처)에서 온다."""
from pathlib import Path

import pytest

from auto_agent_system.dogfood import targets


def test_guide_targets_are_loaded_from_guide_data():
    rows = targets.load_guide_targets()
    routes = {g.route for g in rows}
    # /chainsight/events = GUIDE-CS-GUARD-1 임시 이설(정문이 이야기 피드로 바뀌어 문구가
    # 어긋났다). 정문 /chainsight는 EXTRA_ROUTES로 정량 관측만 계속한다.
    assert routes == {
        "/",
        "/market-pulse-v2",
        "/market-pulse-v2/macro",
        "/chainsight/events",
        "/monitor",
        "/portfolio",
    }


def test_route_is_the_screen_route_not_next_action():
    """nextAction 안의 `route:`가 화면 route를 덮어쓰면 안 된다(first-wins)."""
    by_id = {g.id: g for g in targets.load_guide_targets()}
    assert by_id["dashboard.main"].route == "/"
    assert by_id["marketPulse.main"].route == "/market-pulse-v2"
    # 임시 이설 후에도 화면 자신의 route를 읽는다(nextAction의 /monitor가 아니라).
    assert by_id["chainsight.main"].route == "/chainsight/events"


def test_every_screen_declares_anchors_and_has_parsed_review_status():
    """draft 화면도 등재될 수 있다(검수 전). 채점 대상 선별은 rubric_targets가 한다.

    여기서 잡는 것은 `unknown` — reviewStatus 파싱이 깨져 draft/confirmed 구분이
    통째로 사라지는 경우다(그때 draft 문안이 루브릭에 섞여 들어간다).
    """
    for g in targets.load_guide_targets():
        assert g.anchors, f"{g.id}: 앵커 0건"
        assert g.review_status in {"draft", "confirmed"}, f"{g.id}: {g.review_status}"


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
    # 정문은 가이드가 이설돼도 정량 관측 대상으로 남는다(관측이 회귀로 사라지는 것을 막는다).
    assert "/chainsight" in routes
