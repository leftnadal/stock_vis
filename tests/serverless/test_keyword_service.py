"""
Market Movers 키워드 생성 서비스 테스트
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from django.utils import timezone

from serverless.services.keyword_service import KeywordGenerationService
from serverless.models import StockKeyword, MarketMover


@pytest.mark.django_db
class TestKeywordGenerationService:
    """KeywordGenerationService 단위 테스트"""

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        return KeywordGenerationService()

    @pytest.fixture
    def sample_mover(self):
        """샘플 MarketMover 데이터"""
        today = timezone.now().date()
        return MarketMover.objects.create(
            date=today,
            mover_type='gainers',
            rank=1,
            symbol='NVDA',
            company_name='NVIDIA Corporation',
            price=Decimal('525.32'),
            change_percent=Decimal('8.45'),
            volume=52400000,
            sector='Technology',
            industry='Semiconductors',
        )

    def test_build_prompt(self, service):
        """프롬프트 구성 테스트"""
        prompt = service._build_prompt(
            symbol='NVDA',
            company_name='NVIDIA',
            mover_type='gainers',
            change_percent=8.45,
            sector='Technology',
            industry='Semiconductors'
        )

        assert 'NVDA' in prompt
        assert 'NVIDIA' in prompt
        assert '급등' in prompt
        assert '+8.45%' in prompt
        assert 'Technology' in prompt

    def test_parse_keywords_valid_json(self, service):
        """키워드 파싱 - 정상 JSON"""
        text = '["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]'
        keywords = service._parse_keywords(text)

        assert len(keywords) == 3
        assert "AI 반도체 수요" in keywords

    def test_parse_keywords_with_code_block(self, service):
        """키워드 파싱 - 코드 블록 포함"""
        text = '```json\n["AI 반도체", "실적 호조"]\n```'
        keywords = service._parse_keywords(text)

        assert len(keywords) == 2
        assert "AI 반도체" in keywords

    def test_parse_keywords_limit_to_five(self, service):
        """키워드 파싱 - 5개 제한"""
        text = '["A", "B", "C", "D", "E", "F", "G"]'
        keywords = service._parse_keywords(text)

        assert len(keywords) == 5

    def test_parse_keywords_invalid_json(self, service):
        """키워드 파싱 - 잘못된 JSON"""
        text = 'This is not JSON'

        with pytest.raises(Exception):
            service._parse_keywords(text)

    @patch.object(KeywordGenerationService, '_call_llm_sync')
    def test_generate_keyword_success(self, mock_llm, service, sample_mover):
        """키워드 생성 - 성공"""
        # Given: LLM이 정상 응답
        mock_llm.return_value = (
            ["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"],
            {'input_tokens': 200, 'output_tokens': 50}
        )

        # When: 키워드 생성
        result = service.generate_keyword(
            symbol=sample_mover.symbol,
            company_name=sample_mover.company_name,
            date=sample_mover.date,
            mover_type=sample_mover.mover_type,
            change_percent=float(sample_mover.change_percent),
            sector=sample_mover.sector,
            industry=sample_mover.industry
        )

        # Then: 성공 상태 반환
        assert result['status'] == 'completed'
        assert len(result['keywords']) == 3
        assert "AI 반도체 수요" in result['keywords']
        assert result['error_message'] is None
        assert result['metadata']['prompt_tokens'] == 200
        assert result['metadata']['generation_time_ms'] >= 0

    @patch.object(KeywordGenerationService, '_call_llm_sync')
    def test_generate_keyword_fallback_on_llm_failure(self, mock_llm, service):
        """키워드 생성 - LLM 실패 시 Fallback"""
        # Given: LLM 호출 실패
        mock_llm.side_effect = Exception("API Error")

        # When: 키워드 생성
        result = service.generate_keyword(
            symbol='NVDA',
            company_name='NVIDIA',
            date=timezone.now().date(),
            mover_type='gainers',
            change_percent=8.45,
        )

        # Then: Fallback 키워드 반환
        assert result['status'] == 'failed'
        assert result['keywords'] == ["급등", "거래량 증가", "모멘텀"]
        assert "API Error" in result['error_message']

    @patch.object(KeywordGenerationService, '_call_llm_sync')
    def test_generate_keyword_fallback_on_insufficient_keywords(self, mock_llm, service):
        """키워드 생성 - 키워드 부족 시 Fallback"""
        # Given: LLM이 2개만 반환 (3개 미만)
        mock_llm.return_value = (
            ["AI 반도체"],
            {'input_tokens': 200, 'output_tokens': 20}
        )

        # When: 키워드 생성
        result = service.generate_keyword(
            symbol='NVDA',
            company_name='NVIDIA',
            date=timezone.now().date(),
            mover_type='gainers',
            change_percent=8.45,
        )

        # Then: Fallback 키워드 반환
        assert result['status'] == 'failed'
        assert result['keywords'] == ["급등", "거래량 증가", "모멘텀"]
        assert "키워드 개수 부족" in result['error_message']

    @pytest.mark.django_db
    @patch.object(KeywordGenerationService, '_call_llm_sync')
    def test_batch_generate_success(self, mock_llm, service, sample_mover):
        """배치 생성 - 성공"""
        # Given: LLM이 정상 응답
        mock_llm.return_value = (
            ["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"],
            {'input_tokens': 200, 'output_tokens': 50}
        )

        # When: 배치 생성
        results = service.batch_generate(
            date=sample_mover.date,
            mover_type='gainers',
            limit=1
        )

        # Then: 성공 카운트
        assert results['success'] == 1
        assert results['failed'] == 0
        assert results['skipped'] == 0

        # DB 저장 확인
        keyword = StockKeyword.objects.get(
            symbol=sample_mover.symbol,
            date=sample_mover.date
        )
        assert keyword.status == 'completed'
        assert len(keyword.keywords) == 3

    @pytest.mark.django_db
    @patch.object(KeywordGenerationService, '_call_llm_sync')
    def test_batch_generate_skip_existing(self, mock_llm, service, sample_mover):
        """배치 생성 - 이미 생성된 키워드 스킵"""
        # Given: 이미 생성된 키워드 존재
        StockKeyword.objects.create(
            symbol=sample_mover.symbol,
            company_name=sample_mover.company_name,
            date=sample_mover.date,
            keywords=["기존 키워드"],
            status='completed'
        )

        # When: 배치 생성
        results = service.batch_generate(
            date=sample_mover.date,
            mover_type='gainers',
            limit=1
        )

        # Then: 스킵
        assert results['skipped'] == 1
        assert results['success'] == 0
        assert mock_llm.call_count == 0

    @patch('django.core.cache.cache.delete')
    def test_invalidate_cache_after_generation(self, mock_cache_delete, service):
        """캐시 무효화 테스트"""
        # When: 캐시 무효화
        today = timezone.now().date()
        service.invalidate_cache_after_generation(today, 'gainers')

        # Then: cache.delete() 호출
        mock_cache_delete.assert_called_once_with(
            f'movers_with_keywords:{today}:gainers'
        )
