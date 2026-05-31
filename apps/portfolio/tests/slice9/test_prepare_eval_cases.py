"""Slice 9 Part 2 §1.3 — prepare_eval_cases 단위 테스트.

지시서 §1.3 — 3건. 26 entries / 필수 필드 / manual slots null.
"""

from __future__ import annotations

import pytest

from scripts.slice9.prepare_eval_cases import build_cases

SAMPLE_JOINED = [
    {
        "case_id": "S01_haiku",
        "case_name": "S01",
        "original_model": "claude-haiku-4-5",
        "commentary": "현재 PE 15 이상으로 ...",
        "parsed": {
            "answer": "현재 PE 15 이상으로 ...",
            "action_items": [{"title": "T1", "description": "D1", "priority": "high"}],
        },
        "matrix_patterns_score": 4,
        "rationale_text": "4요소 중 3개 충족",
        "rationale_categories": ["data_grounding"],
        "rationale_score": 4,
        "rationale_specificity_detail": {"P1_metric_mention": True},
    },
    {
        "case_id": "S01_sonnet",
        "case_name": "S01",
        "original_model": "claude-sonnet-4-5",
        "commentary": "다른 답변",
        "parsed": {"answer": "다른 답변", "action_items": []},
        "matrix_patterns_score": 5,
        "rationale_text": "강함",
        "rationale_score": 5,
    },
]


class TestPrepareEvalCases:
    def test_cases_count_matches_input(self) -> None:
        """build_cases는 입력 entries 개수만큼 출력."""
        cases = build_cases(SAMPLE_JOINED)
        assert len(cases) == len(SAMPLE_JOINED)

    def test_required_fields_present(self) -> None:
        """필수 필드 모두 포함."""
        required = {
            "case_id",
            "case_name",
            "original_model",
            "question",
            "commentary",
            "action_items",
            "rationale_text",
            "rationale_score",
            "auto_specificity_score",
            "manual_naturalness",
            "manual_insight",
            "manual_comment",
        }
        cases = build_cases(SAMPLE_JOINED)
        for c in cases:
            assert required.issubset(c.keys())

    def test_manual_slots_initialized_null(self) -> None:
        """manual_naturalness, manual_insight 초기값 None / comment ''."""
        cases = build_cases(SAMPLE_JOINED)
        for c in cases:
            assert c["manual_naturalness"] is None
            assert c["manual_insight"] is None
            assert c["manual_comment"] == ""
