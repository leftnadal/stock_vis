"""
Briefing Output Safety (PR-E).

소속: apps/market_pulse/briefing (app 레이어 LLM 출력 검증).
역할: Gemini 응답 텍스트의 JSON 형태/면책 조항/금지 키워드 등 출력 안전성 검증.
  schemas/briefing.py의 Pydantic 스키마와 직교(이쪽은 텍스트 안전성, 스키마는 구조).
소비처: briefing/client.py 응답 직후 호출.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from apps.market_pulse.briefing.prompt import DISCLAIMER
from apps.market_pulse.llm.safety import (
    detect_refusal as _detect_refusal,
    scan_banned as _scan_banned,
    strip_codeblocks as _strip_codeblocks,
)
from apps.market_pulse.models.briefing import BriefingLog

logger = logging.getLogger(__name__)

# 출력 안전 검출기(banned/refusal/codeblock)는 `apps/market_pulse/llm/safety`로 단일출처화(S1 추출).
# 아래는 Brief 고유 길이 임계 + validate() 오케스트레이션(BriefingLog.Status·{headline,content} 결합).
MIN_LENGTH = 50
MAX_LENGTH = 800


@dataclass(frozen=True)
class SafetyResult:
    status: str
    headline: str
    content: str
    issues: list[str]


def validate(raw_text: str) -> SafetyResult:
    issues: list[str] = []

    if not raw_text or not raw_text.strip():
        return SafetyResult(
            status=BriefingLog.Status.FAILED,
            headline="시장 요약 생성 실패",
            content="LLM 응답이 비어있습니다. 후속 사이클에서 재시도됩니다. "
            + DISCLAIMER,
            issues=["empty_response"],
        )

    if _detect_refusal(raw_text):
        issues.append("refusal_hint")
        return SafetyResult(
            status=BriefingLog.Status.REFUSED,
            headline="시장 요약 생성 보류",
            content="LLM이 응답을 거부했습니다. 다음 사이클에서 재시도됩니다. "
            + DISCLAIMER,
            issues=issues,
        )

    cleaned = _strip_codeblocks(raw_text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        issues.append("json_parse_failed")
        headline = (raw_text.split("\n", 1)[0] or "시장 요약")[:300]
        content = raw_text.strip()
        if not content.endswith(DISCLAIMER):
            content = (content + " " + DISCLAIMER).strip()
        banned = _scan_banned(content)
        issues.extend(banned)
        if banned:
            return SafetyResult(
                status=BriefingLog.Status.REFUSED,
                headline="시장 요약 검토 필요",
                content="출력에 부적절한 표현이 감지되어 사용하지 않습니다. "
                + DISCLAIMER,
                issues=issues,
            )
        return SafetyResult(
            status=BriefingLog.Status.OK,
            headline=headline[:300],
            content=content[:MAX_LENGTH],
            issues=issues,
        )

    headline = str(payload.get("headline", ""))[:300]
    content = str(payload.get("content", ""))

    if len(content) < MIN_LENGTH:
        issues.append("content_too_short")

    banned = _scan_banned(content) + _scan_banned(headline)
    issues.extend(banned)
    if banned:
        return SafetyResult(
            status=BriefingLog.Status.REFUSED,
            headline="시장 요약 검토 필요",
            content="출력에 부적절한 표현이 감지되어 사용하지 않습니다. " + DISCLAIMER,
            issues=issues,
        )

    if not content.endswith(DISCLAIMER):
        content = (content.rstrip() + " " + DISCLAIMER).strip()

    return SafetyResult(
        status=BriefingLog.Status.OK,
        headline=headline,
        content=content[:MAX_LENGTH],
        issues=issues,
    )
