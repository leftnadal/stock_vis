"""Market Pulse v2 — Briefing Output Safety (PR-E)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from apps.market_pulse.briefing.prompt import DISCLAIMER
from apps.market_pulse.models.briefing import BriefingLog

logger = logging.getLogger(__name__)


BANNED_PATTERNS = [
    r"\b추천(\s)*종목\b",
    r"\b매수\s*추천\b",
    r"\b매도\s*추천\b",
    r"\b목표가\b",
    r"\b오를\s*것\b",
    r"\b하락할\s*것\b",
    r"\b오를\s*전망\b",
    r"\b상승\s*확실\b",
    r"\b하락\s*확실\b",
    r"(?i)\bbuy\s+(this|now)\b",
    r"(?i)\bsell\s+now\b",
    r"(?i)\bguaranteed\b",
]
BANNED_REGEX = [re.compile(p) for p in BANNED_PATTERNS]

REFUSAL_HINTS = [
    "i cannot",
    "i'm unable",
    "as an ai",
    "죄송하지만",
    "제공할 수 없",
    "응답할 수 없",
]

MIN_LENGTH = 50
MAX_LENGTH = 800


@dataclass(frozen=True)
class SafetyResult:
    status: str
    headline: str
    content: str
    issues: list[str]


def _strip_codeblocks(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text


def _detect_refusal(text: str) -> bool:
    low = text.lower()
    return any(hint in low for hint in REFUSAL_HINTS)


def _scan_banned(text: str) -> list[str]:
    issues = []
    for pat, regex in zip(BANNED_PATTERNS, BANNED_REGEX):
        if regex.search(text):
            issues.append(f"banned:{pat}")
    return issues


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
