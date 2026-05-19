"""Slice 12 Part 1 Step 5 — PRESET_SCORERS dict + 5 adapter 검증.

Slice 11 Part 1 COMMENTARY_INPUT_CLASSES dict 패턴 미러.

테스트 항목:
1. 5 카테고리 모두 등록 (value/growth/income/factor/special)
2. 각 adapter ScoringEngineBase 상속 (parametrize × 5)
3. get_scorer가 인스턴스 반환 + category 일치 (parametrize × 5)
4. 잘못된 category → KeyError
5. 각 adapter score() NotImplementedError raise (Part 1 스켈레톤) (parametrize × 5)
6. 각 adapter required_metrics() NotImplementedError raise (parametrize × 5)
"""

from __future__ import annotations

import pytest

from portfolio.services.scoring import PRESET_SCORERS, get_scorer
from portfolio.services.scoring.base import ScoringEngineBase

CATEGORIES = ["value", "growth", "income", "factor", "special"]


def test_five_categories_registered():
    """5 카테고리 모두 PRESET_SCORERS에 등록."""
    assert set(PRESET_SCORERS.keys()) == set(CATEGORIES)


@pytest.mark.parametrize("category", CATEGORIES)
def test_each_scorer_inherits_base(category):
    """각 adapter는 ScoringEngineBase 상속."""
    cls = PRESET_SCORERS[category]
    assert issubclass(cls, ScoringEngineBase)


@pytest.mark.parametrize("category", CATEGORIES)
def test_get_scorer_returns_instance(category):
    """get_scorer가 인스턴스 반환 + category 일치."""
    scorer = get_scorer(category)
    assert isinstance(scorer, ScoringEngineBase)
    assert scorer.category == category


def test_invalid_category_raises_key_error():
    """미등록 category → KeyError."""
    with pytest.raises(KeyError):
        get_scorer("nonexistent")


@pytest.mark.parametrize("category", CATEGORIES)
def test_skeleton_score_raises_notimplemented(category):
    """Part 1 스켈레톤: score 호출 시 NotImplementedError (Part 2에서 풀 구현)."""
    scorer = get_scorer(category)
    with pytest.raises(NotImplementedError):
        scorer.score(None)


@pytest.mark.parametrize("category", CATEGORIES)
def test_skeleton_required_metrics_raises_notimplemented(category):
    """Part 1 스켈레톤: required_metrics 호출 시 NotImplementedError."""
    scorer = get_scorer(category)
    with pytest.raises(NotImplementedError):
        scorer.required_metrics()
