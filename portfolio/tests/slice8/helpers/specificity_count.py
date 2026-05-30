"""Slice 8 Part 3 §0.4 — specificity patterns 자동 카운트 헬퍼.

E4 답변 텍스트에 대해 P1~P5 5종 patterns 등장 여부를 판정 → 0~5 score 반환.
"구체성 부족" 판정 기준: score ≤ 2.

설계 출처: docs/portfolio/coach/slice8/specificity_patterns.md
재사용: Slice 9 이후 동일 KPI 측정 시 본 헬퍼 import.
"""

from __future__ import annotations

import re

# P1: 종목별 현재가/지표 언급
_P1_KEYWORDS = ("현재가", "주가", "PE", "PEG", "ROIC", "P/E", "시가")

# P2: 임계값/기준점 명시
_P2_CONTEXT = re.compile(r"(이상|이하|초과|미만|보다\s*(높|낮)|넘[고지]|않)")
_NUMBER = re.compile(r"\d")

# P3: 액션 동사
_P3_KEYWORDS = ("매수", "매도", "보유", "축소", "확대", "편입", "제외", "유지")

# P4: 구체 수치 임계값 (숫자 + 단위)
_P4_UNIT = re.compile(r"\d+(?:\.\d+)?\s*(%|배|원|달러|p)")

# P5: 기간/시점 명시
_P5_PATTERN = re.compile(r"(분기|반기|연간|YoY|QoQ|최근\s*\d+(?:년|개월|주|일))")


def has_p1(text: str) -> bool:
    """P1: 종목별 현재가/지표 키워드 등장."""
    return any(kw in text for kw in _P1_KEYWORDS)


def has_p2(text: str) -> bool:
    """P2: 임계값 비교 + 숫자."""
    return bool(_P2_CONTEXT.search(text) and _NUMBER.search(text))


def has_p3(text: str) -> bool:
    """P3: 액션 동사 등장."""
    return any(kw in text for kw in _P3_KEYWORDS)


def has_p4(text: str) -> bool:
    """P4: 숫자 + 단위 (%/배/원/달러/p)."""
    return bool(_P4_UNIT.search(text))


def has_p5(text: str) -> bool:
    """P5: 기간/시점 표현 등장."""
    return bool(_P5_PATTERN.search(text))


def count_patterns(text: str) -> int:
    """5종 patterns 중 등장 개수 반환 (0~5).

    Args:
        text: E4 답변 commentary 본문.

    Returns:
        score in [0, 5]. score ≤ 2 → "구체성 부족" 판정.
    """
    return sum(
        [has_p1(text), has_p2(text), has_p3(text), has_p4(text), has_p5(text)]
    )


def is_specificity_lacking(text: str) -> bool:
    """구체성 부족 판정 (score ≤ 2)."""
    return count_patterns(text) <= 2


def detail_patterns(text: str) -> dict[str, bool]:
    """P1~P5 각각의 발동 여부 반환 (Slice 9 #44 — rationale prompt에 인용).

    Args:
        text: E4 답변 commentary 본문.

    Returns:
        {"P1_metric_mention": bool, "P2_threshold": bool, "P3_action_verb": bool,
         "P4_quantitative": bool, "P5_time_period": bool}
    """
    return {
        "P1_metric_mention": has_p1(text),
        "P2_threshold": has_p2(text),
        "P3_action_verb": has_p3(text),
        "P4_quantitative": has_p4(text),
        "P5_time_period": has_p5(text),
    }
