"""
Gemini Briefing Client (PR-E) — 일일 브리핑 본문 생성.

소속: apps/market_pulse/briefing (app 레이어 LLM 호출 래퍼).
역할: prompt.py 템플릿에 4 스냅샷(regime/breadth/sector/concentration) + 뉴스를 주입해
  Gemini 2.5 Flash로 동기 호출 → safety.py로 출력 검증 → 본문 텍스트 반환.
의존: packages.shared.api_request.circuit_breaker (CB `gemini`), google.genai 동기 클라이언트.
주의: Celery 안에서 호출 — **반드시 동기 API** 사용(Bug #8 회피).
  async genai.Client는 Celery worker fork 충돌 발생.
소비처: tasks/briefing.py의 mp_generate_brief_daily.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.conf import settings

from apps.market_pulse.briefing.prompt import (
    SYSTEM_PROMPT,
    BriefingContext,
    few_shot_messages,
    render_user_prompt,
)
from packages.shared.api_request.circuit_breaker import get_circuit

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class BriefingRawResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def _resolve_api_key() -> str | None:
    return getattr(settings, "GOOGLE_AI_API_KEY", None) or getattr(
        settings, "GEMINI_API_KEY", None
    )


def _build_client():
    import google.generativeai as genai_module

    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured")
    return genai_module.Client(api_key=api_key)


def _generate_sync(
    ctx: BriefingContext, *, model: str = DEFAULT_MODEL
) -> BriefingRawResponse:
    client = _build_client()
    contents = []
    contents.extend(few_shot_messages())
    contents.append({"role": "user", "parts": [render_user_prompt(ctx)]})
    started = time.time()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={"system_instruction": SYSTEM_PROMPT},
    )
    latency_ms = int((time.time() - started) * 1000)
    text = getattr(response, "text", "") or ""
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    return BriefingRawResponse(text, prompt_tokens, completion_tokens, latency_ms)


def generate(
    ctx: BriefingContext, *, model: str = DEFAULT_MODEL
) -> BriefingRawResponse:
    cb = get_circuit("gemini")
    return cb.call(_generate_sync, ctx, model=model)
