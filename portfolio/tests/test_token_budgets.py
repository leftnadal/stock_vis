"""token_budgets 단위 테스트 (Slice 3 Step 9, 백로그 #5)."""

from __future__ import annotations

import pytest

from portfolio.llm.token_budgets import (
    ENTRYPOINT_TOKEN_BUDGETS,
    estimate_input_tokens,
    get_token_budget,
)


def test_token_budgets_defined():
    """e1, e5, e2 budget 정의됨."""
    for ep in ("e1", "e5", "e2"):
        assert ep in ENTRYPOINT_TOKEN_BUDGETS
        assert ENTRYPOINT_TOKEN_BUDGETS[ep] > 0


def test_get_token_budget_known():
    assert get_token_budget("e1") == 5000
    assert get_token_budget("e5") == 2000
    assert get_token_budget("e2") == 1500


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
