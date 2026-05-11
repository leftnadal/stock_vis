"""
E5 진입점 비즈니스 로직: 자연어 → 구조화 override JSON.

Slice 1 e1_garp.py 패턴 mirror. v2 (I5): module-level import — Mock 패치
타겟은 `portfolio.services.e5_adjustment_parser.LLMClient`.

옵션 B 정합:
  - LLMClient.complete(prompt, provider, model) 사용 (지시서의 .invoke 아님)
  - parse_json_response(model_cls, text) 시그니처 사용
  - PROVIDER_KWARGS label 매핑 (gemini/anthropic/sonnet/haiku)
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.llm import E5Request, E5Response

# Slice 3 Step 2 — _llm_kwargs.py 공유 모듈 흡수 (백로그 #3).
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel  # noqa: F401


# ============================================================
# 프롬프트
# ============================================================

def build_e5_prompt(request: E5Request) -> str:
    """
    E5 프롬프트 조립.

    설계 원칙:
      - schema 강제 — JSON only, no markdown fences, extra 키 금지
      - 의도 매칭 — 사용자 명령에 없는 종목 임의 추가 금지
      - reason_quote 강제 — 모든 adjustment에 자연어 근거 인용 필수
      - confidence 가이드 — 1=불확실, 5=확실
      - no_actionable_intent — 잡담/질문은 빈 adjustments + 플래그
      - action 일관성 — Pydantic validator(I2)와 일치
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", [])
    holdings_summary = ", ".join(
        f"{h.get('ticker', h.get('stock_symbol', '?'))}({_pct(h.get('weight', 0))})"
        for h in holdings
    )
    summary = _format_analysis_summary(ctx)

    return f"""당신은 한국 개인 투자자의 포트폴리오 조정 명령을 파싱하는 전문가입니다.

## 현재 포트폴리오
{holdings_summary}

## 분석 결과 요약
{summary}

## 사용자 명령
"{request.user_command}"

## 작업
사용자 명령을 다음 JSON schema로 변환하세요. JSON 객체만 반환하며, 마크다운
코드 펜스(```json ... ```)나 추가 설명을 절대 포함하지 마세요. 첫 글자는 `{{`,
마지막 글자는 `}}` 입니다.

{{
  "adjustments": [
    {{
      "ticker": "...",
      "action": "increase|decrease|remove|add|info_only",
      "delta_weight": -1.0~1.0 (또는 null),
      "target_weight": 0.0~1.0 (또는 null),
      "reason_quote": "사용자 명령에서 이 조정을 추출한 근거 인용 (한국어 그대로)"
    }}
  ],
  "confidence": 1~5,
  "ambiguity_notes": "명령이 모호한 경우 메모 (또는 null)",
  "no_actionable_intent": false
}}

## 규칙
1. 사용자 명령에 명시되지 않은 종목을 임의로 추가하지 마세요.
2. 비중 수치가 명시되지 않은 경우 delta_weight를 null로 두고 action만 채우세요.
3. 명령이 질문/잡담이면 adjustments=[], no_actionable_intent=true.
4. reason_quote는 사용자 원문에서 인용. 의역 금지.
5. confidence는 명령 명확성 기준 (5=명확, 1=모호).
6. action 일관성: decrease는 delta_weight ≤ 0, increase는 ≥ 0,
   remove는 target_weight=0 또는 null, info_only는 delta/target 모두 None 또는 0.
"""


def _pct(weight: Any) -> str:
    try:
        return f"{float(weight):.0%}"
    except (TypeError, ValueError):
        return "?"


# Slice 3 Step 2 — _prompt_helpers.py 공유 모듈 흡수 (백로그 #4).
from portfolio.services._prompt_helpers import (
    format_analysis_summary as _format_analysis_summary,  # noqa: F401
)


# ============================================================
# entry function
# ============================================================

def run_e5(
    request: E5Request,
    *,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """
    E5 진입점 실행 (view → service).

    Args:
        request: E5Request (analysis_context + user_command).
        provider: label (default haiku — Slice 1 winner).
        client: LLMClient 인스턴스 (의존성 주입, 테스트 모킹용).

    Returns:
        {
            "response":  E5Response.model_dump(),
            "metadata":  LLMResponse.metadata_dict(),
        }
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. "
            f"Valid: {sorted(PROVIDER_KWARGS)}"
        )

    prompt = build_e5_prompt(request)

    if client is None:
        client = LLMClient()
    llm_response = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    parsed = parse_json_response(E5Response, llm_response.text)
    return {
        "response": parsed.model_dump(),
        "metadata": llm_response.metadata_dict(),
    }
