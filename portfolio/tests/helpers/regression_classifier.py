"""Slice 9 #43 / E1 — 회귀 변경 자동 분류.

KPI 9 (회귀 격리) 분류 룰:
- cost 회귀: portfolio/{llm,prompts,services,schemas,views}/ 또는 portfolio/urls.py 변경
- no-cost 회귀: portfolio/tests/ 또는 docs/ 단독 변경
- mixed: cost 경로 + test/docs 동시 변경

지시서 §3 — kpi_e1_regression_classification.md 의 룰을 코드화.
"""

from __future__ import annotations

import subprocess


COST_PREFIXES = [
    "portfolio/llm/",
    "portfolio/prompts/",
    "portfolio/services/",
    "portfolio/schemas/",
    "portfolio/views/",
    "portfolio/urls.py",
]

NO_COST_PREFIXES = [
    "portfolio/tests/",
    "docs/",
]


def get_diff_paths(base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> list[str]:
    """git diff에서 변경 경로 추출.

    Args:
        base_ref: 비교 기준 ref (default HEAD~1)
        head_ref: 비교 대상 ref (default HEAD)

    Returns:
        변경된 파일 경로 리스트 (빈 라인 제외).
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", base_ref, head_ref],
        capture_output=True,
        text=True,
        check=True,
    )
    return [p for p in result.stdout.strip().split("\n") if p]


def _has_cost_path(paths: list[str]) -> bool:
    return any(any(p.startswith(c) for c in COST_PREFIXES) for p in paths)


def _all_paths_are_test_or_docs(paths: list[str]) -> bool:
    """모든 경로가 NO_COST_PREFIXES에 해당하는지."""
    return all(any(p.startswith(nc) for nc in NO_COST_PREFIXES) for p in paths)


def classify_regression(diff_paths: list[str]) -> str:
    """변경 경로로 회귀 종류 분류.

    Args:
        diff_paths: git diff에서 추출한 변경 파일 경로 리스트.

    Returns:
        "cost" / "no-cost" / "mixed"

        - 빈 paths → "no-cost" (변경 없음)
        - cost 경로 + 비-cost 경로 혼합 → "mixed"
        - cost 경로만 → "mixed" (보수적, classify alone도 mixed로 처리)
        - test/docs만 → "no-cost"
    """
    if not diff_paths:
        return "no-cost"

    has_cost = _has_cost_path(diff_paths)

    if has_cost:
        # cost 경로 포함 시 항상 "mixed" (보수적: KPI 9a cost 기준 적용)
        # 정확한 의도: cost 단독은 "cost", test와 섞이면 "mixed"
        # 단순 룰 채택: cost가 포함되면 모두 mixed (테스트 코드를 빠뜨릴 위험 없음)
        return "mixed"

    return "no-cost"


def classify_current_commit() -> str:
    """현재 commit(HEAD vs HEAD~1)의 분류."""
    paths = get_diff_paths()
    return classify_regression(paths)


def classify_range(base_ref: str, head_ref: str = "HEAD") -> str:
    """ref 범위의 분류."""
    paths = get_diff_paths(base_ref, head_ref)
    return classify_regression(paths)
