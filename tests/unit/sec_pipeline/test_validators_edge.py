"""
validators.py 추가 엣지 케이스 테스트.

기존 test_validators.py 에서 누락된 영역:
- MAX_SECTION_LENGTH 초과 시 'unusually long' WARN
- 모듈 상수 (MIN/MAX/EXPECTED) 가 양수
- _check_item_order: item_1 만 있고 item_7 없으면 검증 스킵
- validate_extracted_sections: WARN 만 발생한 섹션은 그대로 유지 (제거 안 됨)
- _check_item_order: item_1 == item_7 위치 (동일) → 위반
"""

import pytest

from sec_pipeline.validators import (
    EXPECTED_MIN_LENGTH,
    MAX_SECTION_LENGTH,
    MIN_SECTION_LENGTH,
    _check_item_order,
    validate_extracted_sections,
)


def _make_full_text():
    return (
        "Item 1 Description of Business\n"
        "Item 1A Risk Factors\n"
        "Item 7 Management Discussion\n"
        "Item 8 Financial Statements\n"
    )


# ---------------------------------------------------------------------------
# Tests: 상수 검증
# ---------------------------------------------------------------------------

class TestConstants:
    def test_constants_positive(self):
        assert MIN_SECTION_LENGTH > 0
        assert MAX_SECTION_LENGTH > 0
        assert EXPECTED_MIN_LENGTH > 0

    def test_constants_ordering(self):
        assert MIN_SECTION_LENGTH < EXPECTED_MIN_LENGTH < MAX_SECTION_LENGTH


# ---------------------------------------------------------------------------
# Tests: validate_extracted_sections — WARN 동작
# ---------------------------------------------------------------------------

class TestValidateWarnBehavior:
    def test_excessively_long_section_warns(self):
        """MAX_SECTION_LENGTH 초과 시 WARN: unusually long."""
        oversized = 'Item 1. Description of Business\n' + ('x ' * (MAX_SECTION_LENGTH))
        sections = {
            'item_1': oversized,
            'item_1a': '',
            'item_7': '',
        }
        validated, warnings = validate_extracted_sections(
            sections, _make_full_text()
        )
        assert any('unusually long' in w for w in warnings)
        # WARN 만 있으면 섹션 유지됨
        assert validated['item_1'] == oversized

    def test_warn_does_not_clear_section(self):
        """WARN: too short 가 발생해도 텍스트는 보존된다 (FAIL 만 비움)."""
        text = 'Item 1. Description of Business\n' + 'x ' * 100  # 짧지만 heading 있음
        sections = {'item_1': text, 'item_1a': '', 'item_7': ''}
        validated, warnings = validate_extracted_sections(
            sections, _make_full_text()
        )
        warns = [w for w in warnings if w.startswith('WARN:')]
        assert len(warns) > 0
        # FAIL 가 없으므로 item_1 텍스트는 그대로 유지
        assert validated['item_1'] == text

    def test_returns_dict_type(self):
        """반환 타입 검증: (dict, list)."""
        result = validate_extracted_sections(
            {'item_1': '', 'item_1a': '', 'item_7': ''},
            _make_full_text(),
        )
        assert isinstance(result, tuple)
        assert isinstance(result[0], dict)
        assert isinstance(result[1], list)


# ---------------------------------------------------------------------------
# Tests: _check_item_order — 누락 케이스
# ---------------------------------------------------------------------------

class TestCheckItemOrderPartial:
    def test_only_item_1_skips_check(self):
        """item_7 이 없으면 순서 검증 스킵 → 빈 문자열 반환."""
        text = "Item 1 Description of Business\nBusiness content."
        assert _check_item_order(text) == ''

    def test_only_item_7_skips_check(self):
        """item_1 이 없으면 순서 검증 스킵."""
        text = "Item 7 Management Discussion\nDiscussion content."
        assert _check_item_order(text) == ''

    def test_item_1a_after_item_7_violation(self):
        """1A 가 7 뒤에 오면 순서 위반."""
        text = (
            "Item 1 Description of Business\n"
            "Item 7 Management Discussion\n"
            "Item 1A Risk Factors\n"
        )
        result = _check_item_order(text)
        assert 'order violation' in result.lower()


# ---------------------------------------------------------------------------
# Tests: validate_extracted_sections — 단일 섹션 비어있을 때
# ---------------------------------------------------------------------------

class TestValidatePartialPresence:
    def test_only_item_1_provided(self):
        """item_1만 채워진 경우, item_7 등 빈 섹션은 길이 경고 없음."""
        sections = {
            'item_1': 'Item 1. Description of Business\n' + ('a ' * 1500),
            'item_1a': '',
            'item_7': '',
        }
        validated, warnings = validate_extracted_sections(
            sections, _make_full_text()
        )
        # 빈 섹션에 대한 길이 경고는 발생하지 않음
        for key in ('item_1a', 'item_7'):
            assert not any(key in w and 'too short' in w for w in warnings)
