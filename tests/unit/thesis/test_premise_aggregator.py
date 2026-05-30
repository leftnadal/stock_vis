"""
PremiseAggregator 단위 테스트 (수학 모델 v2.3.2, Section 4)

검증 항목:
  - weakest_link: score < -0.5인 지표 감지
  - divergence: 양수/음수 혼재 비율 >= 0.3
  - thesis_bias_warning: 총 지표 5개 이상일 때만 편향 경고
"""

import pytest

from thesis.models import Thesis, ThesisIndicator, ThesisPremise
from thesis.services.premise_aggregator import (
    WEAKEST_LINK_THRESHOLD,
    aggregate_premise,
    aggregate_thesis,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_thesis(user):
    return Thesis.objects.create(
        user=user,
        title="Aggregator Test Thesis",
        direction="bullish",
        target="SPY",
        target_type="index",
        thesis_type="trend",
        entry_source="free_input",
    )


def _make_premise(thesis, content="테스트 전제", weight=1.0):
    return ThesisPremise.objects.create(
        thesis=thesis,
        content=content,
        category="macro",
        weight=weight,
    )


def _make_indicator(thesis, premise, name="Indicator", indicator_type="market_data", weight=1.0):
    return ThesisIndicator.objects.create(
        thesis=thesis,
        premise=premise,
        name=name,
        indicator_type=indicator_type,
        data_source="fmp",
        support_direction="positive",
        weight=weight,
    )


def _indicator_scores(*pairs):
    """(indicator, score) 쌍 목록 → {str(id): score} dict."""
    return {str(ind.id): score for ind, score in pairs}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWeakestLinkTrigger:
    def test_weakest_link_trigger(self, user):
        """
        score < -0.5인 지표가 존재하면 weakest_link가 채워진다.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        ind_ok = _make_indicator(thesis, premise, name="Normal Indicator")
        ind_weak = _make_indicator(thesis, premise, name="Weak Indicator")

        scores = _indicator_scores(
            (ind_ok, 0.3),
            (ind_weak, -0.6),  # WEAKEST_LINK_THRESHOLD(-0.5)보다 낮음
        )

        result = aggregate_premise(premise, scores)

        assert result["weakest_link"] is not None
        assert result["weakest_link"]["indicator_name"] == "Weak Indicator"
        assert result["weakest_link"]["score"] == pytest.approx(-0.6)

    def test_no_weakest_link_above_threshold(self, user):
        """
        모든 지표 score >= -0.5이면 weakest_link=None.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        ind_a = _make_indicator(thesis, premise, name="Indicator A")
        ind_b = _make_indicator(thesis, premise, name="Indicator B")

        scores = _indicator_scores(
            (ind_a, 0.4),
            (ind_b, -0.4),  # 임계값보다 크므로(= 덜 부정적이므로) 최약고리 아님
        )

        result = aggregate_premise(premise, scores)

        assert result["weakest_link"] is None


@pytest.mark.django_db
class TestDivergenceTrigger:
    def test_divergence_trigger(self, user):
        """
        양수 2개 + 음수 1개 (minority/total = 1/3 ≈ 0.33 >= 0.3) → divergence=True.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        ind_a = _make_indicator(thesis, premise, name="A")
        ind_b = _make_indicator(thesis, premise, name="B")
        ind_c = _make_indicator(thesis, premise, name="C")

        scores = _indicator_scores(
            (ind_a, 0.5),
            (ind_b, 0.3),
            (ind_c, -0.4),
        )

        result = aggregate_premise(premise, scores)

        assert result["divergence"] is True

    def test_no_divergence_all_same_sign(self, user):
        """
        모두 양수면 divergence=False.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        ind_a = _make_indicator(thesis, premise, name="A")
        ind_b = _make_indicator(thesis, premise, name="B")
        ind_c = _make_indicator(thesis, premise, name="C")

        scores = _indicator_scores(
            (ind_a, 0.5),
            (ind_b, 0.3),
            (ind_c, 0.1),
        )

        result = aggregate_premise(premise, scores)

        assert result["divergence"] is False

    def test_divergence_boundary_below_threshold(self, user):
        """
        minority/total < 0.3이면 divergence=False.

        양수 4개 + 음수 1개 → minority/total = 1/5 = 0.2 < 0.3.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        indicators = [_make_indicator(thesis, premise, name=f"Ind{i}") for i in range(5)]

        scores = {
            str(indicators[0].id): 0.5,
            str(indicators[1].id): 0.4,
            str(indicators[2].id): 0.3,
            str(indicators[3].id): 0.2,
            str(indicators[4].id): -0.3,  # minority 1 / total 5 = 0.2
        }

        result = aggregate_premise(premise, scores)

        assert result["divergence"] is False


@pytest.mark.django_db
class TestThesisBiasWarning:
    def test_thesis_bias_skips_below_5_indicators(self, user):
        """
        총 지표 4개이면 thesis_bias_warning=None (THESIS_BIAS_MIN_INDICATORS=5 미만).
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        # 동일 유형 지표 4개 (60% 이상이어도 총 < 5 → 경고 없음)
        for i in range(4):
            _make_indicator(thesis, premise, name=f"Market Ind {i}", indicator_type="market_data")

        premise_scores = {str(premise.id): 0.5}
        indicator_scores = {}  # aggregate_thesis 내부에서 직접 사용 안 함

        result = aggregate_thesis(thesis, premise_scores, indicator_scores)

        assert result["thesis_bias_warning"] is None

    def test_thesis_bias_warning_present_with_5_same_type(self, user):
        """
        총 지표 5개이고 동일 유형(market_data)이 5개(100%) → bias 경고 발생.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        for i in range(5):
            _make_indicator(thesis, premise, name=f"Market Ind {i}", indicator_type="market_data")

        premise_scores = {str(premise.id): 0.5}
        indicator_scores = {}

        result = aggregate_thesis(thesis, premise_scores, indicator_scores)

        assert result["thesis_bias_warning"] is not None
        assert result["thesis_bias_warning"]["type"] == "indicator_bias"
        assert "시장 데이터" in result["thesis_bias_warning"]["message"]

    def test_thesis_bias_not_triggered_when_mixed_types(self, user):
        """
        5개 지표가 여러 유형으로 분산(최대 비율 < 60%)되면 경고 없음.
        """
        thesis = _make_thesis(user)
        premise = _make_premise(thesis)

        type_cycle = ["market_data", "macro", "sentiment", "technical", "custom"]
        for i, itype in enumerate(type_cycle):
            _make_indicator(thesis, premise, name=f"Ind {i}", indicator_type=itype)

        premise_scores = {str(premise.id): 0.3}
        indicator_scores = {}

        result = aggregate_thesis(thesis, premise_scores, indicator_scores)

        assert result["thesis_bias_warning"] is None
