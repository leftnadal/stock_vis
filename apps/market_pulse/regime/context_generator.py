"""MP2-ANALOG Slice C-L3 — L3 맥락 생성기(오프라인 전용).

역할: 모집단일 T → 그라운딩 선별 → Gemini(generate_with_circuit) 1문장 → 톤가드 → {why_text, provenance}.
  카드 READ 경로 아님 — generate_analog_context 커맨드가 배치 호출(오프라인). 렌더는 저장분만 읽는다.
LLM 경계(STEP0 실측): market_pulse 기존 래퍼 generate_with_circuit 재사용(genai 직접생성 0, 경계 통과).
톤가드 재시도(D-CL3-TONE-RETRY): 1차 실패 → 1회 재생성 → 재실패면 None(why=null 유지, 억지 저장 금지).
그라운딩 0건(D-CL3-EMPTY-NULL): 그날 헤드라인 0건 → None(억지 생성 금지).
"""

from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Any

from apps.market_pulse.llm import analog_context_prompt as prompt_mod
from apps.market_pulse.regime.grounding import select_grounding
from apps.market_pulse.regime.tone_guard import check_tone

logger = logging.getLogger(__name__)


def _invoke_llm(headlines: list[dict[str, Any]]) -> str:
    """generate_with_circuit 경유 동기 호출 → 응답 텍스트. (테스트는 이 함수를 monkeypatch.)"""
    from apps.market_pulse.llm.client import generate_with_circuit

    resp = generate_with_circuit(
        system_instruction=prompt_mod.SYSTEM_INSTRUCTION,
        contents=prompt_mod.build_contents(headlines),
    )
    return resp.text


def generate_for_date(
    target_date: date_cls,
    *,
    prompt_version: str = prompt_mod.PROMPT_VERSION,
) -> dict[str, Any] | None:
    """T의 L3 맥락 생성. 성공 시 {why_text, provenance, prompt_version}, 실패/0건 시 None.

    provenance = 선별 헤드라인 [{id, url, title}] (근거 추적). 저장은 호출부(커맨드) 책임.
    """
    grounding = select_grounding(target_date)
    if not grounding:
        logger.info("C-L3 그라운딩 0건 date=%s → why=null 유지", target_date)
        return None

    text = _invoke_llm(grounding)
    ok, reason = check_tone(text)
    if not ok:
        logger.info("C-L3 톤가드 1차 실패 date=%s reason=%s → 재생성", target_date, reason)
        text = _invoke_llm(grounding)
        ok, reason = check_tone(text)
        if not ok:
            logger.warning("C-L3 톤가드 재실패 date=%s reason=%s → why=null 유지", target_date, reason)
            return None

    provenance = [
        {"id": str(h["id"]), "url": h["url"], "title": h["title"]} for h in grounding
    ]
    return {
        "why_text": text.strip(),
        "provenance": provenance,
        "prompt_version": prompt_version,
    }
