"""
RelationPreFilter Tests (Phase 5)

사전 필터링 서비스 테스트
"""
import pytest
from serverless.services.relation_pre_filter import (
    RelationPreFilter,
    PreFilterResult,
    get_pre_filter,
)


class TestRelationPreFilter:
    """RelationPreFilter 테스트"""

    @pytest.fixture
    def pre_filter(self):
        """PreFilter 인스턴스"""
        return RelationPreFilter()

    # ========================================
    # is_relation_candidate Tests
    # ========================================

    def test_is_candidate_acquired(self, pre_filter):
        """인수 관련 텍스트는 후보로 판단"""
        text = "Microsoft announced plans to acquire Activision Blizzard for $68.7 billion."
        assert pre_filter.is_relation_candidate(text) is True

    def test_is_candidate_invested(self, pre_filter):
        """투자 관련 텍스트는 후보로 판단"""
        text = "SoftBank invested $100 million in the AI startup."
        assert pre_filter.is_relation_candidate(text) is True

    def test_is_candidate_partner(self, pre_filter):
        """파트너십 관련 텍스트는 후보로 판단"""
        text = "Apple partnered with Goldman Sachs to launch the Apple Card."
        assert pre_filter.is_relation_candidate(text) is True

    def test_is_candidate_spinoff(self, pre_filter):
        """분사 관련 텍스트는 후보로 판단"""
        text = "GE announced it will spin off its healthcare division."
        assert pre_filter.is_relation_candidate(text) is True

    def test_is_candidate_sued(self, pre_filter):
        """소송 관련 텍스트는 후보로 판단"""
        text = "Apple is being sued by Epic Games over App Store policies."
        assert pre_filter.is_relation_candidate(text) is True

    def test_not_candidate_earnings(self, pre_filter):
        """실적 발표 텍스트는 후보가 아님"""
        text = "Apple reported quarterly earnings of $1.24 per share, beating estimates."
        assert pre_filter.is_relation_candidate(text) is False

    def test_not_candidate_price(self, pre_filter):
        """주가 관련 텍스트는 후보가 아님"""
        text = "Tesla shares rose 5% after the announcement."
        assert pre_filter.is_relation_candidate(text) is False

    def test_not_candidate_short_text(self, pre_filter):
        """짧은 텍스트는 후보가 아님"""
        text = "Stock price up"
        assert pre_filter.is_relation_candidate(text) is False

    def test_not_candidate_empty_text(self, pre_filter):
        """빈 텍스트는 후보가 아님"""
        assert pre_filter.is_relation_candidate("") is False
        assert pre_filter.is_relation_candidate(None) is False

    # ========================================
    # get_relation_hints Tests
    # ========================================

    def test_hints_acquired(self, pre_filter):
        """인수 텍스트에서 ACQUIRED 힌트 추출"""
        text = "Microsoft acquired Activision Blizzard."
        hints = pre_filter.get_relation_hints(text)
        assert 'ACQUIRED' in hints

    def test_hints_merger(self, pre_filter):
        """합병 텍스트에서 ACQUIRED 힌트 추출"""
        text = "The two companies agreed to merge."
        hints = pre_filter.get_relation_hints(text)
        assert 'ACQUIRED' in hints

    def test_hints_investment(self, pre_filter):
        """투자 텍스트에서 INVESTED_IN 힌트 추출"""
        text = "The company raised $500M in Series C funding."
        hints = pre_filter.get_relation_hints(text)
        assert 'INVESTED_IN' in hints

    def test_hints_partnership(self, pre_filter):
        """파트너십 텍스트에서 PARTNER_OF 힌트 추출"""
        text = "The two companies announced a strategic alliance."
        hints = pre_filter.get_relation_hints(text)
        assert 'PARTNER_OF' in hints

    def test_hints_spinoff(self, pre_filter):
        """분사 텍스트에서 SPIN_OFF 힌트 추출"""
        text = "GE spun off its healthcare unit."
        hints = pre_filter.get_relation_hints(text)
        assert 'SPIN_OFF' in hints

    def test_hints_lawsuit(self, pre_filter):
        """소송 텍스트에서 SUED_BY 힌트 추출"""
        text = "The company filed a lawsuit against the competitor."
        hints = pre_filter.get_relation_hints(text)
        assert 'SUED_BY' in hints

    def test_hints_multiple(self, pre_filter):
        """여러 관계 힌트 추출"""
        text = "After the acquisition was completed, the companies announced a new partnership."
        hints = pre_filter.get_relation_hints(text)
        assert len(hints) >= 2

    def test_hints_none(self, pre_filter):
        """힌트 없는 텍스트"""
        text = "The stock price increased by 5% today."
        hints = pre_filter.get_relation_hints(text)
        assert hints == []

    # ========================================
    # extract_company_mentions Tests
    # ========================================

    def test_company_with_suffix(self, pre_filter):
        """Inc., Corp. 등 접미사 있는 회사명 추출"""
        text = "Apple Inc. announced new products. Microsoft Corp reported earnings."
        mentions = pre_filter.extract_company_mentions(text)
        assert 'Apple Inc' in mentions or 'Apple' in mentions
        assert 'Microsoft Corp' in mentions or 'Microsoft' in mentions

    def test_company_ticker(self, pre_filter):
        """티커 심볼 추출"""
        text = "Shares of Apple (AAPL) and Microsoft (MSFT) rose today."
        mentions = pre_filter.extract_company_mentions(text)
        assert 'AAPL' in mentions
        assert 'MSFT' in mentions

    def test_excludes_common_words(self, pre_filter):
        """일반 단어는 제외"""
        text = "The company reported on Monday that earnings exceeded expectations."
        mentions = pre_filter.extract_company_mentions(text)
        assert 'Monday' not in mentions
        assert 'The' not in mentions

    # ========================================
    # analyze Tests
    # ========================================

    def test_analyze_full(self, pre_filter):
        """전체 분석 테스트"""
        text = "Microsoft (MSFT) announced it will acquire Activision Blizzard (ATVI) for $68.7 billion."
        result = pre_filter.analyze(text)

        assert isinstance(result, PreFilterResult)
        assert result.is_candidate is True
        assert 'ACQUIRED' in result.relation_hints
        assert len(result.company_mentions) >= 2
        assert result.confidence >= 0.5
        assert len(result.matched_patterns) > 0

    def test_analyze_not_candidate(self, pre_filter):
        """후보가 아닌 텍스트 분석"""
        text = "The stock market was volatile today."
        result = pre_filter.analyze(text)

        assert result.is_candidate is False
        assert result.relation_hints == []
        assert result.confidence < 0.3

    # ========================================
    # filter_batch Tests
    # ========================================

    def test_filter_batch(self, pre_filter):
        """배치 필터링 테스트"""
        documents = [
            {'headline': 'Microsoft (MSFT) acquired Activision Blizzard (ATVI) for $68.7B'},
            {'headline': 'Apple stock rises 5%'},
            {'headline': 'SoftBank Group (SFTBY) invested $100M in AI startup OpenAI'},
            {'headline': 'Market closes higher on earnings'},
        ]

        candidates = pre_filter.filter_batch(documents, text_field='headline', min_confidence=0.3)

        # 적어도 1개는 후보 (acquired or invested)
        assert len(candidates) >= 1

        # 후보는 튜플 (document, PreFilterResult)
        for doc, result in candidates:
            assert isinstance(result, PreFilterResult)
            assert result.is_candidate is True

    def test_filter_batch_empty(self, pre_filter):
        """빈 문서 리스트 필터링"""
        candidates = pre_filter.filter_batch([])
        assert candidates == []

    # ========================================
    # Singleton Tests
    # ========================================

    def test_singleton(self):
        """싱글톤 인스턴스 테스트"""
        filter1 = get_pre_filter()
        filter2 = get_pre_filter()
        assert filter1 is filter2
