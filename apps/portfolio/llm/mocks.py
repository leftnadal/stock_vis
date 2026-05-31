"""
Mock LLMClient — 5케이스 결정론적 시뮬레이션 + 진입점별 text strategy.

§7.1: LLMClient 인터페이스 호환. mode별 동작:
  - "normal":            정상 (Gemini 첫 시도 성공)
  - "rate_limit_first":  Gemini RateLimit → Anthropic 폴백 성공
  - "timeout_first":     Gemini Timeout    → Anthropic 폴백 성공
  - "auth_error":        Gemini AuthError → 폴백 안 함, raise
  - "budget_exceeded":   호출 즉시 LLMBudgetExceededError

text_strategy 옵션 (Slice 2 Step 0.5 도입):
  - "e1": OneLineDiagnosis JSON (default — Slice 1 호환)
  - "e5": E5Response JSON (Slice 2 Part 1)
  - "e2": E2DiagnosticCard JSON (Slice 3)
  - "e6": E6ComparisonResponse JSON (Slice 4)
  - "e3": MetricComments JSON (Slice 5)
"""

from __future__ import annotations

import json
from typing import Callable, Literal

from apps.portfolio.llm.exceptions import (
    LLMAuthError,
    LLMBudgetExceededError,
)
from apps.portfolio.schemas.llm import LLMResponse

# OneLineDiagnosis 스키마(headline 10~60자, summary 30~500자)를 통과하는 결정론적 Mock 응답.
_MOCK_DIAGNOSIS = {
    "headline": "GARP 적합도 양호, 밸류에이션 부담 일부",
    "summary": (
        "5개 종목 중 4개가 ROIC 산업 상위 25% 이내이며 EPS 성장도 견조합니다. "
        "다만 PEG 평균이 프리셋 기준 1.5를 상회해 성장 둔화 시 조정 리스크가 잠재합니다."
    ),
}
_MOCK_TEXT_E1 = json.dumps(_MOCK_DIAGNOSIS, ensure_ascii=False)


def _mock_text_e1(prompt: str) -> str:  # noqa: ARG001
    """E1 진입점: OneLineDiagnosis schema 통과 JSON."""
    return _MOCK_TEXT_E1


def _mock_text_e5(prompt: str) -> str:  # noqa: ARG001
    """E5 진입점: E5Response schema 통과 JSON (TSLA decrease 단일 항목)."""
    return (
        '{"adjustments":[{"ticker":"TSLA","action":"decrease",'
        '"delta_weight":-0.05,"target_weight":null,'
        '"reason_quote":"TSLA 줄여줘"}],'
        '"confidence":4,"ambiguity_notes":null,'
        '"no_actionable_intent":false}'
    )


def _mock_text_e2(prompt: str) -> str:  # noqa: ARG001
    """E2 진입점: DiagnosticCard 4요소 schema 통과 JSON (Slice 3 Step 0.6)."""
    return (
        '{"summary":"GARP 적합도 양호. 핵심 지표 균형 잡힌 포트폴리오입니다.",'
        '"strengths":["P/E 22.5 적정 수준입니다","ROE 18% 우수한 수익성"],'
        '"weaknesses":["배당수익률 1.2% 다소 낮음","현금흐름 변동성 존재"],'
        '"actions":["분기별 ROE 모니터링 권장","경쟁사 대비 P/E 추적 필요"]}'
    )


def _mock_text_e3(prompt: str) -> str:
    """E3 진입점: MetricComments schema 통과 JSON (Slice 5).

    prompt에서 metric_id 추출 후 각 지표에 대해 one_liner 생성.
    metric_id 미발견 시 default 3개 (pe_ratio/roic/revenue_growth).
    """
    import re

    metric_ids = re.findall(r'"metric_id"\s*:\s*"([^"]+)"', prompt)
    # 중복 제거 + 순서 유지
    seen: set[str] = set()
    unique_ids: list[str] = []
    for mid in metric_ids:
        if mid not in seen:
            seen.add(mid)
            unique_ids.append(mid)
    if not unique_ids:
        unique_ids = ["pe_ratio", "roic", "revenue_growth_yoy"]

    comments = []
    for mid in unique_ids[:5]:  # 최대 5개
        comments.append(
            {
                "metric_id": mid,
                "one_liner": (
                    f"{mid} 지표는 동종 업계 대비 양호한 수준으로 보입니다. "
                    "프리셋 관점에서 추가 모니터링이 권장됩니다."
                ),
            }
        )

    return json.dumps({"comments": comments}, ensure_ascii=False)


def _mock_text_e6(prompt: str) -> str:  # noqa: ARG001
    """E6 진입점: E6ComparisonResponse schema 통과 JSON (Slice 4 Step 0.6)."""
    return (
        '{"headline":"기술주 집중도 완화로 위험 균형이 개선됩니다",'
        '"before_summary":"기술주 비중 70%로 단일 섹터 집중 위험이 높고 변동성 높은 성장주 위주 구성입니다.",'
        '"after_summary":"기술주 55%로 축소, 디펜시브 15% 추가로 변동성 대비 안정성이 개선될 전망입니다.",'
        '"key_changes":['
        '{"aspect":"allocation","description":"테슬라 비중 20% → 10% 축소"},'
        '{"aspect":"diversification","description":"헬스케어 디펜시브 신규 진입 15%"},'
        '{"aspect":"risk","description":"단일 섹터 집중도 위험이 완화됩니다"}'
        "],"
        '"risk_assessment":"포트폴리오 변동성이 다소 낮아지고 하방 리스크가 완화될 것으로 예상됩니다.",'
        '"closing_remarks":"수익률 상한선은 일부 양보될 수 있으나 장기 안정성 측면에서 합리적인 조정입니다."}'
    )


_MOCK_TEXT_STRATEGIES: dict[str, Callable[[str], str]] = {
    "e1": _mock_text_e1,
    "e5": _mock_text_e5,
    "e2": _mock_text_e2,
    "e6": _mock_text_e6,
    "e3": _mock_text_e3,
}


MockMode = Literal[
    "normal",
    "rate_limit_first",
    "timeout_first",
    "auth_error",
    "budget_exceeded",
]


class MockLLMClient:
    """LLMClient 호환 Mock. 모드별로 폴백/에러/가드를 결정론적으로 시뮬레이션.

    Args:
        mode: 폴백/에러/가드 시나리오 (5개)
        text_strategy: 진입점별 응답 텍스트 (default "e1", Slice 1 호환)
    """

    def __init__(
        self,
        mode: MockMode = "normal",
        text_strategy: str = "e1",
    ) -> None:
        if text_strategy not in _MOCK_TEXT_STRATEGIES:
            raise ValueError(
                f"Unknown text_strategy: {text_strategy!r}. "
                f"Available: {list(_MOCK_TEXT_STRATEGIES)}"
            )
        self.mode: MockMode = mode
        self._call_count: int = 0
        self._text_fn: Callable[[str], str] = _MOCK_TEXT_STRATEGIES[text_strategy]

    def complete(
        self,
        prompt: str,
        provider: Literal["gemini", "anthropic"] = "gemini",
        max_tokens: int = 2000,  # noqa: ARG002
        model: str
        | None = None,  # LLMClient 시그니처 호환 (Sonnet/Haiku 분기, Mock은 무시)  # noqa: ARG002
    ) -> LLMResponse:
        self._call_count += 1

        if self.mode == "budget_exceeded":
            raise LLMBudgetExceededError("Mock 가드 발동: budget_exceeded mode")

        if self.mode == "auth_error":
            raise LLMAuthError("Mock 인증 실패: auth_error mode")

        if self.mode in ("rate_limit_first", "timeout_first") and provider == "gemini":
            # 폴백 결과만 흉내 (실제 retry는 LLMClient가 담당, Mock에서는 결과만)
            return self._mock_response(
                prompt, provider="anthropic", fallback_from="gemini"
            )

        # normal — 또는 anthropic 직접 호출
        return self._mock_response(prompt, provider=provider, fallback_from=None)

    # ------------------------------------------------------------

    def _mock_response(
        self,
        prompt: str,
        provider: Literal["gemini", "anthropic"],
        fallback_from: Literal["gemini", "anthropic"] | None,
    ) -> LLMResponse:
        return LLMResponse(
            text=self._text_fn(prompt),
            provider=provider,
            model=f"mock-{provider}",
            latency_ms=100,
            input_tokens=500,
            output_tokens=50,
            cost_usd=0.001,
            fallback_from=fallback_from,
        )
