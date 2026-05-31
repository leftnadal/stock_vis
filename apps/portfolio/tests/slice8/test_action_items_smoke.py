"""ActionItem이 진입점 fixture에 자연 통합되는지 smoke 검증 (Slice 8 Part 2 Step 3, #28).

지시서 Step 3: backward-compat fixture 호환 케이스를 E3PortfolioCommentary 본체로 검증.
Part 1 fixture (e3_concentrated_v2.json)는 MetricResult 리스트라 별도 형태 (관련 검증은
test_input_v2_smoke.py에서 처리). 본 smoke는 E3PortfolioCommentary 본체 + action_items
슬롯 자체에 집중.
"""

import json
from pathlib import Path

from portfolio.schemas.llm_outputs import E3PortfolioCommentary

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestActionItemsSmoke:
    def test_e3_with_action_items_loads(self):
        """ActionItem 채워진 fixture가 정상 로딩 + 2건 검증."""
        path = FIXTURE_DIR / "e3_concentrated_v2_with_actions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        obj = E3PortfolioCommentary.model_validate(data)
        assert len(obj.action_items) == 2
        assert obj.action_items[0].priority == "high"
        assert obj.action_items[0].category == "rebalance"
        assert obj.action_items[1].priority == "medium"
        assert obj.action_items[1].category == "research"

    def test_e3_empty_action_items_backward_compat(self):
        """action_items 누락된 fixture가 default [] 로 로딩 (backward-compat 핵심)."""
        path = FIXTURE_DIR / "e3_no_actions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        # fixture에 action_items 키 자체가 없음
        assert "action_items" not in data
        obj = E3PortfolioCommentary.model_validate(data)
        # default_factory=list로 빈 리스트 초기화
        assert obj.action_items == []

    def test_action_items_serialization_roundtrip(self):
        """ActionItem 포함된 schema의 직렬화 round-trip."""
        path = FIXTURE_DIR / "e3_concentrated_v2_with_actions.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        obj = E3PortfolioCommentary.model_validate(original)
        dumped = obj.model_dump(mode="json")
        # round-trip 후 action_items 보존
        assert len(dumped["action_items"]) == 2
        assert (
            dumped["action_items"][0]["title"] == original["action_items"][0]["title"]
        )
        assert dumped["action_items"][0]["priority"] == "high"
        assert dumped["action_items"][1]["category"] == "research"

    def test_action_items_validation_caught_at_load(self):
        """잘못된 action_items 값(priority enum 위반)이 load 시점에 ValidationError."""
        from pydantic import ValidationError

        invalid_data = {
            "holistic_assessment": "x" * 50,
            "diversification_comment": "y" * 30,
            "sector_balance_comment": "z" * 30,
            "risk_concentration_comment": "w" * 30,
            "preset_alignment": "aligned",
            "confidence": 3,
            "action_items": [
                {
                    "title": "유효 제목",
                    "description": "x" * 20,
                    "priority": "urgent",  # invalid Literal 값
                }
            ],
        }
        import pytest

        with pytest.raises(ValidationError):
            E3PortfolioCommentary.model_validate(invalid_data)
