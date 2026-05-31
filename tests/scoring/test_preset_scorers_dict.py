"""Slice 12 Part 1+2 — PRESET_SCORERS dict + 5 adapter 통합 검증.

Slice 11 Part 1 COMMENTARY_INPUT_CLASSES dict 패턴 미러.

테스트 항목 (Part 2 풀 구현 반영):
1. 5 카테고리 모두 등록
2. 각 adapter ScoringEngineBase 상속 (parametrize × 5)
3. get_scorer가 인스턴스 반환 + category 일치 (parametrize × 5)
4. 잘못된 category → KeyError
5. 각 adapter score() 빈 metrics dict → dict 반환 + `_category_score` 포함 (parametrize × 5)
6. 각 adapter required_metrics() 1개 이상 반환 (parametrize × 5)
"""

from __future__ import annotations

import pytest

from apps.portfolio.services.scoring import PRESET_SCORERS, get_scorer
from apps.portfolio.services.scoring.base import ScoringEngineBase

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
def test_score_returns_dict_with_category_score(category):
    """Part 2 풀: 빈 metrics 입력 시 dict 반환 + `_category_score` key 포함."""
    scorer = get_scorer(category)
    out = scorer.score({})
    assert isinstance(out, dict)
    assert "_category_score" in out
    # 빈 metrics에서는 모든 preset score가 0 또는 gate 처리됨
    assert 0.0 <= out["_category_score"] <= 100.0


@pytest.mark.parametrize("category", CATEGORIES)
def test_required_metrics_nonempty(category):
    """Part 2 풀: required_metrics는 1개 이상의 지표 키 반환."""
    scorer = get_scorer(category)
    metrics = scorer.required_metrics()
    assert isinstance(metrics, list)
    assert len(metrics) >= 1
    assert all(isinstance(m, str) and m for m in metrics)
