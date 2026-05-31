"""Slice 12 Step 0 #58 — parse_json_response trailing characters tolerance.

Slice 11 Part 4 매트릭스 1/24 FAIL 패턴 흡수:
- LLM이 valid JSON 뒤에 markdown 텍스트(`---\n## 추가 코멘트...`)를 첨부
- 기존 model_validate_json은 json_invalid (trailing characters)로 ValidationError
- 신규 Tier 3: raw_decode로 첫 valid JSON 추출 후 model_validate

테스트 항목 (6건):
1. trailing markdown separator 후 텍스트 → Tier 3 통과
2. trailing 한국어 텍스트 → Tier 3 통과
3. trailing 두 번째 JSON 객체 → 첫 객체만 추출
4. 깨끗한 valid JSON → Tier 1 그대로 (backward-compat)
5. 코드펜스 둘러싼 JSON → 펜스 제거 후 Tier 1 (backward-compat)
6. 완전 invalid (JSON 부분 없음) → ValidationError raise (silent 무시 X)
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from apps.portfolio.llm.parsers import parse_json_response


class _Sample(BaseModel):
    """테스트용 최소 schema."""

    key: str
    value: int = 0


class _SampleKorean(BaseModel):
    summary: str


def test_trailing_markdown_separator():
    """valid JSON + --- + 마크다운 (Slice 11 E3/haiku/#1 패턴)."""
    text = '{"key": "v1", "value": 42}\n---\n\n## 추가 코멘트\n본문 텍스트...'
    result = parse_json_response(_Sample, text)
    assert result.key == "v1"
    assert result.value == 42


def test_trailing_korean_text():
    """valid JSON + 한국어 텍스트."""
    text = '{"summary": "한국어 요약"}\n\n이 분석은 추가로 모니터링이 필요합니다.'
    result = parse_json_response(_SampleKorean, text)
    assert result.summary == "한국어 요약"


def test_trailing_second_json_object():
    """valid JSON + 추가 JSON (첫 객체만 추출)."""
    text = '{"key": "first", "value": 1}\n{"key": "second", "value": 2}'
    result = parse_json_response(_Sample, text)
    assert result.key == "first"
    assert result.value == 1


def test_clean_json_unchanged():
    """trailing 없는 valid JSON은 Tier 1 그대로 (backward-compat)."""
    text = '{"key": "clean", "value": 7}'
    result = parse_json_response(_Sample, text)
    assert result.key == "clean"
    assert result.value == 7


def test_code_fence_unchanged():
    """코드펜스 둘러싼 JSON은 펜스 제거 후 Tier 1 (backward-compat)."""
    text = '```json\n{"key": "fenced", "value": 99}\n```'
    result = parse_json_response(_Sample, text)
    assert result.key == "fenced"
    assert result.value == 99


def test_invalid_json_raises():
    """JSON 블록이 전혀 없으면 ValidationError raise (silent 무시 X)."""
    text = "completely invalid text without any json block"
    with pytest.raises(ValidationError):
        parse_json_response(_Sample, text)
