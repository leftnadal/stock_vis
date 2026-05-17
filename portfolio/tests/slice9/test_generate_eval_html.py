"""Slice 9 Part 2 §2.4 — HTML 평가 페이지 생성 검증.

지시서 §2.4 — 7건. HTML 파일 생성 + cases embed + 라디오/Export 버튼 + escape.
"""

from __future__ import annotations

import pytest

from scripts.slice9.generate_eval_html import generate_html


@pytest.fixture
def sample_cases() -> list[dict]:
    return [
        {
            "case_id": "S01_haiku",
            "case_name": "test_scenario",
            "original_model": "claude-haiku-4-5",
            "question": "테스트 질문",
            "commentary": "테스트 답변",
            "action_items": [
                {"title": "A", "description": "B", "priority": "high"}
            ],
            "rationale_text": "테스트 rationale",
            "rationale_categories": ["data_grounding"],
            "rationale_score": 4,
            "auto_specificity_score": 5,
            "auto_specificity_detail": {},
            "manual_naturalness": None,
            "manual_insight": None,
            "manual_comment": "",
        }
    ]


class TestGenerateEvalHtml:
    def test_html_file_created(self, tmp_path, sample_cases) -> None:
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        assert output.exists()

    def test_html_contains_cases_data(self, tmp_path, sample_cases) -> None:
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert "S01_haiku" in content
        assert "테스트 질문" in content
        assert "테스트 답변" in content

    def test_html_includes_naturalness_radio(self, tmp_path, sample_cases) -> None:
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert "Naturalness" in content
        assert 'name="naturalness"' in content

    def test_html_includes_insight_radio(self, tmp_path, sample_cases) -> None:
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert "Insight" in content
        assert 'name="insight"' in content

    def test_html_includes_export_button(self, tmp_path, sample_cases) -> None:
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert 'id="export-btn"' in content
        assert "Export to JSON" in content

    def test_html_includes_progress_bar(self, tmp_path, sample_cases) -> None:
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert 'id="progress-bar"' in content

    def test_html_includes_escape_function(self, tmp_path) -> None:
        """XSS 방지 — JS escapeHtml 정의 존재."""
        cases = [
            {
                "case_id": "S99",
                "case_name": "<script>alert(1)</script>",
                "original_model": "test",
                "question": "<img onerror=alert(1)>",
                "commentary": "<svg/onload=alert(1)>",
                "action_items": [],
                "rationale_text": "",
                "rationale_categories": [],
                "rationale_score": 0,
                "auto_specificity_score": 0,
                "auto_specificity_detail": {},
                "manual_naturalness": None,
                "manual_insight": None,
                "manual_comment": "",
            }
        ]
        output = tmp_path / "eval.html"
        generate_html(cases, output)
        content = output.read_text(encoding="utf-8")
        # escapeHtml 함수 정의 (런타임 escape)
        assert "function escapeHtml" in content
        # </script>는 split 처리되어 inline JSON 토큰 안에 raw로 안 나타남
        # (case_name "<script>alert(1)</script>"는 <\/script>로 변환됨)
        # cases_json 영역에서 </script>가 그대로 출현하지 않아야 함
        # (단, HTML 본문의 </script> 끝 태그는 1회 정상 존재)
        assert content.count("</script>") == 1  # 끝 태그 단 1회
