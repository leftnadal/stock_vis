"""
Gemini Briefing Client (PR-E) — 일일 브리핑 본문 생성.

소속: apps/market_pulse/briefing (app 레이어 LLM 호출 — Brief 고유 프롬프트 조립).
역할: prompt.py 템플릿에 4 스냅샷(regime/breadth/sector/concentration) + 뉴스를 주입해
  Gemini 2.5 Flash로 동기 호출 → 본문 텍스트 반환. genai 호출·CB 결합 plumbing은
  `apps/market_pulse/llm/client` 공용 모듈로 단일출처화(복제 0, S1 추출).
의존: apps.market_pulse.llm.client (genai+CB plumbing), prompt.py (Brief 고유 프롬프트).
주의: Celery 안에서 호출 — **반드시 동기 API**(Bug #8: async genai.Client fork 충돌).
소비처: tasks/briefing.py의 mp_generate_brief_daily.
"""

from __future__ import annotations

import logging

from apps.market_pulse.briefing.prompt import (
    SYSTEM_PROMPT,
    BriefingContext,
    few_shot_messages,
    render_user_prompt,
)
from apps.market_pulse.llm.client import (
    DEFAULT_MODEL,
    LLMRawResponse,
    generate_with_circuit,
)

logger = logging.getLogger(__name__)

# 후방호환 alias — 기존 소비처가 BriefingRawResponse를 import할 수 있음(공용 LLMRawResponse).
BriefingRawResponse = LLMRawResponse


def generate(ctx: BriefingContext, *, model: str = DEFAULT_MODEL) -> LLMRawResponse:
    """Brief 고유 프롬프트(few-shot + user) 조립 후 공용 LLM plumbing 위임."""
    contents: list = []
    contents.extend(few_shot_messages())
    contents.append({"role": "user", "parts": [{"text": render_user_prompt(ctx)}]})
    return generate_with_circuit(
        system_instruction=SYSTEM_PROMPT, contents=contents, model=model
    )
