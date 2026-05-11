"""Slice 6 Part 2 Step B — E3 portfolio service layer.

서비스 흐름 4단계 (지시서 §2.5):
  1. build_e3_portfolio_prompt(context) → prompt string (Step A 보강본)
  2. llm_client.invoke(prompt, model) → raw response
  3. parse_e3_portfolio_response(raw) → E3PortfolioCommentary
  4. validate() + cost tracking (CostGuard)

mock 단계에서는 2번을 mock_responses fixture로 치환 (Part 3 진입 전 정적 검증).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.prompts.e3_portfolio import build_e3_portfolio_prompt
from portfolio.schemas.llm_outputs import E3PortfolioCommentary
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel


# ============================================================
# Mock fixture loader (Step B 정적 검증용)
# ============================================================

MOCK_FIXTURE_ROOT = (
    Path(__file__).parent.parent
    / "tests"
    / "fixtures"
    / "mock_responses"
    / "e3_portfolio"
)


def load_mock_response(fixture_id: str, model_label: str) -> str:
    """V1~V5 × haiku/sonnet mock fixture 로딩.

    Args:
        fixture_id: v1~v5 식별자 (예: "v1_concentrated_balanced").
        model_label: "haiku" 또는 "sonnet".

    Returns:
        mock LLM raw response 텍스트 (JSON string).

    Raises:
        FileNotFoundError: 등록되지 않은 fixture/model 조합.
        ValueError: 잘못된 model_label.
    """
    if model_label not in ("haiku", "sonnet"):
        raise ValueError(
            f"Unknown model_label: {model_label!r}. Valid: 'haiku' | 'sonnet'. "
            "gemini는 Slice 1 9/9 폴백 후 매트릭스 일관 제외 정책."
        )

    # fixture_id에서 short name 추출 (v1_concentrated_balanced → v1)
    short = fixture_id.split("_")[0]
    if short not in ("v1", "v2", "v3", "v4", "v5"):
        raise ValueError(
            f"Unknown fixture_id prefix: {short!r} (from {fixture_id!r}). "
            "Valid: v1~v5."
        )

    path = MOCK_FIXTURE_ROOT / f"{short}_{model_label}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Mock fixture not found: {path}. "
            f"Required: 10건 (V1~V5 × haiku/sonnet)."
        )
    return path.read_text(encoding="utf-8")


# ============================================================
# 파싱
# ============================================================


def parse_e3_portfolio_response(text: str) -> E3PortfolioCommentary:
    """LLM raw text → E3PortfolioCommentary (Pydantic 6 필드).

    parse_json_response가 마크다운 펜스 사후 제거 + Pydantic 검증 처리.
    """
    return parse_json_response(E3PortfolioCommentary, text)


# ============================================================
# 진입 함수 (real LLM — Part 3 진입 시 사용)
# ============================================================


def run_e3_portfolio(
    *,
    preset_id: str,
    preset_intent: str,
    holdings_summary: str,
    sector_concentration: str,
    diversification_score: float,
    risk_concentration_score: float,
    core_metrics_summary: str,
    analysis_context: dict[str, Any] | None = None,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """E3 portfolio 진입 함수 — real LLM 호출.

    Args:
        preset_id: preset 식별자.
        preset_intent: preset 의도 자연어.
        holdings_summary: 보유 종목 평탄화.
        sector_concentration, diversification_score, risk_concentration_score: 분석엔진 산출.
        core_metrics_summary: Core 7종 raw.
        analysis_context: dict — None 시 minimal 모드, dict 시 reinforced 모드 (Part 2 Step A).
        provider: "haiku"(default, 글쓰기 5/5 정착) | "sonnet" | "anthropic" | "gemini".
        client: LLMClient (테스트 모킹용 의존성 주입).

    Returns:
        {"response": E3PortfolioCommentary.model_dump(), "metadata": LLMResponse.metadata_dict()}

    Raises:
        ValueError: 미등록 provider.
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    prompt = build_e3_portfolio_prompt(
        preset_id=preset_id,
        preset_intent=preset_intent,
        holdings_summary=holdings_summary,
        sector_concentration=sector_concentration,
        diversification_score=diversification_score,
        risk_concentration_score=risk_concentration_score,
        core_metrics_summary=core_metrics_summary,
        analysis_context=analysis_context,
    )

    if client is None:
        client = LLMClient()
    raw = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    parsed = parse_e3_portfolio_response(raw.text)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }


# ============================================================
# Mock 서비스 흐름 4단계 (Step B 정적 검증용)
# ============================================================


def run_e3_portfolio_with_mock(
    *,
    fixture_id: str,
    model_label: str,
    preset_id: str,
    preset_intent: str,
    holdings_summary: str,
    sector_concentration: str,
    diversification_score: float,
    risk_concentration_score: float,
    core_metrics_summary: str,
    analysis_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mock LLM 응답으로 서비스 흐름 4단계 검증 (Part 3 real LLM 진입 전 정적).

    1. build_e3_portfolio_prompt(...) → prompt
    2. load_mock_response(fixture_id, model_label) → raw text (mock)
    3. parse_e3_portfolio_response(raw) → E3PortfolioCommentary
    4. validate (Pydantic 자동 — parse 단계 통과 = validate 통과)

    Returns:
        {
            "prompt": str (Step 1 산출),
            "raw_response": str (Step 2 mock 산출),
            "parsed": E3PortfolioCommentary.model_dump() (Step 3),
            "model_label": str,
            "fixture_id": str,
        }
    """
    prompt = build_e3_portfolio_prompt(
        preset_id=preset_id,
        preset_intent=preset_intent,
        holdings_summary=holdings_summary,
        sector_concentration=sector_concentration,
        diversification_score=diversification_score,
        risk_concentration_score=risk_concentration_score,
        core_metrics_summary=core_metrics_summary,
        analysis_context=analysis_context,
    )
    raw = load_mock_response(fixture_id, model_label)
    parsed = parse_e3_portfolio_response(raw)
    return {
        "prompt": prompt,
        "raw_response": raw,
        "parsed": parsed.model_dump(),
        "model_label": model_label,
        "fixture_id": fixture_id,
    }
