"""AGENT-SHOT-1 온디맨드 캡처 드라이버 단위 테스트 (브라우저 없음).

build_screens(경로/목록/오류) · _safe · screen_text · write_outputs(meta·텍스트).
run_render(Playwright)는 통합 실행에서 검증 — 여기서는 순수 로직만.
"""

from __future__ import annotations

import json

import pytest

from auto_agent_system.dogfood import shot


class TestBuildScreens:
    def test_path_single_screen(self):
        screens = shot.build_screens("/monitor/abc-123", None)
        assert len(screens) == 1
        assert screens[0]["route"] == "/monitor/abc-123"
        assert screens[0]["id"].startswith("adhoc_")
        assert screens[0]["anchors"] == []

    def test_path_must_start_with_slash(self):
        with pytest.raises(SystemExit):
            shot.build_screens("monitor/abc", None)

    def test_screens_filter_by_id(self, monkeypatch):
        class G:
            def __init__(self, i):
                self.id, self.route, self.title, self.anchors = i, f"/{i}", i.upper(), ["a"]

        monkeypatch.setattr(shot, "load_guide_targets", lambda: [G("home"), G("monitor"), G("news")])
        screens = shot.build_screens(None, "home,news")
        assert {s["id"] for s in screens} == {"home", "news"}

    def test_unknown_screen_id_errors(self, monkeypatch):
        class G:
            def __init__(self, i):
                self.id, self.route, self.title, self.anchors = i, f"/{i}", i, []

        monkeypatch.setattr(shot, "load_guide_targets", lambda: [G("home")])
        with pytest.raises(SystemExit):
            shot.build_screens(None, "home,ghost")

    def test_requires_path_or_screens(self):
        with pytest.raises(SystemExit):
            shot.build_screens(None, None)


class TestHelpers:
    def test_safe_sanitizes(self):
        assert shot._safe("/monitor/a b!c") == "monitor_a_b_c"
        assert shot._safe("") == "screen"

    def test_screen_text_prefers_regions(self):
        s = {"regions": [{"text": "hello"}, {"text": "world"}], "fallback_text": "fb"}
        assert shot.screen_text(s) == "hello world"

    def test_screen_text_fallback(self):
        s = {"regions": [{"text": ""}], "fallback_text": "본문 텍스트"}
        assert shot.screen_text(s) == "본문 텍스트"


class TestWriteOutputs:
    def test_meta_and_text_written(self, tmp_path):
        raw = {
            "base_url": "http://localhost:3000",
            "authenticated": True,
            "auth_fail_reason": "",
            "screens": [
                {
                    "id": "adhoc_x",
                    "route": "/monitor/x",
                    "ok": True,
                    "screenshot": str(tmp_path / "adhoc_x.png"),
                    "regions": [{"text": "IONQ 상세"}],
                    "fallback_text": "",
                }
            ],
        }
        meta = shot.write_outputs(tmp_path, raw)
        assert meta["authenticated"] is True
        assert meta["screens"][0]["url"] == "http://localhost:3000/monitor/x"
        assert (tmp_path / "adhoc_x.txt").read_text(encoding="utf-8") == "IONQ 상세"
        on_disk = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
        assert on_disk["screens"][0]["id"] == "adhoc_x"
        assert "web_tree_hash" in on_disk
