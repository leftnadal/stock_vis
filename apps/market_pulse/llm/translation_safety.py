"""
Translation Output Safety (Phase 1.5 S3) — senses 봉투 파싱 + 출력 안전 검증.

소속: apps/market_pulse/llm (app 레이어 LLM 출력 검증, briefing/safety 미러).
역할: Gemini 응답 텍스트를 {regime,breadth,sector,concentration} JSON 봉투로 파싱하고,
  각 문장에 금지표현/거부를 스캔해 TranslationLog.Status(OK/REFUSED)와 senses dict를 결정.
  검출기(banned/refusal/codeblock)는 `apps/market_pulse/llm/safety` 단일출처를 재사용.
소비처: tasks/translation.py 응답 직후 호출.

상태 정책(S2 스키마 = OK/REFUSED만):
  - 빈 응답·refusal·JSON 파싱 실패·봉투 형식 불일치 → REFUSED, senses 비움(조용한 빈 OK 금지, 로그).
  - 금지표현 검출 → REFUSED, 해당 출력 전체 폐기(senses 비움).
  - 일부 카드 키 누락 → 누락 카드만 senses에서 빠지고 status=OK + issue 경고(부분 표기는
    새 status 값 없이 issues로 — 새 status 필요 시 별도 결정).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from apps.market_pulse.llm.safety import (
    detect_refusal as _detect_refusal,
    scan_banned as _scan_banned,
    strip_codeblocks as _strip_codeblocks,
)
from apps.market_pulse.llm.translation_prompt import SENSE_KEYS
from apps.market_pulse.models.translation import TranslationLog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SensesResult:
    status: str
    senses: dict
    issues: list[str] = field(default_factory=list)


def validate_senses(raw_text: str) -> SensesResult:
    import json

    if not raw_text or not raw_text.strip():
        return SensesResult(TranslationLog.Status.REFUSED, {}, ["empty_response"])

    if _detect_refusal(raw_text):
        return SensesResult(TranslationLog.Status.REFUSED, {}, ["refusal_hint"])

    cleaned = _strip_codeblocks(raw_text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return SensesResult(TranslationLog.Status.REFUSED, {}, ["json_parse_failed"])

    if not isinstance(payload, dict):
        return SensesResult(TranslationLog.Status.REFUSED, {}, ["envelope_not_object"])

    issues: list[str] = []
    senses: dict = {}
    for key in SENSE_KEYS:
        value = payload.get(key)
        if value is None or not str(value).strip():
            issues.append(f"missing:{key}")
            continue
        senses[str(key)] = str(value).strip()

    # 금지표현은 전체 폐기(부분 통과 금지) — 어느 카드라도 검출 시 REFUSED.
    banned: list[str] = []
    for key, text in senses.items():
        hits = _scan_banned(text)
        banned.extend(f"{key}:{h}" for h in hits)
    if banned:
        issues.extend(banned)
        return SensesResult(TranslationLog.Status.REFUSED, {}, issues)

    if not senses:
        # 4키 전부 누락/공백 — 빈 OK 금지.
        return SensesResult(TranslationLog.Status.REFUSED, {}, issues or ["all_keys_missing"])

    return SensesResult(TranslationLog.Status.OK, senses, issues)
