"""Slice 9 #43 / E1 — 회귀 분류 helper 검증.

지시서 §3.4 — 단위 테스트 7건.
"""

from __future__ import annotations

from portfolio.tests.helpers.regression_classifier import classify_regression


class TestRegressionClassifier:
    """git diff 경로 기반 회귀 분류."""

    def test_only_tests_is_no_cost(self) -> None:
        paths = [
            "portfolio/tests/slice9/test_foo.py",
            "portfolio/tests/helpers/bar.py",
        ]
        assert classify_regression(paths) == "no-cost"

    def test_only_docs_is_no_cost(self) -> None:
        paths = ["docs/portfolio/coach/slice9/note.md"]
        assert classify_regression(paths) == "no-cost"

    def test_only_llm_is_mixed(self) -> None:
        """llm/ 단독은 보수적으로 mixed 반환 (cost 또는 mixed 허용)."""
        paths = ["portfolio/llm/cost_guard.py"]
        result = classify_regression(paths)
        assert result in ("cost", "mixed")

    def test_llm_and_tests_is_mixed(self) -> None:
        paths = [
            "portfolio/llm/cost_guard.py",
            "portfolio/tests/slice9/test_cost_guard_cap.py",
        ]
        assert classify_regression(paths) == "mixed"

    def test_prompts_and_tests_is_mixed(self) -> None:
        paths = [
            "portfolio/prompts/e4/builder.py",
            "portfolio/tests/slice8/test_e4_prompt_builder.py",
        ]
        assert classify_regression(paths) == "mixed"

    def test_empty_paths_is_no_cost(self) -> None:
        assert classify_regression([]) == "no-cost"

    def test_slice8_part3_commits_classification(self) -> None:
        """Slice 8 Part 3 commit 5b37e12 시뮬레이션 — mixed로 분류되어야 함."""
        paths = [
            "portfolio/prompts/e4/builder.py",
            "portfolio/prompts/e4/samples.py",
            "portfolio/tests/slice8/helpers/specificity_count.py",
            "portfolio/tests/slice8/test_e4_prompt_builder.py",
            "portfolio/tests/slice8/test_specificity_patterns.py",
            "docs/portfolio/coach/slice8/specificity_patterns.md",
        ]
        assert classify_regression(paths) == "mixed"

    def test_data_prep_only_is_data_prep(self) -> None:
        """Slice 10 mini-slice: scripts/coach/ + tests/coach/ 단독 → data-prep."""
        paths = [
            "scripts/coach/dump_all_llm_calls.py",
            "tests/coach/test_dump_llm_calls.py",
        ]
        assert classify_regression(paths) == "data-prep"

    def test_measure_dir_is_mixed(self) -> None:
        """Slice 10: portfolio/measure/는 cost 카테고리 → mixed."""
        paths = [
            "portfolio/measure/estimator_v3.py",
            "tests/coach/test_estimator_v3.py",
        ]
        assert classify_regression(paths) == "mixed"
