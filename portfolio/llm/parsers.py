"""
LLM 응답 robust 파서.

LLM이 prompt 지시(no markdown fences)를 무시하고 ```json ... ``` 펜스로
감싸는 케이스가 빈번 (Gemini/Claude 모두 관찰됨). 이를 사전 제거 후
Pydantic schema 검증으로 양도.

Slice 12 Step 0 (#58 close): Tier 3 trailing characters tolerance 도입.
LLM이 valid JSON 뒤에 markdown 텍스트를 첨부하는 패턴(Slice 11 Part 4 4.17% FAIL)을
raw_decode로 흡수. 첫 valid JSON 블록만 추출하여 schema validate로 양도.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError


_FENCE_OPEN = re.compile(r"^\s*```(?:json|JSON)?\s*\n?", flags=re.MULTILINE)
_FENCE_CLOSE = re.compile(r"\n?\s*```\s*$")


def strip_markdown_fences(text: str) -> str:
    """선두/말미의 ```json...``` 펜스 제거. 펜스 없으면 원문 반환."""
    s = text.strip()
    if "```" not in s:
        return s
    s = _FENCE_OPEN.sub("", s, count=1)
    s = _FENCE_CLOSE.sub("", s, count=1)
    return s.strip()


_M = TypeVar("_M", bound=BaseModel)


def parse_json_response(model_cls: type[_M], text: str) -> _M:
    """
    LLM 응답 텍스트를 Pydantic 모델로 파싱.

    3 Tier tolerance:
        Tier 1: 마크다운 펜스 제거 후 model_validate_json (Slice 1 기존)
        Tier 2: 펜스 제거 (Tier 1 안에 흡수)
        Tier 3: raw_decode로 첫 valid JSON 블록 추출 후 model_validate (Slice 12 #58)

    Args:
        model_cls: 대상 Pydantic 모델 클래스 (예: OneLineDiagnosis).
        text: LLM raw 응답.

    Returns:
        검증된 Pydantic 모델 인스턴스.

    Raises:
        pydantic.ValidationError: schema 미일치 또는 JSON 추출 불가.
    """
    cleaned = strip_markdown_fences(text)
    try:
        return model_cls.model_validate_json(cleaned)
    except ValidationError as exc:
        # Tier 3: trailing characters tolerance (Slice 12 Step 0 #58).
        # LLM이 valid JSON 뒤에 markdown 등 추가 텍스트를 첨부한 경우 흡수.
        if not _is_trailing_characters_error(exc):
            raise
        try:
            obj, _end_idx = json.JSONDecoder().raw_decode(cleaned)
        except json.JSONDecodeError:
            # raw_decode도 실패하면 원래 ValidationError 유지 (LLM 응답 자체가 깨짐).
            raise exc
        return model_cls.model_validate(obj)


def _is_trailing_characters_error(exc: ValidationError) -> bool:
    """ValidationError가 trailing characters 패턴인지 식별.

    Pydantic은 json_invalid 타입에 'trailing characters' 메시지를 포함시킨다.
    """
    for err in exc.errors():
        if err.get("type") == "json_invalid":
            msg = (err.get("msg") or "").lower()
            ctx = err.get("ctx") or {}
            ctx_err = (ctx.get("error") or "").lower()
            if "trailing" in msg or "trailing" in ctx_err or "extra data" in msg:
                return True
    return False
