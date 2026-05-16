"""ActionItem schema 검증 (Slice 8 Part 2 Step 1, #28)."""

import pytest
from pydantic import ValidationError

from portfolio.schemas.commentary_output import ActionItem


class TestActionItemSchema:
    def test_minimal_valid_action_item(self):
        """필수 필드만 채워진 정상 케이스."""
        item = ActionItem(
            title="현금 비중 축소",
            description="포트폴리오 현금 비중이 25%로 과도하여 축소 검토.",
        )
        assert item.title == "현금 비중 축소"
        assert item.priority == "medium"  # default
        assert item.category is None  # default

    def test_full_action_item(self):
        """모든 필드 채워진 케이스."""
        item = ActionItem(
            title="섹터 분산 개선",
            description="IT 섹터 비중 60%, 금융 5%로 편중. 금융/소비재 추가 검토.",
            priority="high",
            category="rebalance",
        )
        assert item.priority == "high"
        assert item.category == "rebalance"

    def test_title_too_short(self):
        """title이 빈 문자열이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(title="", description="x" * 20)

    def test_title_too_long(self):
        """title이 80자 초과면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(title="a" * 81, description="x" * 20)

    def test_description_too_short(self):
        """description이 10자 미만이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(title="t", description="짧음")

    def test_invalid_priority(self):
        """priority가 허용되지 않은 값이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(
                title="t",
                description="x" * 20,
                priority="urgent",  # type: ignore
            )

    def test_invalid_category(self):
        """category가 허용되지 않은 값이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(
                title="t",
                description="x" * 20,
                category="invalid",  # type: ignore
            )
