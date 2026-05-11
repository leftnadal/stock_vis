"""
LLM 응답 robust 파서.

LLM이 prompt 지시(no markdown fences)를 무시하고 ```json ... ``` 펜스로
감싸는 케이스가 빈번 (Gemini/Claude 모두 관찰됨). 이를 사전 제거 후
Pydantic schema 검증으로 양도.
"""

from __future__ import annotations

import re
from typing import TypeVar

from pydantic import BaseModel


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
    LLM 응답 텍스트를 Pydantic 모델로 파싱. 마크다운 펜스 사전 제거.

    Args:
        model_cls: 대상 Pydantic 모델 클래스 (예: OneLineDiagnosis).
        text: LLM raw 응답.

    Returns:
        검증된 Pydantic 모델 인스턴스.

    Raises:
        pydantic.ValidationError: schema 미일치.
    """
    cleaned = strip_markdown_fences(text)
    return model_cls.model_validate_json(cleaned)
