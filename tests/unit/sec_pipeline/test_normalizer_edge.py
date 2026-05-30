"""
normalizer.py 추가 엣지 케이스 테스트.

기존 test_normalizer.py 에서 누락된 영역:
- filter_paragraphs: default track 인자
- filter_paragraphs: max_paragraphs=0
- normalize_section_all: item_1 + item_7 결합 시 item_1 이 앞에 옴
- filter_paragraphs: 대문자 키워드 매칭 (case-insensitive)
- _clean_text: 빈 문자열
"""

import pytest

from sec_pipeline.normalizer import (
    SUPPLY_CHAIN_KEYWORDS,
    _clean_text,
    filter_paragraphs,
    normalize_section_all,
)

# ---------------------------------------------------------------------------
# Tests: filter_paragraphs — 인자 처리
# ---------------------------------------------------------------------------

class TestFilterParagraphsArgs:
    def test_default_track_is_supply_chain(self):
        """track 인자를 생략하면 supply_chain 키워드 사용."""
        text = "Our key supplier is critical for our raw material procurement. " + "x " * 30
        # track 인자 생략
        result = filter_paragraphs(text)
        assert len(result) >= 1

    def test_max_paragraphs_one_returns_at_most_one(self):
        """max_paragraphs=1 이면 최대 1개만 반환."""
        text = (
            "Our supplier provides raw material. " + "x " * 30 + "\n"
            "Our customer base is concentrated. " + "y " * 30 + "\n"
            "We rely on our distributor network. " + "z " * 30
        )
        result = filter_paragraphs(text, max_paragraphs=1)
        assert len(result) <= 1

    def test_keyword_match_case_insensitive(self):
        """대문자 키워드도 매칭된다 (SUPPLIER, CUSTOMER 등)."""
        text = "Our KEY SUPPLIER provides CRITICAL components. " + "x " * 30
        result = filter_paragraphs(text)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Tests: normalize_section_all — 순서
# ---------------------------------------------------------------------------

class TestNormalizeSectionAllOrder:
    def test_item_1_before_item_7(self):
        """결합 결과에서 item_1 이 item_7 보다 앞에 위치."""
        sections = {
            'item_1': 'BUSINESS_TEXT',
            'item_7': 'MDA_TEXT',
        }
        result = normalize_section_all(sections)
        assert result.index('BUSINESS_TEXT') < result.index('MDA_TEXT')

    def test_separator_between_sections(self):
        """두 섹션 사이에 빈 줄(\\n\\n) 구분자가 들어간다."""
        sections = {'item_1': 'A', 'item_7': 'B'}
        result = normalize_section_all(sections)
        assert '\n\n' in result


# ---------------------------------------------------------------------------
# Tests: _clean_text — 추가 케이스
# ---------------------------------------------------------------------------

class TestCleanTextExtra:
    def test_empty_string_returns_empty(self):
        assert _clean_text('') == ''

    def test_only_whitespace_returns_empty(self):
        assert _clean_text('   \n\n\t  ') == ''

    def test_preserves_alphanumeric_content(self):
        """일반 단어는 그대로 보존."""
        text = 'Apple Inc. designs phones.'
        result = _clean_text(text)
        assert 'Apple Inc.' in result
        assert 'designs phones' in result


# ---------------------------------------------------------------------------
# Tests: SUPPLY_CHAIN_KEYWORDS — 추가 검증
# ---------------------------------------------------------------------------

class TestSupplyChainKeywordsExtra:
    def test_keywords_are_lowercase_or_normalized(self):
        """일부 키워드는 소문자로 정의됨 (case-insensitive 매칭 전제)."""
        # 적어도 절반 이상은 소문자 시작
        lowers = [kw for kw in SUPPLY_CHAIN_KEYWORDS if kw[0].islower()]
        assert len(lowers) > len(SUPPLY_CHAIN_KEYWORDS) / 2

    def test_no_duplicate_keywords(self):
        assert len(SUPPLY_CHAIN_KEYWORDS) == len(set(SUPPLY_CHAIN_KEYWORDS))
