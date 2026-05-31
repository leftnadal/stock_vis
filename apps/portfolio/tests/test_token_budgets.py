"""token_budgets 단위 테스트 (Slice 3 Step 9, 백로그 #5)."""

from __future__ import annotations

import pytest

from apps.portfolio.llm.token_budgets import (
    ENTRYPOINT_TOKEN_BUDGETS,
    estimate_input_tokens,
    get_token_budget,
)


def test_token_budgets_defined():
    """e1, e5, e2, e6 budget 정의됨."""
    for ep in ("e1", "e5", "e2", "e6"):
        assert ep in ENTRYPOINT_TOKEN_BUDGETS
        assert ENTRYPOINT_TOKEN_BUDGETS[ep] > 0


def test_get_token_budget_known():
    assert get_token_budget("e1") == 5000
    assert get_token_budget("e5") == 2000
    assert get_token_budget("e2") == 1500
    assert get_token_budget("e6") == 1500


def test_get_token_budget_unknown():
    with pytest.raises(ValueError, match="Unknown entrypoint"):
        get_token_budget("e99_nonexistent")


def test_estimate_input_tokens_heuristic():
    """3 char ≈ 1 token 휴리스틱."""
    assert estimate_input_tokens("") == 0
    assert estimate_input_tokens("abc") == 1
    assert estimate_input_tokens("abcdef") == 2
    # 한국어 (4자 = 12 bytes UTF-8이지만 char 단위로 추정)
    assert estimate_input_tokens("가나다") == 1


def test_e6_budget_registered():
    """Slice 4 Step 7 — e6 budget 등록."""
    assert "e6" in ENTRYPOINT_TOKEN_BUDGETS
    budget = get_token_budget("e6")
    assert budget >= 500  # round-up 500 단위 최소
    assert budget <= 5000  # e1보다 크지 않음 (E6는 분석 엔진 의존성 회피로 가벼움)


def test_e6_budget_smaller_than_e1():
    """E6는 분석 엔진 의존 없어 e1보다 작아야 함 (입력 평탄화 가벼움)."""
    assert get_token_budget("e6") < get_token_budget("e1")


def test_token_budgets_full_dict():
    """ENTRYPOINT_TOKEN_BUDGETS dict가 5 진입점 (e1/e5/e2/e6/e3) 모두 등록."""
    assert {"e1", "e5", "e2", "e6", "e3"}.issubset(set(ENTRYPOINT_TOKEN_BUDGETS.keys()))


# ============================================================
# Slice 5 Step 7 — e3 budget 단위 테스트 +3건
# ============================================================


def test_e3_budget_registered():
    """Slice 5 Step 7 — e3 budget 등록 (AnalysisContext 전체 직렬화 반영)."""
    assert "e3" in ENTRYPOINT_TOKEN_BUDGETS
    budget = get_token_budget("e3")
    assert budget > 0


def test_e3_budget_round_up_500():
    """Slice 5 Step 7 — e3 budget round-up 500 단위 (P90 × 1.5 결정 규칙)."""
    budget = get_token_budget("e3")
    assert budget % 500 == 0


def test_e3_budget_within_estimate_range():
    """Slice 5 Step 7 — e3 budget 합리적 범위 (실측 P90×1.5 round-up 기반).

    Q3 1차 추정 1500 대비 +366% 갱신 (AnalysisContext 전체 직렬화 영향).
    Step 7 측정: P90=4359 × 1.5 = 6538.5 → round-up 500 = 7000.
    측정값 변동 허용 마진: 4000 ≤ budget ≤ 10000.
    """
    budget = get_token_budget("e3")
    assert 4000 <= budget <= 10000
