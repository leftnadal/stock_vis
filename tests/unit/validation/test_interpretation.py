"""
interpretation 단위 테스트

테스트 대상 (순수 함수, DB 불필요):
  - generate_summary_text() — 종합 한줄 요약
  - generate_metric_interpretation() — 개별 지표 해석
  - determine_trend() — 3년 추세 판정
  - generate_leader_summary() — 업종 리더 비교 요약
"""

from types import SimpleNamespace

import pytest

from validation.services.interpretation import (
    determine_trend,
    generate_leader_summary,
    generate_metric_interpretation,
    generate_summary_text,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(category, signal, score=50.0):
    """CategorySignal mock."""
    return SimpleNamespace(category=category, signal=signal, score=score)


# ---------------------------------------------------------------------------
# Tests: generate_summary_text
# ---------------------------------------------------------------------------


class TestGenerateSummaryText:
    def test_two_greens(self):
        """green 2개 이상 → '높은 X과(와) Y' 포함."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'green', 70),
            _make_signal('valuation', 'yellow', 50),
        ]
        text = generate_summary_text(signals)
        assert '수익성' in text or '성장성' in text

    def test_single_green(self):
        """green 1개 → '이(가) 강점'."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'yellow', 50),
        ]
        text = generate_summary_text(signals)
        assert '강점' in text

    def test_red_warning(self):
        """red 존재 → '주의 필요' 포함."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('financial_structure', 'red', 20),
        ]
        text = generate_summary_text(signals)
        assert '주의 필요' in text

    def test_all_greens(self):
        """green >= 5 → '전반적으로 양호' 포함."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'green', 75),
            _make_signal('financial_structure', 'green', 70),
            _make_signal('cash_flow_quality', 'green', 65),
            _make_signal('operational_efficiency', 'green', 60),
        ]
        text = generate_summary_text(signals)
        assert '전반적으로 양호' in text

    def test_multiple_reds(self):
        """red >= 2 → '심층 분석 권장'."""
        signals = [
            _make_signal('financial_structure', 'red', 20),
            _make_signal('cash_flow_quality', 'red', 15),
        ]
        text = generate_summary_text(signals)
        assert '심층 분석 권장' in text

    def test_no_signal(self):
        """green/red 없음 → 중립 문구."""
        signals = [
            _make_signal('profitability', 'yellow', 50),
            _make_signal('growth', 'yellow', 50),
        ]
        text = generate_summary_text(signals)
        assert '중립' in text or '강점/약점 없음' in text

    def test_gray_count(self):
        """gray 존재 → 해석 제한 언급."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('financial_structure', 'gray', 0),
            _make_signal('cash_flow_quality', 'gray', 0),
        ]
        text = generate_summary_text(signals)
        assert '해석 제한' in text
        assert '2개' in text


# ---------------------------------------------------------------------------
# Tests: generate_metric_interpretation
# ---------------------------------------------------------------------------


class TestGenerateMetricInterpretation:
    def test_not_applicable(self):
        text = generate_metric_interpretation(
            'interest_coverage', True, None, '', 'not_applicable', 'high',
            '무차입 기업'
        )
        assert text == '무차입 기업'

    def test_missing(self):
        text = generate_metric_interpretation(
            'sbc_to_revenue', True, None, '', 'missing', 'high'
        )
        assert '데이터가 제공되지 않아' in text

    def test_high_percentile(self):
        """percentile >= 75 → '상위' 포함."""
        text = generate_metric_interpretation(
            'roe', True, 85.0, 'improving', 'normal', 'high'
        )
        assert '상위' in text
        assert '개선' in text

    def test_low_percentile(self):
        """percentile <= 25 → '하위' 포함."""
        text = generate_metric_interpretation(
            'roe', True, 15.0, 'declining', 'normal', 'high'
        )
        assert '하위' in text
        assert '하락' in text

    def test_mid_percentile(self):
        """25 < percentile < 75 → '중앙값 수준'."""
        text = generate_metric_interpretation(
            'roe', True, 50.0, 'stable', 'normal', 'high'
        )
        assert '중앙값 수준' in text

    def test_low_confidence_warning(self):
        """confidence low/limited → 주의 경고."""
        text = generate_metric_interpretation(
            'roe', True, 50.0, '', 'normal', 'limited'
        )
        assert '표본이 적어' in text

    def test_unstable_warning(self):
        text = generate_metric_interpretation(
            'interest_coverage', True, 60.0, '', 'unstable', 'high'
        )
        assert '변동이 크므로' in text

    def test_direction_higher_is_better(self):
        text = generate_metric_interpretation(
            'roe', True, 50.0, '', 'normal', 'high'
        )
        assert '높을수록' in text

    def test_direction_lower_is_better(self):
        text = generate_metric_interpretation(
            'debt_to_equity', False, 50.0, '', 'normal', 'high'
        )
        assert '낮을수록' in text


# ---------------------------------------------------------------------------
# Tests: determine_trend
# ---------------------------------------------------------------------------


class TestDetermineTrend:
    def test_improving(self):
        """마지막 > 처음 * 1.05 → improving."""
        assert determine_trend([10.0, 11.0, 12.0]) == 'improving'

    def test_declining(self):
        """마지막 < 처음 * 0.95 → declining."""
        assert determine_trend([12.0, 11.0, 10.0]) == 'declining'

    def test_stable(self):
        """변동 < 5% → stable."""
        assert determine_trend([10.0, 10.1, 10.2]) == 'stable'

    def test_insufficient_data(self):
        """3개 미만 → 빈 문자열."""
        assert determine_trend([10.0, 11.0]) == ''

    def test_exactly_three(self):
        """정확히 3개 → 정상 계산."""
        result = determine_trend([5.0, 7.0, 10.0])
        assert result == 'improving'

    def test_longer_list_uses_last_three(self):
        """4개 이상 → 마지막 3개만 사용."""
        # [-3:] = [100, 90, 80] → declining
        assert determine_trend([50.0, 100.0, 90.0, 80.0]) == 'declining'


# ---------------------------------------------------------------------------
# Tests: generate_leader_summary
# ---------------------------------------------------------------------------


class TestGenerateLeaderSummary:
    def test_normal(self):
        adv = [
            {'category': 'profitability', 'metric': 'roe', 'delta': 0.05},
            {'category': 'growth', 'metric': 'revenue_growth_yoy', 'delta': 0.02},
        ]
        disadv = [
            {'category': 'valuation', 'metric': 'pe_ratio', 'delta': -5.0},
        ]
        text = generate_leader_summary(adv, disadv)
        assert '3개 비교 지표' in text
        assert '2개 우위' in text
        assert '강점' in text
        assert '약점' in text

    def test_no_data(self):
        text = generate_leader_summary([], [])
        assert '부족' in text

    def test_all_advantages(self):
        adv = [
            {'category': 'profitability', 'metric': 'roe'},
            {'category': 'growth', 'metric': 'fcf_growth_yoy'},
        ]
        text = generate_leader_summary(adv, [])
        assert '2개 우위' in text
        assert '약점' not in text

    def test_all_disadvantages(self):
        disadv = [
            {'category': 'valuation', 'metric': 'pe_ratio'},
            {'category': 'financial_structure', 'metric': 'debt_to_equity'},
        ]
        text = generate_leader_summary([], disadv)
        assert '0개 우위' in text
        assert '약점' in text
