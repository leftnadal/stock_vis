"""Slice 8 Part 3 §0.4 — specificity patterns count 헬퍼 검증."""

from __future__ import annotations

import pytest

from portfolio.tests.slice8.helpers.specificity_count import (
    count_patterns,
    has_p1,
    has_p2,
    has_p3,
    has_p4,
    has_p5,
    is_specificity_lacking,
)


class TestSpecificityPatterns:
    def test_p1_keyword_detection(self):
        """P1: 종목별 현재가/지표 키워드."""
        assert has_p1("삼성전자 PE 12.5 양호합니다")
        assert has_p1("ROIC 11% 우수")
        assert has_p1("현재가 70,000원")
        assert not has_p1("일반적으로 좋습니다")

    def test_p2_threshold_detection(self):
        """P2: 임계값 비교 + 숫자."""
        assert has_p2("PE 15 이상은 부담")
        assert has_p2("ROIC 10% 미만 우려")
        assert has_p2("KOSPI 변동성 14%보다 높음")
        assert not has_p2("좋아요")
        assert not has_p2("이상 좋음")  # 숫자 없음

    def test_p3_action_verb_detection(self):
        """P3: 액션 동사 등장."""
        assert has_p3("삼성전자 축소 검토")
        assert has_p3("매수 권장")
        assert has_p3("유지 권장")
        assert not has_p3("좋은 종목입니다")

    def test_p4_quantitative_threshold_detection(self):
        """P4: 숫자 + 단위."""
        assert has_p4("5%p 축소")
        assert has_p4("2배 노출")
        assert has_p4("70000원")  # 한국식 "10만원" 표현은 별도 영역, raw 숫자만 검출
        assert has_p4("PE 12.5배")
        assert not has_p4("좋아요")

    def test_p5_time_period_detection(self):
        """P5: 기간/시점 표현."""
        assert has_p5("최근 3개월 변동성")
        assert has_p5("분기 내 조정")
        assert has_p5("YoY 15% 성장")
        assert has_p5("연간 수익률")
        assert not has_p5("좋아요")

    def test_count_patterns_full_5(self):
        """4요소 모두 포함된 답변 → score 5."""
        text = (
            "삼성전자 PE 12.5는 업종 평균 15보다 낮습니다. "
            "최근 4분기 ROIC 11% 유지로 안정적입니다. "
            "5%p 비중 축소 검토 권장."
        )
        assert count_patterns(text) == 5

    def test_count_patterns_lacking(self):
        """추상 표현만 → score ≤ 2 → 구체성 부족."""
        text = "일반적으로 좋은 포트폴리오입니다. 추가 분석이 필요할 수 있습니다."
        score = count_patterns(text)
        assert score <= 2
        assert is_specificity_lacking(text)

    def test_count_patterns_score_range(self):
        """score는 항상 0~5 사이."""
        for text in ["", "x", "PE 12.5", "분기 매수", "최근 3개월"]:
            score = count_patterns(text)
            assert 0 <= score <= 5
