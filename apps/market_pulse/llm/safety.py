"""
Market Pulse 공용 LLM 출력 안전 검출기 — banned/refusal/codeblock 순수 함수 (Brief에서 추출).

소속: apps/market_pulse/llm.
역할: LLM 텍스트 출력의 금지표현·거부·코드블록 검출(모델/스키마/disclaimer 무관 순수 함수).
  소비처(briefing.safety.validate·후속 translation 검증)가 재사용. disclaimer 문구·status 매핑·
  길이 임계는 각 소비처 고유(투자 면책 문구는 surface마다 다름) — 본 모듈에 두지 않는다.
"""

from __future__ import annotations

import re

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


def strip_codeblocks(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text


def detect_refusal(text: str) -> bool:
    low = text.lower()
    return any(hint in low for hint in REFUSAL_HINTS)


def scan_banned(text: str) -> list[str]:
    issues = []
    for pat, regex in zip(BANNED_PATTERNS, BANNED_REGEX):
        if regex.search(text):
            issues.append(f"banned:{pat}")
    return issues
