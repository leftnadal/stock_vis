"""Slice 12 Part 1 Step 5 — ScoringEngineBase 단위 테스트.

Slice 11 Part 1 base class 검증 패턴 미러.

테스트 항목 (3건):
1. ScoringEngineBase abstract 직접 인스턴스화 불가
2. Pydantic config (frozen=True + extra=forbid) 검증
3. abstractmethod 등록 (score, required_metrics)
"""

from __future__ import annotations

import pytest

from portfolio.services.scoring.base import ScoringEngineBase


def test_abstract_cannot_instantiate():
    """ScoringEngineBase는 abstract → 직접 인스턴스화 시 TypeError."""
    with pytest.raises(TypeError):
        ScoringEngineBase()


def test_frozen_extra_forbid_config():
    """Pydantic config 검증 — frozen + extra=forbid."""
    assert ScoringEngineBase.model_config.get("frozen") is True
    assert ScoringEngineBase.model_config.get("extra") == "forbid"


def test_abstract_methods_defined():
    """abstract 메서드 등록 확인 — score / required_metrics."""
    assert "score" in ScoringEngineBase.__abstractmethods__
    assert "required_metrics" in ScoringEngineBase.__abstractmethods__
