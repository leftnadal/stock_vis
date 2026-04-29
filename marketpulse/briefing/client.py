"""Market Pulse v2 — Gemini Briefing Client (PR-E). 동기 호출만 사용 (Bug #8)."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.conf import settings

from marketpulse.briefing.prompt import (
    SYSTEM_PROMPT,
    BriefingContext,
    few_shot_messages,
    render_user_prompt,
)
from marketpulse.utils.circuit_breaker import get_circuit

logger = logging.getLogger(__name__)


DEFAULT_MODEL = 'gemini-2.5-flash'


@dataclass(frozen=True)
class BriefingRawResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def _resolve_api_key() -> str | None:
    return (
        getattr(settings, 'GOOGLE_AI_API_KEY', None)
        or getattr(settings, 'GEMINI_API_KEY', None)
    )


def _build_client():
    import google.generativeai as genai_module
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY/GOOGLE_AI_API_KEY not configured')
    return genai_module.Client(api_key=api_key)


def _generate_sync(ctx: BriefingContext, *, model: str = DEFAULT_MODEL) -> BriefingRawResponse:
    client = _build_client()
    contents = []
    contents.extend(few_shot_messages())
    contents.append({'role': 'user', 'parts': [render_user_prompt(ctx)]})
    started = time.time()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={'system_instruction': SYSTEM_PROMPT},
    )
    latency_ms = int((time.time() - started) * 1000)
    text = getattr(response, 'text', '') or ''
    usage = getattr(response, 'usage_metadata', None)
    prompt_tokens = int(getattr(usage, 'prompt_token_count', 0) or 0)
    completion_tokens = int(getattr(usage, 'candidates_token_count', 0) or 0)
    return BriefingRawResponse(text, prompt_tokens, completion_tokens, latency_ms)


def generate(ctx: BriefingContext, *, model: str = DEFAULT_MODEL) -> BriefingRawResponse:
    cb = get_circuit('gemini')
    return cb.call(_generate_sync, ctx, model=model)
