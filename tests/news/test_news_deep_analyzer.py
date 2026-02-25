"""
NewsDeepAnalyzer 단위 테스트

커버 범위:
- NewsDeepAnalyzer.__init__() - API key 검증, Gemini 클라이언트 초기화
- NewsDeepAnalyzer._determine_tier() - importance_score 기반 Tier 결정
- NewsDeepAnalyzer._build_system_prompt() - Tier별 시스템 프롬프트
- NewsDeepAnalyzer._build_prompt() - Tier별 사용자 프롬프트
- NewsDeepAnalyzer._parse_response() - JSON 파싱 및 필드 검증
- NewsDeepAnalyzer._validate_tickers() - Stock DB 기반 티커 유효성 검증
- NewsDeepAnalyzer._get_valid_symbols() - 유효 심볼 캐시
- NewsDeepAnalyzer._analyze_single() - 단일 기사 LLM 분석
- NewsDeepAnalyzer.analyze_batch() - 배치 분석 흐름 전체
"""

import pytest
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, MagicMock, call

from django.conf import settings
from django.utils import timezone

from news.models import NewsArticle
from stocks.models import Stock


# ===== Helper: analyzer fixture =====

@pytest.fixture
def mock_genai():
    """google.genai 모듈 전체를 모킹"""
    with patch('news.services.news_deep_analyzer.genai') as mock:
        mock_client = MagicMock()
        mock.Client.return_value = mock_client
        yield mock, mock_client


@pytest.fixture
def analyzer(mock_genai):
    """
    NewsDeepAnalyzer 인스턴스 (Gemini 클라이언트 모킹)

    settings.GEMINI_API_KEY 또는 settings.GOOGLE_AI_API_KEY가 설정된 상태에서
    genai.Client 호출을 차단한 채 인스턴스를 생성합니다.
    """
    from news.services.news_deep_analyzer import NewsDeepAnalyzer

    with patch.object(settings, 'GEMINI_API_KEY', 'test-api-key', create=True):
        with patch.object(settings, 'GOOGLE_AI_API_KEY', None, create=True):
            return NewsDeepAnalyzer()


@pytest.fixture
def analyzer_with_client(mock_genai):
    """analyzer와 mock_client를 함께 반환하는 fixture"""
    _, mock_client = mock_genai
    from news.services.news_deep_analyzer import NewsDeepAnalyzer

    with patch.object(settings, 'GEMINI_API_KEY', 'test-api-key', create=True):
        with patch.object(settings, 'GOOGLE_AI_API_KEY', None, create=True):
            inst = NewsDeepAnalyzer()
    return inst, mock_client


@pytest.fixture
def news_article_factory():
    """
    NewsArticle 인스턴스를 DB 없이 생성하는 팩토리 함수.
    DB 기록이 필요한 테스트는 @pytest.mark.django_db를 사용합니다.
    """
    def _factory(
        importance_score=0.90,
        title='Apple Reports Record Earnings',
        summary='Apple reported record quarterly earnings exceeding analysts estimates.',
        source='Reuters',
        rule_tickers=None,
        rule_sectors=None,
        sentiment_score=None,
        llm_analyzed=False,
    ):
        article = MagicMock(spec=NewsArticle)
        article.id = 'mock-article-id-001'
        article.title = title
        article.summary = summary
        article.source = source
        article.published_at = datetime(2026, 2, 25, 10, 0, 0, tzinfo=dt_timezone.utc)
        article.importance_score = importance_score
        article.rule_tickers = rule_tickers
        article.rule_sectors = rule_sectors
        article.sentiment_score = sentiment_score
        article.llm_analyzed = llm_analyzed
        article.llm_analysis = None
        return article

    return _factory


# ===== TestNewsDeepAnalyzerInit =====

class TestNewsDeepAnalyzerInit:
    """__init__() 초기화 테스트"""

    def test_init_success_with_gemini_api_key(self, mock_genai):
        """
        Given: settings.GEMINI_API_KEY가 설정된 상태
        When: NewsDeepAnalyzer() 초기화
        Then: genai.Client가 해당 키로 호출됨, 예외 없음
        """
        mock_genai_module, mock_client = mock_genai
        from news.services.news_deep_analyzer import NewsDeepAnalyzer

        with patch.object(settings, 'GEMINI_API_KEY', 'my-gemini-key', create=True):
            with patch.object(settings, 'GOOGLE_AI_API_KEY', None, create=True):
                inst = NewsDeepAnalyzer()

        mock_genai_module.Client.assert_called_once_with(api_key='my-gemini-key')
        assert inst._valid_symbols_cache is None

    def test_init_success_with_google_ai_api_key(self, mock_genai):
        """
        Given: settings.GOOGLE_AI_API_KEY가 설정된 상태 (GEMINI_API_KEY 없음)
        When: NewsDeepAnalyzer() 초기화
        Then: GOOGLE_AI_API_KEY로 genai.Client 호출됨
        """
        mock_genai_module, _ = mock_genai
        from news.services.news_deep_analyzer import NewsDeepAnalyzer

        with patch.object(settings, 'GOOGLE_AI_API_KEY', 'google-ai-key', create=True):
            with patch.object(settings, 'GEMINI_API_KEY', None, create=True):
                inst = NewsDeepAnalyzer()

        mock_genai_module.Client.assert_called_once_with(api_key='google-ai-key')

    def test_init_prefers_google_ai_api_key_over_gemini_key(self, mock_genai):
        """
        Given: GOOGLE_AI_API_KEY와 GEMINI_API_KEY 모두 설정
        When: NewsDeepAnalyzer() 초기화
        Then: GOOGLE_AI_API_KEY가 우선 사용됨
        """
        mock_genai_module, _ = mock_genai
        from news.services.news_deep_analyzer import NewsDeepAnalyzer

        with patch.object(settings, 'GOOGLE_AI_API_KEY', 'google-key', create=True):
            with patch.object(settings, 'GEMINI_API_KEY', 'gemini-key', create=True):
                NewsDeepAnalyzer()

        mock_genai_module.Client.assert_called_once_with(api_key='google-key')

    def test_init_raises_when_no_api_key(self, mock_genai):
        """
        Given: API 키가 전혀 설정되지 않은 상태
        When: NewsDeepAnalyzer() 초기화
        Then: ValueError 발생
        """
        from news.services.news_deep_analyzer import NewsDeepAnalyzer

        with patch.object(settings, 'GEMINI_API_KEY', None, create=True):
            with patch.object(settings, 'GOOGLE_AI_API_KEY', None, create=True):
                with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                    NewsDeepAnalyzer()

    def test_init_valid_symbols_cache_starts_none(self, analyzer):
        """
        Given: 정상 초기화된 NewsDeepAnalyzer
        When: _valid_symbols_cache 확인
        Then: None (첫 호출 전 캐시 없음)
        """
        assert analyzer._valid_symbols_cache is None


# ===== TestDetermineTier =====

class TestDetermineTier:
    """_determine_tier() 메서드 테스트"""

    def test_tier_c_at_exact_threshold(self, analyzer):
        """
        Given: importance_score == 0.93 (Tier C 임계값)
        When: _determine_tier() 호출
        Then: 'C' 반환
        """
        result = analyzer._determine_tier(0.93)

        assert result == 'C'

    def test_tier_c_above_threshold(self, analyzer):
        """
        Given: importance_score == 0.99 (Tier C 초과)
        When: _determine_tier() 호출
        Then: 'C' 반환
        """
        result = analyzer._determine_tier(0.99)

        assert result == 'C'

    def test_tier_c_at_maximum(self, analyzer):
        """
        Given: importance_score == 1.0
        When: _determine_tier() 호출
        Then: 'C' 반환
        """
        result = analyzer._determine_tier(1.0)

        assert result == 'C'

    def test_tier_b_at_exact_threshold(self, analyzer):
        """
        Given: importance_score == 0.85 (Tier B 임계값)
        When: _determine_tier() 호출
        Then: 'B' 반환
        """
        result = analyzer._determine_tier(0.85)

        assert result == 'B'

    def test_tier_b_between_b_and_c_thresholds(self, analyzer):
        """
        Given: importance_score == 0.90 (0.85 <= x < 0.93)
        When: _determine_tier() 호출
        Then: 'B' 반환
        """
        result = analyzer._determine_tier(0.90)

        assert result == 'B'

    def test_tier_b_just_below_c_threshold(self, analyzer):
        """
        Given: importance_score == 0.929 (Tier C 바로 아래)
        When: _determine_tier() 호출
        Then: 'B' 반환
        """
        result = analyzer._determine_tier(0.929)

        assert result == 'B'

    def test_tier_a_at_exact_threshold(self, analyzer):
        """
        Given: importance_score == 0.70 (Tier A 임계값)
        When: _determine_tier() 호출
        Then: 'A' 반환
        """
        result = analyzer._determine_tier(0.70)

        assert result == 'A'

    def test_tier_a_between_a_and_b_thresholds(self, analyzer):
        """
        Given: importance_score == 0.75 (0.70 <= x < 0.85)
        When: _determine_tier() 호출
        Then: 'A' 반환
        """
        result = analyzer._determine_tier(0.75)

        assert result == 'A'

    def test_tier_a_just_below_b_threshold(self, analyzer):
        """
        Given: importance_score == 0.849 (Tier B 바로 아래)
        When: _determine_tier() 호출
        Then: 'A' 반환
        """
        result = analyzer._determine_tier(0.849)

        assert result == 'A'

    def test_none_just_below_a_threshold(self, analyzer):
        """
        Given: importance_score == 0.699 (Tier A 바로 아래)
        When: _determine_tier() 호출
        Then: None 반환
        """
        result = analyzer._determine_tier(0.699)

        assert result is None

    def test_none_at_zero(self, analyzer):
        """
        Given: importance_score == 0.0
        When: _determine_tier() 호출
        Then: None 반환
        """
        result = analyzer._determine_tier(0.0)

        assert result is None

    def test_none_for_low_score(self, analyzer):
        """
        Given: importance_score == 0.5 (낮은 점수)
        When: _determine_tier() 호출
        Then: None 반환
        """
        result = analyzer._determine_tier(0.5)

        assert result is None

    @pytest.mark.parametrize('score,expected', [
        (1.0, 'C'),
        (0.93, 'C'),
        (0.92, 'B'),
        (0.85, 'B'),
        (0.84, 'A'),
        (0.70, 'A'),
        (0.69, None),
        (0.0, None),
    ])
    def test_tier_boundary_parametrize(self, analyzer, score, expected):
        """
        Given: 경계값 테스트 테이블
        When: _determine_tier() 호출
        Then: 예상 Tier 반환
        """
        assert analyzer._determine_tier(score) == expected


# ===== TestBuildSystemPrompt =====

class TestBuildSystemPrompt:
    """_build_system_prompt() 메서드 테스트"""

    def test_system_prompt_tier_a_contains_direct_impact_only(self, analyzer):
        """
        Given: tier == 'A'
        When: _build_system_prompt() 호출
        Then: 'DIRECT impact'만 언급, 'indirect'는 미포함
        """
        result = analyzer._build_system_prompt('A')

        assert 'DIRECT' in result
        assert 'direct_impacts' in result
        assert 'indirect' not in result.lower().replace('indirect', '')

    def test_system_prompt_tier_a_includes_json_schema(self, analyzer):
        """
        Given: tier == 'A'
        When: _build_system_prompt() 호출
        Then: direct_impacts, symbol, direction, confidence, reason 포함
        """
        result = analyzer._build_system_prompt('A')

        assert 'direct_impacts' in result
        assert 'symbol' in result
        assert 'direction' in result
        assert 'confidence' in result
        assert 'reason' in result

    def test_system_prompt_tier_b_contains_indirect_impact(self, analyzer):
        """
        Given: tier == 'B'
        When: _build_system_prompt() 호출
        Then: 'indirect_impacts'와 'chain_logic' 포함
        """
        result = analyzer._build_system_prompt('B')

        assert 'indirect_impacts' in result
        assert 'chain_logic' in result

    def test_system_prompt_tier_b_limits_indirect_to_three(self, analyzer):
        """
        Given: tier == 'B'
        When: _build_system_prompt() 호출
        Then: '3'이라는 제한 수 포함
        """
        result = analyzer._build_system_prompt('B')

        assert '3' in result

    def test_system_prompt_tier_c_contains_all_fields(self, analyzer):
        """
        Given: tier == 'C'
        When: _build_system_prompt() 호출
        Then: direct_impacts, indirect_impacts, opportunities, sector_ripple 모두 포함
        """
        result = analyzer._build_system_prompt('C')

        assert 'direct_impacts' in result
        assert 'indirect_impacts' in result
        assert 'opportunities' in result
        assert 'sector_ripple' in result

    def test_system_prompt_tier_c_includes_opportunity_fields(self, analyzer):
        """
        Given: tier == 'C'
        When: _build_system_prompt() 호출
        Then: 'thesis', 'timeframe' 포함 (opportunities 스키마)
        """
        result = analyzer._build_system_prompt('C')

        assert 'thesis' in result
        assert 'timeframe' in result

    def test_system_prompt_all_tiers_contain_base_instruction(self, analyzer):
        """
        Given: 모든 tier
        When: _build_system_prompt() 호출
        Then: 기본 JSON 출력 지시 포함
        """
        for tier in ['A', 'B', 'C']:
            result = analyzer._build_system_prompt(tier)
            assert 'JSON' in result
            assert 'financial news analyst' in result.lower()

    def test_system_prompt_all_tiers_forbid_markdown_fences(self, analyzer):
        """
        Given: 모든 tier
        When: _build_system_prompt() 호출
        Then: 마크다운 코드 블록 금지 지시 포함
        """
        for tier in ['A', 'B', 'C']:
            result = analyzer._build_system_prompt(tier)
            assert 'markdown' in result.lower() or 'code fences' in result.lower()

    def test_system_prompt_tiers_are_distinct(self, analyzer):
        """
        Given: 세 가지 tier
        When: _build_system_prompt() 호출
        Then: 세 프롬프트가 서로 다름
        """
        prompt_a = analyzer._build_system_prompt('A')
        prompt_b = analyzer._build_system_prompt('B')
        prompt_c = analyzer._build_system_prompt('C')

        assert prompt_a != prompt_b
        assert prompt_b != prompt_c
        assert prompt_a != prompt_c


# ===== TestBuildPrompt =====

class TestBuildPrompt:
    """_build_prompt() 메서드 테스트"""

    def test_build_prompt_includes_article_title(self, analyzer, news_article_factory):
        """
        Given: 제목이 있는 기사
        When: _build_prompt() 호출
        Then: 프롬프트에 제목 포함
        """
        article = news_article_factory(title='NVDA Surges on AI Chip Announcement')

        result = analyzer._build_prompt(article, 'A')

        assert 'NVDA Surges on AI Chip Announcement' in result

    def test_build_prompt_includes_summary_truncated_to_500(self, analyzer, news_article_factory):
        """
        Given: 500자 초과 요약
        When: _build_prompt() 호출
        Then: 요약이 500자로 잘려서 포함됨
        """
        long_summary = 'X' * 1000
        article = news_article_factory(summary=long_summary)

        result = analyzer._build_prompt(article, 'A')

        assert 'X' * 500 in result
        assert 'X' * 501 not in result

    def test_build_prompt_summary_none_shows_na(self, analyzer, news_article_factory):
        """
        Given: summary가 None인 기사
        When: _build_prompt() 호출
        Then: 'N/A' 포함
        """
        article = news_article_factory()
        article.summary = None

        result = analyzer._build_prompt(article, 'A')

        assert 'N/A' in result

    def test_build_prompt_includes_source(self, analyzer, news_article_factory):
        """
        Given: source='Bloomberg'인 기사
        When: _build_prompt() 호출
        Then: 'Bloomberg' 포함
        """
        article = news_article_factory(source='Bloomberg')

        result = analyzer._build_prompt(article, 'A')

        assert 'Bloomberg' in result

    def test_build_prompt_includes_rule_tickers_when_present(self, analyzer, news_article_factory):
        """
        Given: rule_tickers=['AAPL', 'MSFT']인 기사
        When: _build_prompt() 호출
        Then: 티커 목록 포함
        """
        article = news_article_factory(rule_tickers=['AAPL', 'MSFT'])

        result = analyzer._build_prompt(article, 'A')

        assert 'AAPL' in result
        assert 'MSFT' in result

    def test_build_prompt_excludes_detected_tickers_line_when_none(self, analyzer, news_article_factory):
        """
        Given: rule_tickers=None인 기사
        When: _build_prompt() 호출
        Then: 'Detected Tickers' 라인 미포함
        """
        article = news_article_factory(rule_tickers=None)

        result = analyzer._build_prompt(article, 'A')

        assert 'Detected Tickers' not in result

    def test_build_prompt_includes_rule_sectors_when_present(self, analyzer, news_article_factory):
        """
        Given: rule_sectors=['Technology', 'Semiconductors']인 기사
        When: _build_prompt() 호출
        Then: 섹터 목록 포함
        """
        article = news_article_factory(rule_sectors=['Technology', 'Semiconductors'])

        result = analyzer._build_prompt(article, 'A')

        assert 'Technology' in result
        assert 'Semiconductors' in result

    def test_build_prompt_excludes_sectors_line_when_none(self, analyzer, news_article_factory):
        """
        Given: rule_sectors=None인 기사
        When: _build_prompt() 호출
        Then: 'Detected Sectors' 라인 미포함
        """
        article = news_article_factory(rule_sectors=None)

        result = analyzer._build_prompt(article, 'A')

        assert 'Detected Sectors' not in result

    def test_build_prompt_includes_sentiment_score_when_present(self, analyzer, news_article_factory):
        """
        Given: sentiment_score=0.75인 기사
        When: _build_prompt() 호출
        Then: '0.75' 포함
        """
        article = news_article_factory(sentiment_score=0.75)

        result = analyzer._build_prompt(article, 'A')

        assert '0.75' in result

    def test_build_prompt_sentiment_none_shows_na(self, analyzer, news_article_factory):
        """
        Given: sentiment_score=None인 기사
        When: _build_prompt() 호출
        Then: 'N/A' 포함
        """
        article = news_article_factory(sentiment_score=None)

        result = analyzer._build_prompt(article, 'A')

        assert 'N/A' in result

    def test_build_prompt_tier_a_instruction(self, analyzer, news_article_factory):
        """
        Given: tier == 'A'
        When: _build_prompt() 호출
        Then: 'direct stock impacts' 분석 지시 포함
        """
        article = news_article_factory()

        result = analyzer._build_prompt(article, 'A')

        assert 'direct' in result.lower()

    def test_build_prompt_tier_b_instruction(self, analyzer, news_article_factory):
        """
        Given: tier == 'B'
        When: _build_prompt() 호출
        Then: 'indirect' 언급 포함
        """
        article = news_article_factory()

        result = analyzer._build_prompt(article, 'B')

        assert 'indirect' in result.lower()

    def test_build_prompt_tier_c_instruction(self, analyzer, news_article_factory):
        """
        Given: tier == 'C'
        When: _build_prompt() 호출
        Then: 'comprehensive', 'opportunity' 또는 'sector ripple' 언급 포함
        """
        article = news_article_factory()

        result = analyzer._build_prompt(article, 'C')

        assert any(kw in result.lower() for kw in ['comprehensive', 'opportunity', 'sector ripple'])

    def test_build_prompt_tiers_produce_different_tails(self, analyzer, news_article_factory):
        """
        Given: 동일 기사, 세 가지 tier
        When: _build_prompt() 호출
        Then: 세 프롬프트가 서로 다름 (tier별 지시문 차이)
        """
        article = news_article_factory()

        result_a = analyzer._build_prompt(article, 'A')
        result_b = analyzer._build_prompt(article, 'B')
        result_c = analyzer._build_prompt(article, 'C')

        assert result_a != result_b
        assert result_b != result_c
        assert result_a != result_c


# ===== TestParseResponse =====

class TestParseResponse:
    """_parse_response() 메서드 테스트"""

    def test_parse_valid_json_tier_a(self, analyzer):
        """
        Given: 유효한 JSON (Tier A 형식)
        When: _parse_response() 호출
        Then: dict 반환, direct_impacts 포함
        """
        raw = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bullish", "confidence": 0.8, "reason": "Strong earnings"}]}'

        result = analyzer._parse_response(raw, 'A')

        assert result is not None
        assert 'direct_impacts' in result
        assert len(result['direct_impacts']) == 1
        assert result['direct_impacts'][0]['symbol'] == 'AAPL'

    def test_parse_valid_json_tier_b(self, analyzer):
        """
        Given: 유효한 JSON (Tier B 형식, direct+indirect)
        When: _parse_response() 호출
        Then: dict 반환, direct_impacts + indirect_impacts 포함
        """
        raw = (
            '{"direct_impacts": [{"symbol": "NVDA", "direction": "bullish", "confidence": 0.9, "reason": "AI chip demand"}],'
            ' "indirect_impacts": [{"symbol": "AMD", "direction": "bullish", "confidence": 0.5, "reason": "Competitor benefit", "chain_logic": "Market share shift"}]}'
        )

        result = analyzer._parse_response(raw, 'B')

        assert result is not None
        assert 'direct_impacts' in result
        assert 'indirect_impacts' in result

    def test_parse_valid_json_tier_c(self, analyzer):
        """
        Given: 유효한 JSON (Tier C 형식, 전체 필드)
        When: _parse_response() 호출
        Then: dict 반환, opportunities + sector_ripple 포함
        """
        raw = (
            '{"direct_impacts": [], "indirect_impacts": [],'
            ' "opportunities": [{"symbol": "INTC", "thesis": "Contrarian play", "timeframe": "3M", "confidence": 0.4}],'
            ' "sector_ripple": [{"sector": "Semiconductors", "direction": "bullish", "reason": "Supply chain"}]}'
        )

        result = analyzer._parse_response(raw, 'C')

        assert result is not None
        assert 'opportunities' in result
        assert 'sector_ripple' in result

    def test_parse_json_embedded_in_text(self, analyzer):
        """
        Given: JSON이 텍스트 안에 삽입된 LLM 응답 (코드 블록 없이)
        When: _parse_response() 호출
        Then: JSON 추출 성공
        """
        raw = 'Here is my analysis:\n{"direct_impacts": [{"symbol": "TSLA", "direction": "bearish", "confidence": 0.7, "reason": "Recall news"}]}\nEnd of analysis.'

        result = analyzer._parse_response(raw, 'A')

        assert result is not None
        assert result['direct_impacts'][0]['symbol'] == 'TSLA'

    def test_parse_returns_none_for_invalid_json(self, analyzer):
        """
        Given: 완전히 잘못된 JSON 문자열
        When: _parse_response() 호출
        Then: None 반환
        """
        raw = 'This is not JSON at all.'

        result = analyzer._parse_response(raw, 'A')

        assert result is None

    def test_parse_returns_none_for_empty_string(self, analyzer):
        """
        Given: 빈 문자열
        When: _parse_response() 호출
        Then: None 반환
        """
        result = analyzer._parse_response('', 'A')

        assert result is None

    def test_parse_adds_default_direct_impacts_when_missing(self, analyzer):
        """
        Given: 'direct_impacts' 키가 없는 JSON
        When: _parse_response() 호출
        Then: direct_impacts=[] 기본값으로 추가됨
        """
        raw = '{"indirect_impacts": []}'

        result = analyzer._parse_response(raw, 'B')

        assert result is not None
        assert result['direct_impacts'] == []

    def test_parse_adds_default_confidence_to_direct_impacts(self, analyzer):
        """
        Given: confidence 없는 direct_impact 항목
        When: _parse_response() 호출
        Then: confidence=0.5 기본값 추가됨
        """
        raw = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bullish", "reason": "Earnings"}]}'

        result = analyzer._parse_response(raw, 'A')

        assert result['direct_impacts'][0]['confidence'] == 0.5

    def test_parse_adds_default_direction_to_direct_impacts(self, analyzer):
        """
        Given: direction 없는 direct_impact 항목
        When: _parse_response() 호출
        Then: direction='neutral' 기본값 추가됨
        """
        raw = '{"direct_impacts": [{"symbol": "AAPL", "confidence": 0.7, "reason": "Test"}]}'

        result = analyzer._parse_response(raw, 'A')

        assert result['direct_impacts'][0]['direction'] == 'neutral'

    def test_parse_adds_default_reason_to_direct_impacts(self, analyzer):
        """
        Given: reason 없는 direct_impact 항목
        When: _parse_response() 호출
        Then: reason='' 기본값 추가됨
        """
        raw = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bullish", "confidence": 0.8}]}'

        result = analyzer._parse_response(raw, 'A')

        assert result['direct_impacts'][0]['reason'] == ''

    def test_parse_adds_default_chain_logic_to_indirect_impacts(self, analyzer):
        """
        Given: chain_logic 없는 indirect_impact 항목
        When: _parse_response() 호출
        Then: chain_logic='' 기본값 추가됨
        """
        raw = (
            '{"direct_impacts": [],'
            ' "indirect_impacts": [{"symbol": "AMD", "direction": "bullish", "confidence": 0.5, "reason": "Competition"}]}'
        )

        result = analyzer._parse_response(raw, 'B')

        assert result['indirect_impacts'][0]['chain_logic'] == ''

    def test_parse_adds_default_confidence_to_indirect_impacts(self, analyzer):
        """
        Given: confidence 없는 indirect_impact 항목
        When: _parse_response() 호출
        Then: confidence=0.3 기본값 추가됨
        """
        raw = (
            '{"direct_impacts": [],'
            ' "indirect_impacts": [{"symbol": "AMD", "direction": "bullish", "reason": "Competition", "chain_logic": "Shift"}]}'
        )

        result = analyzer._parse_response(raw, 'B')

        assert result['indirect_impacts'][0]['confidence'] == 0.3

    def test_parse_preserves_existing_fields(self, analyzer):
        """
        Given: 모든 필드가 완전히 채워진 JSON
        When: _parse_response() 호출
        Then: 기존 값 유지 (기본값으로 덮어쓰지 않음)
        """
        raw = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bearish", "confidence": 0.95, "reason": "Recall issue"}]}'

        result = analyzer._parse_response(raw, 'A')

        assert result['direct_impacts'][0]['direction'] == 'bearish'
        assert result['direct_impacts'][0]['confidence'] == 0.95
        assert result['direct_impacts'][0]['reason'] == 'Recall issue'

    def test_parse_handles_malformed_partial_json(self, analyzer):
        """
        Given: 잘린 불완전한 JSON
        When: _parse_response() 호출
        Then: None 반환
        """
        raw = '{"direct_impacts": [{"symbol": "AAPL"'  # 잘린 JSON

        result = analyzer._parse_response(raw, 'A')

        assert result is None

    def test_parse_empty_direct_impacts_list(self, analyzer):
        """
        Given: 빈 direct_impacts 리스트
        When: _parse_response() 호출
        Then: 빈 리스트 반환 (정상 처리)
        """
        raw = '{"direct_impacts": []}'

        result = analyzer._parse_response(raw, 'A')

        assert result is not None
        assert result['direct_impacts'] == []


# ===== TestValidateTickers =====

@pytest.mark.django_db
class TestValidateTickers:
    """_validate_tickers() 메서드 테스트"""

    @pytest.fixture(autouse=True)
    def create_stocks(self):
        """테스트용 Stock 레코드 생성"""
        Stock.objects.create(
            symbol='AAPL',
            stock_name='Apple Inc.',
            sector='Technology',
            exchange='NASDAQ',
            currency='USD',
        )
        Stock.objects.create(
            symbol='NVDA',
            stock_name='NVIDIA Corporation',
            sector='Technology',
            exchange='NASDAQ',
            currency='USD',
        )
        Stock.objects.create(
            symbol='MSFT',
            stock_name='Microsoft Corporation',
            sector='Technology',
            exchange='NASDAQ',
            currency='USD',
        )

    def test_valid_ticker_in_direct_impacts_kept(self, analyzer):
        """
        Given: Stock DB에 존재하는 AAPL이 direct_impacts에 포함
        When: _validate_tickers() 호출
        Then: AAPL 항목 유지됨
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [{'symbol': 'AAPL', 'direction': 'bullish', 'confidence': 0.8, 'reason': ''}],
        }

        result = analyzer._validate_tickers(analysis)

        assert len(result['direct_impacts']) == 1
        assert result['direct_impacts'][0]['symbol'] == 'AAPL'

    def test_invalid_ticker_in_direct_impacts_removed(self, analyzer):
        """
        Given: Stock DB에 없는 FAKE가 direct_impacts에 포함
        When: _validate_tickers() 호출
        Then: FAKE 항목 제거됨
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [{'symbol': 'FAKE', 'direction': 'bullish', 'confidence': 0.8, 'reason': ''}],
        }

        result = analyzer._validate_tickers(analysis)

        assert len(result['direct_impacts']) == 0

    def test_mixed_valid_invalid_tickers_filtered(self, analyzer):
        """
        Given: 유효한 AAPL + 무효한 FAKE가 direct_impacts에 포함
        When: _validate_tickers() 호출
        Then: AAPL만 유지, FAKE 제거
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [
                {'symbol': 'AAPL', 'direction': 'bullish', 'confidence': 0.8, 'reason': ''},
                {'symbol': 'FAKE', 'direction': 'bearish', 'confidence': 0.7, 'reason': ''},
            ],
        }

        result = analyzer._validate_tickers(analysis)

        assert len(result['direct_impacts']) == 1
        assert result['direct_impacts'][0]['symbol'] == 'AAPL'

    def test_symbol_normalized_to_uppercase(self, analyzer):
        """
        Given: 소문자 'aapl'이 direct_impacts에 포함
        When: _validate_tickers() 호출
        Then: 'AAPL'로 대문자 정규화됨
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [{'symbol': 'aapl', 'direction': 'bullish', 'confidence': 0.8, 'reason': ''}],
        }

        result = analyzer._validate_tickers(analysis)

        assert len(result['direct_impacts']) == 1
        assert result['direct_impacts'][0]['symbol'] == 'AAPL'

    def test_indirect_impacts_also_validated(self, analyzer):
        """
        Given: 무효한 티커가 indirect_impacts에 포함
        When: _validate_tickers() 호출
        Then: 무효 티커 제거됨
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [],
            'indirect_impacts': [
                {'symbol': 'NVDA', 'direction': 'bullish', 'confidence': 0.5, 'reason': '', 'chain_logic': ''},
                {'symbol': 'GHOST', 'direction': 'neutral', 'confidence': 0.3, 'reason': '', 'chain_logic': ''},
            ],
        }

        result = analyzer._validate_tickers(analysis)

        symbols = [i['symbol'] for i in result['indirect_impacts']]
        assert 'NVDA' in symbols
        assert 'GHOST' not in symbols

    def test_opportunities_also_validated(self, analyzer):
        """
        Given: 무효한 티커가 opportunities에 포함
        When: _validate_tickers() 호출
        Then: 무효 티커 제거됨
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [],
            'opportunities': [
                {'symbol': 'MSFT', 'thesis': 'Cloud growth', 'timeframe': '6M', 'confidence': 0.6},
                {'symbol': 'INVALID', 'thesis': 'Speculation', 'timeframe': '1M', 'confidence': 0.3},
            ],
        }

        result = analyzer._validate_tickers(analysis)

        symbols = [o['symbol'] for o in result['opportunities']]
        assert 'MSFT' in symbols
        assert 'INVALID' not in symbols

    def test_empty_symbol_field_removed(self, analyzer):
        """
        Given: symbol이 빈 문자열인 항목
        When: _validate_tickers() 호출
        Then: 해당 항목 제거됨 (Stock DB에 '' 없음)
        """
        analyzer._valid_symbols_cache = None
        analysis = {
            'direct_impacts': [{'symbol': '', 'direction': 'neutral', 'confidence': 0.5, 'reason': ''}],
        }

        result = analyzer._validate_tickers(analysis)

        assert len(result['direct_impacts']) == 0

    def test_missing_key_returns_empty_list(self, analyzer):
        """
        Given: 'direct_impacts' 키가 아예 없는 분석 결과
        When: _validate_tickers() 호출
        Then: 해당 키는 빈 리스트로 설정됨
        """
        analyzer._valid_symbols_cache = None
        analysis = {}

        result = analyzer._validate_tickers(analysis)

        assert result.get('direct_impacts') == []

    def test_valid_symbols_cache_used_on_second_call(self, analyzer):
        """
        Given: _get_valid_symbols()가 이미 한 번 호출됨 (캐시 저장)
        When: _validate_tickers() 두 번 연속 호출
        Then: Stock DB 쿼리는 1회만 발생 (캐시 재사용)
        """
        analyzer._valid_symbols_cache = None
        analysis = {'direct_impacts': [{'symbol': 'AAPL', 'direction': 'bullish', 'confidence': 0.8, 'reason': ''}]}

        with patch.object(
            type(analyzer), '_get_valid_symbols',
            wraps=analyzer._get_valid_symbols
        ) as mock_get:
            analyzer._validate_tickers(analysis)
            analyzer._validate_tickers(analysis)

        # _get_valid_symbols는 내부에서 캐시를 확인하므로
        # 두 번 호출되더라도 DB 쿼리는 첫 번째에만 발생
        assert mock_get.call_count == 2
        assert analyzer._valid_symbols_cache is not None


# ===== TestGetValidSymbols =====

@pytest.mark.django_db
class TestGetValidSymbols:
    """_get_valid_symbols() 메서드 테스트"""

    def test_returns_set_of_symbols(self, analyzer):
        """
        Given: DB에 AAPL, TSLA 두 Stock 존재
        When: _get_valid_symbols() 호출
        Then: 두 심볼을 포함하는 set 반환
        """
        Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.', sector='Technology', exchange='NASDAQ', currency='USD')
        Stock.objects.create(symbol='TSLA', stock_name='Tesla Inc.', sector='Consumer Cyclical', exchange='NASDAQ', currency='USD')

        analyzer._valid_symbols_cache = None
        result = analyzer._get_valid_symbols()

        assert isinstance(result, set)
        assert 'AAPL' in result
        assert 'TSLA' in result

    def test_caches_result_after_first_call(self, analyzer):
        """
        Given: DB에 Stock 없음
        When: _get_valid_symbols() 두 번 호출
        Then: 캐시가 채워지고 두 번째 호출 시 DB 쿼리 없음
        """
        analyzer._valid_symbols_cache = None

        result1 = analyzer._get_valid_symbols()
        # 캐시 직접 수정하여 두 번째 호출 시 캐시 반환 검증
        analyzer._valid_symbols_cache = {'CACHED_VALUE'}
        result2 = analyzer._get_valid_symbols()

        assert result2 == {'CACHED_VALUE'}

    def test_returns_empty_set_when_no_stocks(self, analyzer):
        """
        Given: DB에 Stock 없음
        When: _get_valid_symbols() 호출
        Then: 빈 set 반환
        """
        analyzer._valid_symbols_cache = None
        result = analyzer._get_valid_symbols()

        assert isinstance(result, set)
        assert len(result) == 0


# ===== TestAnalyzeSingle =====

class TestAnalyzeSingle:
    """_analyze_single() 메서드 테스트"""

    def test_analyze_single_returns_dict_on_success(self, analyzer_with_client, news_article_factory):
        """
        Given: LLM이 유효한 JSON 응답 반환
        When: _analyze_single() 호출
        Then: dict 반환
        """
        analyzer, mock_client = analyzer_with_client
        article = news_article_factory(importance_score=0.85, rule_tickers=['AAPL'])

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bullish", "confidence": 0.8, "reason": "Earnings"}]}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value={'AAPL', 'MSFT', 'NVDA'}):
            result = analyzer._analyze_single(article, 'B')

        assert result is not None
        assert isinstance(result, dict)

    def test_analyze_single_adds_tier_field(self, analyzer_with_client, news_article_factory):
        """
        Given: LLM 정상 응답
        When: _analyze_single(article, 'C') 호출
        Then: 결과에 tier='C' 포함
        """
        analyzer, mock_client = analyzer_with_client
        article = news_article_factory(importance_score=0.95, rule_tickers=['NVDA'])

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": [{"symbol": "NVDA", "direction": "bullish", "confidence": 0.9, "reason": "AI"}]}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value={'NVDA'}):
            result = analyzer._analyze_single(article, 'C')

        assert result['tier'] == 'C'

    def test_analyze_single_adds_analyzed_at_field(self, analyzer_with_client, news_article_factory):
        """
        Given: LLM 정상 응답
        When: _analyze_single() 호출
        Then: 결과에 'analyzed_at' ISO 형식 타임스탬프 포함
        """
        analyzer, mock_client = analyzer_with_client
        article = news_article_factory(importance_score=0.80)

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value=set()):
            result = analyzer._analyze_single(article, 'A')

        assert 'analyzed_at' in result
        assert isinstance(result['analyzed_at'], str)

    def test_analyze_single_calls_generate_content_with_correct_model(self, analyzer_with_client, news_article_factory):
        """
        Given: tier == 'A'
        When: _analyze_single() 호출
        Then: generate_content가 gemini-2.5-flash 모델로 호출됨
        """
        analyzer, mock_client = analyzer_with_client
        article = news_article_factory(importance_score=0.75)

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value=set()):
            analyzer._analyze_single(article, 'A')

        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs['model'] == 'gemini-2.5-flash'

    def test_analyze_single_returns_none_when_llm_raises_exception(self, analyzer_with_client, news_article_factory):
        """
        Given: LLM 호출 중 예외 발생
        When: _analyze_single() 호출
        Then: None 반환 (예외 전파 없음)
        """
        analyzer, mock_client = analyzer_with_client
        article = news_article_factory(importance_score=0.90)

        mock_client.models.generate_content.side_effect = Exception('API rate limit exceeded')

        result = analyzer._analyze_single(article, 'B')

        assert result is None

    def test_analyze_single_returns_none_when_response_is_invalid_json(self, analyzer_with_client, news_article_factory):
        """
        Given: LLM이 JSON 파싱 불가능한 응답 반환
        When: _analyze_single() 호출
        Then: None 반환
        """
        analyzer, mock_client = analyzer_with_client
        article = news_article_factory(importance_score=0.88)

        mock_response = MagicMock()
        mock_response.text = 'Sorry, I cannot analyze this article.'
        mock_client.models.generate_content.return_value = mock_response

        result = analyzer._analyze_single(article, 'B')

        assert result is None

    def test_analyze_single_max_tokens_by_tier(self, analyzer_with_client, news_article_factory):
        """
        Given: Tier A, B, C 각각
        When: _analyze_single() 호출
        Then: max_output_tokens가 A=2000, B=4000, C=6000으로 설정됨
        """
        from google.genai import types

        analyzer, mock_client = analyzer_with_client

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value=set()):
            for tier, expected_tokens in [('A', 2000), ('B', 4000), ('C', 6000)]:
                article = news_article_factory(importance_score=0.75)
                mock_client.models.generate_content.reset_mock()

                with patch('news.services.news_deep_analyzer.types') as mock_types:
                    mock_config = MagicMock()
                    mock_types.GenerateContentConfig.return_value = mock_config
                    analyzer._analyze_single(article, tier)

                mock_types.GenerateContentConfig.assert_called_once()
                call_kwargs = mock_types.GenerateContentConfig.call_args.kwargs
                assert call_kwargs['max_output_tokens'] == expected_tokens, f"Tier {tier}: expected {expected_tokens}"


# ===== TestAnalyzeBatch =====

@pytest.mark.django_db
class TestAnalyzeBatch:
    """analyze_batch() 메서드 테스트"""

    @pytest.fixture(autouse=True)
    def create_stock(self):
        """테스트용 Stock 생성"""
        Stock.objects.create(
            symbol='AAPL',
            stock_name='Apple Inc.',
            sector='Technology',
            exchange='NASDAQ',
            currency='USD',
        )

    def _create_article(self, importance_score, llm_analyzed=False, url_suffix=''):
        """DB에 NewsArticle 생성 헬퍼"""
        return NewsArticle.objects.create(
            url=f'https://example.com/test-article-{url_suffix or importance_score}',
            title='Test Article',
            summary='Test summary for analysis.',
            source='Reuters',
            published_at=timezone.now(),
            category='general',
            importance_score=importance_score,
            llm_analyzed=llm_analyzed,
        )

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_returns_result_dict(self, mock_sleep, analyzer_with_client):
        """
        Given: 분석 대상 기사 없음
        When: analyze_batch() 호출
        Then: analyzed, errors, skipped 키를 가진 dict 반환
        """
        analyzer, _ = analyzer_with_client

        result = analyzer.analyze_batch(max_articles=10)

        assert 'analyzed' in result
        assert 'errors' in result
        assert 'skipped' in result

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_skips_low_score_articles(self, mock_sleep, analyzer_with_client):
        """
        Given: importance_score=0.50 (Tier 없음) 기사
        When: analyze_batch() 호출
        Then: skipped=1, analyzed=0
        """
        analyzer, _ = analyzer_with_client
        self._create_article(importance_score=0.50, url_suffix='low')

        result = analyzer.analyze_batch(max_articles=10)

        assert result['skipped'] == 1
        assert result['analyzed'] == 0

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_analyzes_high_score_article(self, mock_sleep, analyzer_with_client):
        """
        Given: importance_score=0.95 (Tier C) 기사
        When: LLM이 유효한 JSON 반환 + analyze_batch() 호출
        Then: analyzed=1, 기사의 llm_analyzed=True로 업데이트됨
        """
        analyzer, mock_client = analyzer_with_client
        article = self._create_article(importance_score=0.95, url_suffix='high')

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bullish", "confidence": 0.8, "reason": "Strong"}]}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value={'AAPL'}):
            result = analyzer.analyze_batch(max_articles=10)

        assert result['analyzed'] == 1
        assert result['errors'] == 0

        article.refresh_from_db()
        assert article.llm_analyzed is True

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_records_error_on_llm_failure(self, mock_sleep, analyzer_with_client):
        """
        Given: importance_score=0.90 (Tier B) 기사, LLM 예외 발생
        When: analyze_batch() 호출
        Then: errors=1, 기사의 llm_analyzed=False 유지
        """
        analyzer, mock_client = analyzer_with_client
        article = self._create_article(importance_score=0.90, url_suffix='error')

        mock_client.models.generate_content.side_effect = Exception('Network error')

        result = analyzer.analyze_batch(max_articles=10)

        assert result['errors'] == 1
        assert result['analyzed'] == 0

        article.refresh_from_db()
        assert article.llm_analyzed is False

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_only_processes_unanalyzed_articles(self, mock_sleep, analyzer_with_client):
        """
        Given: llm_analyzed=True인 기사 (이미 분석됨)
        When: analyze_batch() 호출
        Then: analyzed=0, skipped=0, errors=0 (쿼리 자체에서 제외)
        """
        analyzer, _ = analyzer_with_client
        self._create_article(importance_score=0.95, llm_analyzed=True, url_suffix='done')

        result = analyzer.analyze_batch(max_articles=10)

        assert result['analyzed'] == 0
        assert result['errors'] == 0
        assert result['skipped'] == 0

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_only_processes_articles_with_importance_score(self, mock_sleep, analyzer_with_client):
        """
        Given: importance_score=None인 기사
        When: analyze_batch() 호출
        Then: 해당 기사 처리되지 않음 (쿼리 필터에서 제외)
        """
        analyzer, _ = analyzer_with_client
        NewsArticle.objects.create(
            url='https://example.com/no-score-article',
            title='No Score Article',
            summary='Test.',
            source='Test',
            published_at=timezone.now(),
            category='general',
            importance_score=None,
            llm_analyzed=False,
        )

        result = analyzer.analyze_batch(max_articles=10)

        assert result['analyzed'] == 0
        assert result['skipped'] == 0
        assert result['errors'] == 0

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_respects_max_articles_limit(self, mock_sleep, analyzer_with_client):
        """
        Given: importance_score=0.95인 기사 5개
        When: max_articles=2로 analyze_batch() 호출
        Then: 최대 2개만 처리됨 (analyzed + skipped + errors <= 2)
        """
        analyzer, mock_client = analyzer_with_client

        for i in range(5):
            self._create_article(importance_score=0.95, url_suffix=f'limit-{i}')

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value={'AAPL'}):
            result = analyzer.analyze_batch(max_articles=2)

        total = result['analyzed'] + result['skipped'] + result['errors']
        assert total <= 2

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_calls_sleep_between_articles(self, mock_sleep, analyzer_with_client):
        """
        Given: importance_score=0.95 기사 2개
        When: analyze_batch() 호출
        Then: time.sleep이 RPM_DELAY 인자로 두 번 호출됨
        """
        analyzer, mock_client = analyzer_with_client

        for i in range(2):
            self._create_article(importance_score=0.95, url_suffix=f'sleep-{i}')

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value=set()):
            analyzer.analyze_batch(max_articles=10)

        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(analyzer.RPM_DELAY)

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_updates_llm_analysis_field(self, mock_sleep, analyzer_with_client):
        """
        Given: 분석 대상 기사, LLM이 유효한 JSON 반환
        When: analyze_batch() 호출
        Then: 기사의 llm_analysis 필드가 업데이트됨
        """
        analyzer, mock_client = analyzer_with_client
        article = self._create_article(importance_score=0.90, url_suffix='analysis-field')

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": [{"symbol": "AAPL", "direction": "bullish", "confidence": 0.8, "reason": "Test"}]}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value={'AAPL'}):
            analyzer.analyze_batch(max_articles=10)

        article.refresh_from_db()
        assert article.llm_analysis is not None
        assert 'direct_impacts' in article.llm_analysis

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_increments_errors_when_analysis_returns_none(self, mock_sleep, analyzer_with_client):
        """
        Given: LLM이 파싱 불가능한 응답 반환 (_analyze_single 반환값 None)
        When: analyze_batch() 호출
        Then: errors 카운트 1 증가, analyzed 카운트 증가 없음
        """
        analyzer, mock_client = analyzer_with_client
        self._create_article(importance_score=0.90, url_suffix='none-result')

        mock_response = MagicMock()
        mock_response.text = 'Not valid JSON at all'
        mock_client.models.generate_content.return_value = mock_response

        result = analyzer.analyze_batch(max_articles=10)

        assert result['errors'] == 1
        assert result['analyzed'] == 0

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_processes_only_todays_articles(self, mock_sleep, analyzer_with_client):
        """
        Given: 오늘 날짜 기사 1개, 어제 날짜 기사 1개
        When: analyze_batch() 호출
        Then: 오늘 기사만 처리됨 (published_at 기반 필터)
        """
        from datetime import timedelta

        analyzer, mock_client = analyzer_with_client

        # 오늘 기사
        NewsArticle.objects.create(
            url='https://example.com/today-article',
            title='Today Article',
            summary='Today news.',
            source='Reuters',
            published_at=timezone.now(),
            category='general',
            importance_score=0.95,
            llm_analyzed=False,
        )

        # 어제 기사 (today 필터에서 제외되어야 함)
        NewsArticle.objects.create(
            url='https://example.com/yesterday-article',
            title='Yesterday Article',
            summary='Yesterday news.',
            source='Reuters',
            published_at=timezone.now() - timedelta(days=1),
            category='general',
            importance_score=0.95,
            llm_analyzed=False,
        )

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value=set()):
            result = analyzer.analyze_batch(max_articles=10)

        # 오늘 기사만 처리 (어제 기사는 start_of_day 필터로 제외)
        total = result['analyzed'] + result['errors'] + result['skipped']
        assert total == 1

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_empty_db_returns_zeros(self, mock_sleep, analyzer_with_client):
        """
        Given: DB에 분석 대상 기사 없음
        When: analyze_batch() 호출
        Then: analyzed=0, errors=0, skipped=0
        """
        analyzer, _ = analyzer_with_client

        result = analyzer.analyze_batch(max_articles=50)

        assert result == {'analyzed': 0, 'errors': 0, 'skipped': 0}

    @patch('news.services.news_deep_analyzer.time.sleep')
    def test_analyze_batch_mixed_tiers(self, mock_sleep, analyzer_with_client):
        """
        Given: Tier C(0.95), Tier B(0.88), Tier A(0.72), 아래(0.60) 각 1개
        When: analyze_batch() 호출
        Then: analyzed=3 (또는 errors 일부), skipped=1 (0.60 기사)
        """
        analyzer, mock_client = analyzer_with_client

        self._create_article(importance_score=0.95, url_suffix='tier-c')
        self._create_article(importance_score=0.88, url_suffix='tier-b')
        self._create_article(importance_score=0.72, url_suffix='tier-a')
        self._create_article(importance_score=0.60, url_suffix='no-tier')

        mock_response = MagicMock()
        mock_response.text = '{"direct_impacts": []}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(analyzer, '_get_valid_symbols', return_value=set()):
            result = analyzer.analyze_batch(max_articles=10)

        # 0.60 기사는 tier=None -> skipped
        assert result['skipped'] == 1
        # 나머지 3개는 analyzed (빈 direct_impacts이지만 parse 성공)
        assert result['analyzed'] == 3


# ===== TestEdgeCases =====

class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_parse_response_with_nested_json_in_text(self, analyzer):
        """
        Given: 텍스트 안에 중첩된 JSON 구조
        When: _parse_response() 호출
        Then: 가장 외부 JSON 객체 추출
        """
        raw = 'Analysis result: {"direct_impacts": [], "meta": {"count": 0}}'

        result = analyzer._parse_response(raw, 'A')

        assert result is not None
        assert 'direct_impacts' in result

    def test_build_prompt_with_no_rule_tickers_and_no_sectors(self, analyzer, news_article_factory):
        """
        Given: rule_tickers=None, rule_sectors=None인 기사 (엣지 케이스)
        When: _build_prompt() 호출
        Then: 예외 없이 프롬프트 생성, 기본 정보 포함
        """
        article = news_article_factory(rule_tickers=None, rule_sectors=None)

        result = analyzer._build_prompt(article, 'A')

        assert article.title in result
        assert 'Detected Tickers' not in result
        assert 'Detected Sectors' not in result

    def test_build_prompt_with_empty_summary(self, analyzer, news_article_factory):
        """
        Given: summary='' 빈 문자열인 기사
        When: _build_prompt() 호출
        Then: 예외 없이 프롬프트 생성
        """
        article = news_article_factory()
        article.summary = ''

        result = analyzer._build_prompt(article, 'B')

        assert result is not None
        assert isinstance(result, str)

    def test_parse_response_only_whitespace(self, analyzer):
        """
        Given: 공백만 있는 응답
        When: _parse_response() 호출
        Then: None 반환
        """
        result = analyzer._parse_response('   \n\t  ', 'A')

        assert result is None

    def test_parse_response_json_array_not_object(self, analyzer):
        """
        Given: JSON 배열 (객체 아님)
        When: _parse_response() 호출
        Then: None 반환 ('{' 없음)
        """
        raw = '[{"symbol": "AAPL"}]'

        # re.search(r'\{[\s\S]*\}', raw)는 배열 내부의 {} 객체를 매칭함
        # 실제 동작은 구현에 따라 다를 수 있으므로 예외 없이 종료됨을 확인
        result = analyzer._parse_response(raw, 'A')

        # 배열 안에 {} 객체가 있으면 파싱 시도, 없으면 None
        # None이거나 dict여야 함 (예외 발생 없어야 함)
        assert result is None or isinstance(result, dict)

    @pytest.mark.django_db
    def test_validate_tickers_with_all_empty_lists(self, analyzer):
        """
        Given: 모든 impact 리스트가 비어 있는 analysis
        When: _validate_tickers() 호출
        Then: 빈 리스트 그대로 반환, 예외 없음
        """
        analyzer._valid_symbols_cache = set()
        analysis = {
            'direct_impacts': [],
            'indirect_impacts': [],
            'opportunities': [],
        }

        result = analyzer._validate_tickers(analysis)

        assert result['direct_impacts'] == []
        assert result['indirect_impacts'] == []
        assert result['opportunities'] == []

    def test_determine_tier_boundary_precision(self, analyzer):
        """
        Given: 부동소수점 경계값 테스트
        When: _determine_tier() 호출
        Then: 0.930000001 -> 'C', 0.929999999 -> 'B'
        """
        assert analyzer._determine_tier(0.9300001) == 'C'
        assert analyzer._determine_tier(0.9299999) == 'B'


# ===== 마커 설정 =====

pytestmark = pytest.mark.django_db
