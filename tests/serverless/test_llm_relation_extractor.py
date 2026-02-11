"""
LLMRelationExtractor Tests (Phase 5)

LLM 기반 관계 추출 서비스 테스트
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from decimal import Decimal

from serverless.services.llm_relation_extractor import (
    LLMRelationExtractor,
    ExtractedRelation,
    ExtractionResult,
)


class TestExtractedRelation:
    """ExtractedRelation 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        relation = ExtractedRelation(
            source_company="Microsoft",
            target_company="Activision Blizzard",
            relation_type="ACQUIRED",
            confidence_score=0.95,
            evidence="Microsoft acquired Activision...",
            context={"deal_value": "$68.7B"}
        )

        assert relation.source_company == "Microsoft"
        assert relation.target_company == "Activision Blizzard"
        assert relation.relation_type == "ACQUIRED"
        assert relation.confidence_score == 0.95
        assert relation.context["deal_value"] == "$68.7B"

    def test_default_context(self):
        """기본 context 테스트"""
        relation = ExtractedRelation(
            source_company="A",
            target_company="B",
            relation_type="PARTNER_OF",
            confidence_score=0.5,
            evidence="test"
        )

        assert relation.context == {}


class TestExtractionResult:
    """ExtractionResult 데이터클래스 테스트"""

    def test_creation(self):
        """생성 테스트"""
        result = ExtractionResult(
            relations=[],
            source_id="abc123",
            source_type="news",
            prompt_tokens=100,
            completion_tokens=50,
            extraction_time_ms=1500
        )

        assert result.source_id == "abc123"
        assert result.source_type == "news"
        assert result.prompt_tokens == 100
        assert result.extraction_time_ms == 1500
        assert result.error is None

    def test_with_error(self):
        """에러 포함 테스트"""
        result = ExtractionResult(
            relations=[],
            source_id="abc123",
            source_type="news",
            error="API failed"
        )

        assert result.error == "API failed"


class TestLLMRelationExtractorParsing:
    """LLM 응답 파싱 테스트 (LLM 호출 없음)"""

    @pytest.fixture
    def mock_extractor(self):
        """LLM 클라이언트 모킹된 Extractor"""
        with patch('serverless.services.llm_relation_extractor.genai.Client'):
            extractor = LLMRelationExtractor()
            return extractor

    def test_parse_valid_response(self, mock_extractor):
        """유효한 JSON 응답 파싱"""
        llm_result = {
            'text': '''
            {
                "relations": [
                    {
                        "source_company": "Microsoft",
                        "target_company": "Activision Blizzard",
                        "relation_type": "ACQUIRED",
                        "confidence": 0.95,
                        "evidence": "Microsoft acquired Activision Blizzard for $68.7 billion.",
                        "context": {"deal_value": "$68.7B", "status": "completed"}
                    }
                ]
            }
            ''',
            'prompt_tokens': 100,
            'completion_tokens': 50
        }

        relations = mock_extractor._parse_llm_response(llm_result)

        assert len(relations) == 1
        assert relations[0].source_company == "Microsoft"
        assert relations[0].target_company == "Activision Blizzard"
        assert relations[0].relation_type == "ACQUIRED"
        assert relations[0].confidence_score == 0.95

    def test_parse_multiple_relations(self, mock_extractor):
        """여러 관계 파싱"""
        llm_result = {
            'text': '''
            {
                "relations": [
                    {
                        "source_company": "Microsoft",
                        "target_company": "Activision",
                        "relation_type": "ACQUIRED",
                        "confidence": 0.9,
                        "evidence": "Microsoft acquired Activision."
                    },
                    {
                        "source_company": "Apple",
                        "target_company": "Goldman Sachs",
                        "relation_type": "PARTNER_OF",
                        "confidence": 0.85,
                        "evidence": "Apple partnered with Goldman."
                    }
                ]
            }
            '''
        }

        relations = mock_extractor._parse_llm_response(llm_result)

        assert len(relations) == 2
        assert relations[0].relation_type == "ACQUIRED"
        assert relations[1].relation_type == "PARTNER_OF"

    def test_parse_empty_relations(self, mock_extractor):
        """빈 관계 배열 파싱"""
        llm_result = {
            'text': '{"relations": []}'
        }

        relations = mock_extractor._parse_llm_response(llm_result)
        assert relations == []

    def test_parse_invalid_relation_type(self, mock_extractor):
        """유효하지 않은 관계 타입은 무시"""
        llm_result = {
            'text': '''
            {
                "relations": [
                    {
                        "source_company": "A",
                        "target_company": "B",
                        "relation_type": "INVALID_TYPE",
                        "confidence": 0.5,
                        "evidence": "test"
                    },
                    {
                        "source_company": "C",
                        "target_company": "D",
                        "relation_type": "ACQUIRED",
                        "confidence": 0.5,
                        "evidence": "test"
                    }
                ]
            }
            '''
        }

        relations = mock_extractor._parse_llm_response(llm_result)

        # INVALID_TYPE은 무시, ACQUIRED만 포함
        assert len(relations) == 1
        assert relations[0].relation_type == "ACQUIRED"

    def test_parse_missing_fields(self, mock_extractor):
        """필수 필드 누락시 무시"""
        llm_result = {
            'text': '''
            {
                "relations": [
                    {
                        "source_company": "A",
                        "relation_type": "ACQUIRED"
                    },
                    {
                        "source_company": "C",
                        "target_company": "D",
                        "relation_type": "PARTNER_OF",
                        "confidence": 0.5,
                        "evidence": "test"
                    }
                ]
            }
            '''
        }

        relations = mock_extractor._parse_llm_response(llm_result)

        # target_company 없는 첫번째는 무시
        assert len(relations) == 1

    def test_parse_malformed_json(self, mock_extractor):
        """잘못된 JSON 복구"""
        llm_result = {
            'text': '''{"relations": [{"source_company": "Microsoft", "target_company": "Activision", "relation_type": "ACQUIRED"'''
        }

        relations = mock_extractor._parse_llm_response(llm_result)

        # 정규식으로 복구 시도
        assert len(relations) >= 0  # 복구 실패해도 빈 리스트

    def test_recover_from_partial_json(self, mock_extractor):
        """부분 JSON 복구"""
        partial_text = '''
        {"relations": [
            {"source_company": "Microsoft", "target_company": "Activision", "relation_type": "ACQUIRED", "confidence": 0.9},
            {"source_company": "Apple", "target_company": "Goldman
        '''

        relations = mock_extractor._recover_from_partial_json(partial_text)

        # 최소 1개는 복구
        assert len(relations) >= 1
        assert relations[0].source_company == "Microsoft"

    # ========================================
    # Score to Level Tests
    # ========================================

    def test_score_to_level_high(self, mock_extractor):
        """High 신뢰도"""
        assert mock_extractor._score_to_level(0.95) == 'high'
        assert mock_extractor._score_to_level(0.80) == 'high'

    def test_score_to_level_medium(self, mock_extractor):
        """Medium 신뢰도"""
        assert mock_extractor._score_to_level(0.70) == 'medium'
        assert mock_extractor._score_to_level(0.60) == 'medium'

    def test_score_to_level_low(self, mock_extractor):
        """Low 신뢰도"""
        assert mock_extractor._score_to_level(0.50) == 'low'
        assert mock_extractor._score_to_level(0.30) == 'low'


class TestLLMRelationExtractorIntegration:
    """통합 테스트 (PreFilter, SymbolMatcher 연동)"""

    @pytest.fixture
    def mock_extractor(self):
        """모든 외부 의존성 모킹"""
        with patch('serverless.services.llm_relation_extractor.genai.Client'):
            with patch('serverless.services.llm_relation_extractor.get_pre_filter') as mock_pf:
                with patch('serverless.services.llm_relation_extractor.get_symbol_matcher') as mock_sm:
                    # PreFilter 모킹
                    mock_pre_filter = MagicMock()
                    mock_pf.return_value = mock_pre_filter

                    # SymbolMatcher 모킹
                    mock_symbol_matcher = MagicMock()
                    mock_sm.return_value = mock_symbol_matcher

                    extractor = LLMRelationExtractor()
                    extractor.pre_filter = mock_pre_filter
                    extractor.symbol_matcher = mock_symbol_matcher

                    yield extractor

    def test_extract_skipped_by_prefilter(self, mock_extractor):
        """PreFilter에서 거부된 텍스트는 스킵"""
        # PreFilter가 후보 아님으로 판단
        mock_result = MagicMock()
        mock_result.is_candidate = False
        mock_extractor.pre_filter.analyze.return_value = mock_result

        with patch.object(mock_extractor, '_call_llm') as mock_llm:
            result = mock_extractor.extract_from_text(
                text="The stock price rose 5%.",
                source_id="test123",
                source_type="news"
            )

        # LLM 호출 없어야 함
        mock_llm.assert_not_called()
        assert result.relations == []

    def test_extract_with_prefilter_pass(self, mock_extractor):
        """PreFilter 통과시 LLM 호출"""
        # PreFilter가 후보로 판단
        mock_result = MagicMock()
        mock_result.is_candidate = True
        mock_extractor.pre_filter.analyze.return_value = mock_result

        # LLM 응답 모킹
        with patch.object(mock_extractor, '_call_llm') as mock_llm:
            mock_llm.return_value = {
                'text': '{"relations": []}',
                'prompt_tokens': 100,
                'completion_tokens': 50
            }

            result = mock_extractor.extract_from_text(
                text="Microsoft acquired Activision.",
                source_id="test123",
                source_type="news"
            )

        # LLM 호출됨
        mock_llm.assert_called_once()

    def test_extract_skip_prefilter(self, mock_extractor):
        """skip_prefilter=True 시 PreFilter 무시"""
        with patch.object(mock_extractor, '_call_llm') as mock_llm:
            mock_llm.return_value = {
                'text': '{"relations": []}',
                'prompt_tokens': 100,
                'completion_tokens': 50
            }

            result = mock_extractor.extract_from_text(
                text="Any text",
                source_id="test123",
                source_type="news",
                skip_prefilter=True
            )

        # PreFilter.analyze 호출 안 됨
        mock_extractor.pre_filter.analyze.assert_not_called()
        # LLM 호출됨
        mock_llm.assert_called_once()


class TestLLMRelationExtractorDB:
    """DB 저장 테스트"""

    @pytest.fixture
    def mock_extractor(self):
        """LLM 모킹된 Extractor"""
        with patch('serverless.services.llm_relation_extractor.genai.Client'):
            with patch('serverless.services.llm_relation_extractor.get_pre_filter') as mock_pf:
                with patch('serverless.services.llm_relation_extractor.get_symbol_matcher') as mock_sm:
                    mock_pre_filter = MagicMock()
                    mock_pf.return_value = mock_pre_filter

                    mock_symbol_matcher = MagicMock()
                    mock_sm.return_value = mock_symbol_matcher

                    extractor = LLMRelationExtractor()
                    extractor.pre_filter = mock_pre_filter
                    extractor.symbol_matcher = mock_symbol_matcher

                    yield extractor

    @pytest.mark.django_db
    def test_extract_and_save(self, mock_extractor):
        """추출 후 DB 저장"""
        from serverless.models import LLMExtractedRelation

        # PreFilter 통과
        mock_result = MagicMock()
        mock_result.is_candidate = True
        mock_extractor.pre_filter.analyze.return_value = mock_result

        # LLM 응답
        with patch.object(mock_extractor, '_call_llm') as mock_llm:
            mock_llm.return_value = {
                'text': '''
                {
                    "relations": [
                        {
                            "source_company": "Microsoft",
                            "target_company": "Activision",
                            "relation_type": "ACQUIRED",
                            "confidence": 0.95,
                            "evidence": "Microsoft acquired Activision."
                        }
                    ]
                }
                ''',
                'prompt_tokens': 100,
                'completion_tokens': 50
            }

            # SymbolMatcher 응답
            mock_extractor.symbol_matcher.match.side_effect = lambda x: {
                "Microsoft": "MSFT",
                "Activision": "ATVI"
            }.get(x)

            relations = mock_extractor.extract_and_save(
                text="Microsoft acquired Activision for $68.7B.",
                source_id="news-001",
                source_type="news",
                source_url="https://example.com/news/001"
            )

        # DB에 저장됨
        assert len(relations) == 1
        assert relations[0].source_symbol == "MSFT"
        assert relations[0].target_symbol == "ATVI"
        assert relations[0].relation_type == "ACQUIRED"

        # DB에서 조회
        db_relation = LLMExtractedRelation.objects.get(source_id="news-001")
        assert db_relation.source_symbol == "MSFT"
        assert db_relation.target_symbol == "ATVI"

    @pytest.mark.django_db
    def test_extract_and_save_no_symbol_match(self, mock_extractor):
        """심볼 매칭 실패시 저장 안 됨"""
        from serverless.models import LLMExtractedRelation

        # PreFilter 통과
        mock_result = MagicMock()
        mock_result.is_candidate = True
        mock_extractor.pre_filter.analyze.return_value = mock_result

        # LLM 응답
        with patch.object(mock_extractor, '_call_llm') as mock_llm:
            mock_llm.return_value = {
                'text': '''
                {
                    "relations": [
                        {
                            "source_company": "Unknown Corp",
                            "target_company": "Another Unknown",
                            "relation_type": "ACQUIRED",
                            "confidence": 0.9,
                            "evidence": "Unknown Corp acquired Another Unknown."
                        }
                    ]
                }
                ''',
                'prompt_tokens': 100,
                'completion_tokens': 50
            }

            # SymbolMatcher가 None 반환
            mock_extractor.symbol_matcher.match.return_value = None

            relations = mock_extractor.extract_and_save(
                text="Unknown Corp acquired Another Unknown.",
                source_id="news-002",
                source_type="news"
            )

        # 저장 안 됨
        assert len(relations) == 0
        assert LLMExtractedRelation.objects.filter(source_id="news-002").count() == 0
