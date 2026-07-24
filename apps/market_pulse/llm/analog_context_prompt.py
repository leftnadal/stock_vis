"""MP2-ANALOG Slice C-L3 — L3 맥락 생성 프롬프트(그라운딩·톤가드 규칙 주입).

소속: apps/market_pulse/llm (app 레이어 프롬프트 조립).
역할: 그날 선별 헤드라인 스니펫만 contents로 주입 → Gemini가 그날 '맥락'을 한국어 1문장으로 서술.
  system_instruction에 그라운딩 절대·톤가드 규칙을 박아 1차 방어(context_generator의 check_tone이 2차).
PROMPT_VERSION: 동결 태깅. 재생성 시 증가(AnalogDayContext.prompt_version).
"""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "cl3_v1"

SYSTEM_INSTRUCTION = (
    "너는 금융 시장 국면 아카이브의 맥락 서술자다. "
    "특정 날짜의 실제 뉴스 헤드라인만 근거로, 그날 시장이 처했던 '맥락'을 한국어 한 문장으로 서술한다.\n"
    "규칙(반드시 지켜라):\n"
    "1. 제공된 헤드라인에 등장하는 사실만 사용한다. 사전지식·추측·수치 발명은 금지한다.\n"
    "2. 원인을 단정하지 마라. '무엇 때문에 하락' 같은 인과 단정은 금지. "
    "대신 '어떤 발표가 있던 국면', '어떤 우려가 부각된 날'처럼 맥락만 서술한다.\n"
    "3. 시세 방향 예측('오를 것', '하락할 전망')과 투자 조언('매수', '매도')은 절대 금지한다.\n"
    "4. 한국어 한 문장, 40자 내외. 개별 종목보다 시장 전반의 맥락을 우선한다.\n"
    "5. 헤드라인이 뚜렷한 시장 주제를 뒷받침하지 못하면, "
    "'뚜렷한 시장 주제 없이 개별 종목 뉴스가 오간 날'처럼 담백하게 서술한다."
)


def build_contents(headlines: list[dict[str, Any]]) -> list[str]:
    """선별 헤드라인 → contents(문자열 1개). 제목 스니펫만 주입(그라운딩 절대)."""
    lines = "\n".join(f"- {h.get('title', '')}" for h in headlines)
    return [
        "다음은 특정 날짜의 실제 시장 뉴스 헤드라인 목록이다:\n"
        f"{lines}\n\n"
        "이 헤드라인들만 근거로, 그날 시장 맥락을 위 규칙에 따라 한국어 한 문장으로 서술하라."
    ]
