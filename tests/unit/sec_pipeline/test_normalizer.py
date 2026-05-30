"""
normalizer.py 단위 테스트.

normalize_section_all, filter_paragraphs, _clean_text 검증.
"""

import pytest

from sec_pipeline.normalizer import (
    SUPPLY_CHAIN_KEYWORDS,
    _clean_text,
    filter_paragraphs,
    normalize_section_all,
)

# ---------------------------------------------------------------------------
# Tests: normalize_section_all
# ---------------------------------------------------------------------------

class TestNormalizeSectionAll:
    def test_combines_item1_and_item7(self):
        sections = {
            'item_1': 'Business description here.',
            'item_1a': 'Risk factors here.',
            'item_7': 'Management discussion here.',
        }
        result = normalize_section_all(sections)
        assert 'Business description' in result
        assert 'Management discussion' in result
        # item_1a는 포함하지 않음 (Track A는 item_1 + item_7만)
        assert 'Risk factors' not in result

    def test_empty_sections(self):
        sections = {'item_1': '', 'item_7': ''}
        result = normalize_section_all(sections)
        assert result == ''

    def test_only_item1(self):
        sections = {'item_1': 'Only business.', 'item_7': ''}
        result = normalize_section_all(sections)
        assert 'Only business' in result

    def test_cleans_html_entities(self):
        sections = {
            'item_1': 'Apple&amp;Google &nbsp; test',
            'item_7': '',
        }
        result = normalize_section_all(sections)
        assert '&amp;' not in result
        assert '&nbsp;' not in result


# ---------------------------------------------------------------------------
# Tests: filter_paragraphs
# ---------------------------------------------------------------------------

class TestFilterParagraphs:
    def test_filters_by_keywords(self):
        text = (
            "This paragraph mentions a key supplier and raw material procurement.\n"
            "This paragraph is about weather and climate.\n"
            "Another paragraph about our customer and distributor network."
        )
        result = filter_paragraphs(text)
        assert len(result) >= 1
        # keyword-containing paragraphs should be selected
        assert any('supplier' in p.lower() for p in result)

    def test_max_paragraphs_limit(self):
        # Generate many keyword-rich paragraphs
        paras = []
        for i in range(30):
            paras.append(
                f"Paragraph {i}: our supplier provides raw material and components "
                f"to our manufacturing facility. We compete with many vendors. "
                + "x " * 30
            )
        text = '\n'.join(paras)
        result = filter_paragraphs(text, max_paragraphs=5)
        assert len(result) <= 5

    def test_no_keywords_returns_empty(self):
        text = "The sky is blue and the grass is green. Nothing about business here. " + "a " * 50
        result = filter_paragraphs(text)
        assert result == []

    def test_short_paragraphs_excluded(self):
        text = "supplier\nThis is a long paragraph about our key supplier and the raw material " + "x " * 30
        result = filter_paragraphs(text)
        # "supplier" alone is < 50 chars, should be excluded
        for p in result:
            assert len(p) >= 50

    def test_deduplication(self):
        same_para = "Our key supplier provides critical components for manufacturing. " + "x " * 30
        text = f"{same_para}\n{same_para}\n{same_para}"
        result = filter_paragraphs(text)
        assert len(result) == 1

    def test_ranking_by_keyword_hits(self):
        low_hit = "Our supplier is important. " + "x " * 30
        high_hit = (
            "Our supplier provides raw material via our distributor. "
            "We compete with vendor networks and rely on procurement. " + "y " * 30
        )
        text = f"{low_hit}\n{high_hit}"
        result = filter_paragraphs(text)
        # high_hit should come first (more keyword matches)
        if len(result) >= 2:
            assert 'distributor' in result[0].lower() or 'compete' in result[0].lower()


# ---------------------------------------------------------------------------
# Tests: _clean_text
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_removes_html_entities(self):
        text = 'Hello&amp;World &lt;tag&gt;'
        result = _clean_text(text)
        assert '&amp;' not in result
        assert '&lt;' not in result

    def test_removes_numeric_entities(self):
        text = 'Price: &#36;100 &#8212; test'
        result = _clean_text(text)
        assert '&#36;' not in result
        assert '&#8212;' not in result

    def test_collapses_whitespace(self):
        text = 'Hello     World\n\n\n\n\nNext'
        result = _clean_text(text)
        assert '     ' not in result
        assert '\n\n\n' not in result

    def test_strips_edges(self):
        text = '   content   '
        result = _clean_text(text)
        assert result == 'content'


# ---------------------------------------------------------------------------
# Tests: SUPPLY_CHAIN_KEYWORDS
# ---------------------------------------------------------------------------

class TestSupplyChainKeywords:
    def test_keywords_not_empty(self):
        assert len(SUPPLY_CHAIN_KEYWORDS) > 10

    def test_essential_keywords_present(self):
        essential = ['supplier', 'customer', 'supply chain', 'competitor']
        for kw in essential:
            assert kw in SUPPLY_CHAIN_KEYWORDS
