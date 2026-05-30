"""Slice 5 Part 2 Step 9 — _prompt_helpers 단위 테스트.

format_metrics_to_str 일반화 (#11) + format_metrics_table deprecated wrapper 회귀 검증.
"""

from __future__ import annotations

import json

import pytest

from portfolio.services._prompt_helpers import (
    format_metrics_table,
    format_metrics_to_str,
)

# ============================================================
# format_metrics_to_str — 일반화 (Slice 5 Part 2 Step 9 #11)
# ============================================================


class TestFormatMetricsToStrMarkdown:
    """markdown 형식 — 기존 format_metrics_table과 동일 출력 보장."""

    def test_dict_input_to_markdown_table(self):
        """dict 입력 → markdown 표 출력."""
        metrics = {"P/E": 12.5, "ROE": 0.18}
        result = format_metrics_to_str(metrics, format="markdown")

        assert "| Metric | Value |" in result
        assert "|---|---|" in result
        assert "| P/E | 12.5000 |" in result
        assert "| ROE | 0.1800 |" in result

    def test_markdown_default_format(self):
        """format 인자 미지정 시 markdown 기본."""
        metrics = {"PEG": 1.5}
        assert format_metrics_to_str(metrics) == format_metrics_to_str(
            metrics, format="markdown"
        )

    def test_markdown_identical_to_legacy_format_metrics_table(self):
        """기존 format_metrics_table과 동일 출력 보장 (회귀 KPI)."""
        metrics = {
            "P/E": 12.5,
            "ROE": 0.18,
            "growth": {"value": 0.25, "tag": "high"},
        }
        legacy = format_metrics_table(metrics)
        new = format_metrics_to_str(metrics, format="markdown")
        assert legacy == new


class TestFormatMetricsToStrJson:
    """json 형식 — E3 builder 호출 패턴 (list[dict] / nested)."""

    def test_list_dict_input_to_indented_json(self):
        """list[dict] 입력 → indented JSON 출력."""
        data = [
            {"metric_id": "PEG", "level_tag": "weak"},
            {"metric_id": "ROIC", "level_tag": "top"},
        ]
        result = format_metrics_to_str(data, format="json")

        # round-trip 검증
        parsed = json.loads(result)
        assert parsed == data

        # indent=2 형식 확인
        assert "\n  " in result  # indented

    def test_json_korean_ensure_ascii_false(self):
        """한국어 ensure_ascii=False — 한글 그대로 직렬화."""
        data = {"태그": "최상위"}
        result = format_metrics_to_str(data, format="json")

        assert "태그" in result
        assert "최상위" in result
        # ASCII escape 미적용 확인
        assert "\\u" not in result


class TestFormatMetricsToStrEmpty:
    """빈 입력 / 미지원 형식 / 미지원 타입 처리."""

    def test_empty_dict_markdown_returns_placeholder(self):
        """빈 dict → '(지표 데이터 없음)' (markdown)."""
        assert format_metrics_to_str({}, format="markdown") == "(지표 데이터 없음)"

    def test_empty_list_json_returns_empty_array(self):
        """빈 list → '[]' (json)."""
        assert format_metrics_to_str([], format="json") == "[]"

    def test_unknown_format_raises_value_error(self):
        """미등록 format → ValueError (방어 검증)."""
        with pytest.raises(ValueError, match="Unknown format"):
            format_metrics_to_str({"x": 1}, format="yaml")  # type: ignore[arg-type]


# ============================================================
# format_metrics_table — deprecated wrapper 회귀 검증
# ============================================================


class TestFormatMetricsTableDeprecated:
    """기존 format_metrics_table 호환성 보존 (백로그 #21로 Slice 6+ 제거 검토)."""

    def test_legacy_basic_dict(self):
        metrics = {"P/E": 10.0}
        result = format_metrics_table(metrics)
        assert "| P/E | 10.0000 |" in result

    def test_legacy_empty_dict_unchanged(self):
        assert format_metrics_table({}) == "(지표 데이터 없음)"
