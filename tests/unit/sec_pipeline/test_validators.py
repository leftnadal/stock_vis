"""
validators.py 단위 테스트.

validate_extracted_sections, _check_item_order 검증.
"""

import pytest

from services.sec_pipeline.validators import (
    EXPECTED_MIN_LENGTH,
    MAX_SECTION_LENGTH,
    MIN_SECTION_LENGTH,
    _check_item_order,
    validate_extracted_sections,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_section_text(key_label, length=3000):
    """heading + 지정 길이의 섹션 텍스트 생성."""
    headings = {
        'item_1': 'Item 1. Description of Business\n',
        'item_1a': 'Item 1A. Risk Factors\n',
        'item_7': "Item 7. Management's Discussion and Analysis\n",
    }
    heading = headings.get(key_label, '')
    body = 'x ' * ((length - len(heading)) // 2)
    return heading + body


def _make_full_text():
    """순서가 올바른 원문 텍스트."""
    return (
        "Some preamble.\n"
        "Item 1 Description of Business\n"
        "Business content here.\n"
        "Item 1A Risk Factors\n"
        "Risk content here.\n"
        "Item 7 Management Discussion\n"
        "Discussion content here.\n"
        "Item 8 Financial Statements\n"
        "Financial content here.\n"
    )


# ---------------------------------------------------------------------------
# Tests: _check_item_order
# ---------------------------------------------------------------------------

class TestCheckItemOrder:
    def test_correct_order(self):
        text = _make_full_text()
        assert _check_item_order(text) == ''

    def test_reversed_order(self):
        text = (
            "Item 7 Management Discussion\n"
            "Discussion content.\n"
            "Item 1 Description of Business\n"
            "Business content.\n"
        )
        result = _check_item_order(text)
        assert 'order violation' in result.lower() or 'Item order violation' in result

    def test_missing_items_skips_check(self):
        text = "Some text with no Item headings at all."
        assert _check_item_order(text) == ''


# ---------------------------------------------------------------------------
# Tests: validate_extracted_sections
# ---------------------------------------------------------------------------

class TestValidateExtractedSections:
    def test_all_valid(self):
        sections = {
            'item_1': _make_section_text('item_1'),
            'item_1a': _make_section_text('item_1a'),
            'item_7': _make_section_text('item_7'),
        }
        full_text = _make_full_text()
        validated, warnings = validate_extracted_sections(sections, full_text)

        # No FAIL warnings
        fail_warnings = [w for w in warnings if w.startswith('FAIL:')]
        assert len(fail_warnings) == 0
        assert validated['item_1'] != ''
        assert validated['item_7'] != ''

    def test_order_violation_discards_all(self):
        sections = {
            'item_1': _make_section_text('item_1'),
            'item_1a': _make_section_text('item_1a'),
            'item_7': _make_section_text('item_7'),
        }
        # Item 7 before Item 1
        bad_text = (
            "Item 7 Management Discussion\n"
            "Item 1 Description of Business\n"
        )
        validated, warnings = validate_extracted_sections(sections, bad_text)

        assert any('FAIL:' in w for w in warnings)
        assert validated['item_1'] == ''
        assert validated['item_1a'] == ''
        assert validated['item_7'] == ''

    def test_missing_heading_removes_section(self):
        sections = {
            'item_1': 'No heading here, just random text. ' * 100,  # no Item 1 heading
            'item_1a': _make_section_text('item_1a'),
            'item_7': _make_section_text('item_7'),
        }
        full_text = _make_full_text()
        validated, warnings = validate_extracted_sections(sections, full_text)

        assert validated['item_1'] == ''
        assert any('item_1 heading not found' in w for w in warnings)

    def test_short_section_warns(self):
        sections = {
            'item_1': 'Item 1. Description of Business\n' + 'x ' * 200,
            'item_1a': '',
            'item_7': '',
        }
        full_text = _make_full_text()
        validated, warnings = validate_extracted_sections(sections, full_text)

        warn_msgs = [w for w in warnings if 'WARN:' in w]
        assert len(warn_msgs) > 0

    def test_empty_sections_no_warnings(self):
        sections = {'item_1': '', 'item_1a': '', 'item_7': ''}
        full_text = _make_full_text()
        validated, warnings = validate_extracted_sections(sections, full_text)
        # Empty sections should not trigger length warnings
        length_warns = [w for w in warnings if 'too short' in w or 'long' in w]
        assert len(length_warns) == 0
