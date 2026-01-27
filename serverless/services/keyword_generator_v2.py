"""
Market Movers 키워드 생성 서비스 V2

풍부한 컨텍스트(Overview + 뉴스)를 활용한 개선된 키워드 생성 시스템
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from django.conf import settings
from google import genai
from google.genai import types

from .keyword_prompts_v2 import EnhancedKeywordPromptBuilder, EnhancedKeywordResponseParser
from .keyword_context_builder import KeywordContextBuilder, ContextEnricher
from ..models import MarketMover

logger = logging.getLogger(__name__)


class EnhancedKeywordGenerator:
    """
    향상된 Market Movers 키워드 생성 서비스

    Features:
    - Overview + 뉴스 컨텍스트 활용
    - Gemini 2.5 Flash 사용 (저비용)
    - 배치 처리 (20개 종목 일괄 처리)
    - 토큰 최적화 (4000 토큰 이내)
    - Fallback 전략 (데이터 부족 시)
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 8000  # 배치 처리용
    TEMPERATURE = 0.3  # 일관된 키워드 생성

    # 배치 크기
    BATCH_SIZE = 20

    # 토큰 제한
    MAX_BATCH_TOKENS = 4000

    def __init__(self, language: str = "ko", enable_enrichment: bool = True):
        """
        Args:
            language: 키워드 언어 ('ko' 또는 'en')
            enable_enrichment: Overview/뉴스 보강 활성화
        """
        self.language = language
        self.enable_enrichment = enable_enrichment

        self.prompt_builder = EnhancedKeywordPromptBuilder(language=language)
        self.context_builder = KeywordContextBuilder()
        self.parser = EnhancedKeywordResponseParser()

        # Gemini API 클라이언트 초기화
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다."
            )
        self.client = genai.Client(api_key=api_key)

    async def generate_keywords_for_movers(
        self,
        mover_date: date,
        mover_type: str,
        max_stocks: int = 20
    ) -> List[Dict[str, Any]]:
        """
        특정 날짜/타입의 Market Movers에 대해 키워드 생성

        Args:
            mover_date: Market Movers 날짜
            mover_type: 'gainers', 'losers', 'actives'
            max_stocks: 최대 처리 종목 수 (기본 20)

        Returns:
            [
                {
                    'symbol': str,
                    'keywords': [
                        {'text': str, 'category': str, 'confidence': float},
                        ...
                    ],
                    'summary': str
                },
                ...
            ]
        """
        # MarketMover 조회
        movers = MarketMover.objects.filter(
            date=mover_date,
            mover_type=mover_type
        ).order_by('rank')[:max_stocks]

        if not movers:
            logger.warning(
                f"No movers found for {mover_date} {mover_type}"
            )
            return []

        # 컨텍스트 구성
        stock_contexts = []
        for mover in movers:
            context_data = self._prepare_context_data(mover)
            stock_contexts.append(context_data)

        # 배치 컨텍스트 구성 (토큰 제한)
        batch_contexts = self.context_builder.build_batch_contexts(
            stock_contexts,
            max_tokens=self.MAX_BATCH_TOKENS
        )

        if not batch_contexts:
            logger.warning("No contexts built (token limit exceeded)")
            return []

        logger.info(
            f"Generating keywords for {len(batch_contexts)} stocks. "
            f"Total estimated tokens: {sum(c['estimated_tokens'] for c in batch_contexts)}"
        )

        # LLM 호출 (비동기)
        try:
            response_text = await self._call_llm_batch(batch_contexts, mover_type)

            # 응답 파싱
            results = self.parser.parse_batch_response(response_text)

            logger.info(
                f"Successfully generated keywords for {len(results)}/{len(batch_contexts)} stocks"
            )

            return results

        except Exception as e:
            logger.exception(f"Failed to generate keywords: {e}")
            return []

    async def generate_keywords_single(
        self,
        mover: MarketMover
    ) -> Optional[Dict[str, Any]]:
        """
        단일 종목 키워드 생성

        Args:
            mover: MarketMover 인스턴스

        Returns:
            {
                'symbol': str,
                'keywords': [...],
                'summary': str
            }
            또는 None
        """
        context_data = self._prepare_context_data(mover)
        context = self.context_builder.build_stock_context(**context_data)

        logger.info(
            f"Generating keywords for {context_data['symbol']} "
            f"(has_overview={context['has_overview']}, has_news={context['has_news']})"
        )

        try:
            response_text = await self._call_llm_single(context, mover.mover_type)

            result = self.parser.parse_single_response(response_text)

            if result:
                logger.info(
                    f"Successfully generated {len(result['keywords'])} keywords for {context_data['symbol']}"
                )
            else:
                logger.warning(
                    f"Failed to parse keywords for {context_data['symbol']}"
                )

            return result

        except Exception as e:
            logger.exception(
                f"Failed to generate keywords for {context_data['symbol']}: {e}"
            )
            return None

    def _prepare_context_data(self, mover: MarketMover) -> Dict[str, Any]:
        """
        MarketMover 인스턴스를 컨텍스트 데이터로 변환

        Args:
            mover: MarketMover 인스턴스

        Returns:
            KeywordContextBuilder.build_stock_context에 전달할 데이터
        """
        price_data = {
            'price': float(mover.price) if mover.price else None,
            'change_percent': float(mover.change_percent) if mover.change_percent else None,
            'volume': int(mover.volume) if mover.volume else None,
            'open': float(mover.open_price) if mover.open_price else None,
            'high': float(mover.high) if mover.high else None,
            'low': float(mover.low) if mover.low else None,
        }

        indicators = {
            'rvol': float(mover.rvol) if mover.rvol else None,
            'trend_strength': float(mover.trend_strength) if mover.trend_strength else None,
            'sector_alpha': float(mover.sector_alpha) if mover.sector_alpha else None,
            'etf_sync_rate': float(mover.etf_sync_rate) if mover.etf_sync_rate else None,
            'volatility_pct': int(mover.volatility_pct) if mover.volatility_pct else None,
        }

        context_data = {
            'symbol': mover.symbol,
            'company_name': mover.company_name,
            'mover_type': mover.mover_type,
            'price_data': price_data,
            'indicators': indicators,
            'sector': mover.sector,
            'industry': mover.industry,
        }

        # Overview/뉴스 보강 (옵션)
        if self.enable_enrichment:
            overview = ContextEnricher.fetch_overview(mover.symbol)
            news = ContextEnricher.fetch_news(mover.symbol, days=7, limit=3)

            if overview:
                context_data['overview'] = overview
                logger.debug(f"{mover.symbol}: Overview enriched")

            if news:
                context_data['news'] = news
                logger.debug(f"{mover.symbol}: News enriched ({len(news)} articles)")

        return context_data

    async def _call_llm_batch(
        self,
        contexts: List[Dict[str, Any]],
        mover_type: str
    ) -> str:
        """
        LLM API 배치 호출

        Args:
            contexts: 컨텍스트 리스트
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            LLM 응답 텍스트
        """
        system_prompt = self.prompt_builder.get_system_prompt(mover_type)
        user_prompt = self.prompt_builder.build_batch_prompt(contexts, mover_type)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.MAX_TOKENS,
            temperature=self.TEMPERATURE,
        )

        # 비동기 호출
        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=user_prompt,
            config=config,
        )

        # 응답 텍스트 추출
        return self._extract_response_text(response)

    async def _call_llm_single(
        self,
        context: Dict[str, Any],
        mover_type: str
    ) -> str:
        """
        LLM API 단일 호출

        Args:
            context: 컨텍스트
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            LLM 응답 텍스트
        """
        system_prompt = self.prompt_builder.get_system_prompt(mover_type)
        user_prompt = self.prompt_builder.build_user_prompt(context)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2000,  # 단일 종목은 2000 토큰으로 충분
            temperature=self.TEMPERATURE,
        )

        # 비동기 호출
        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=user_prompt,
            config=config,
        )

        return self._extract_response_text(response)

    def _extract_response_text(self, response) -> str:
        """
        Gemini API 응답에서 텍스트 추출

        Args:
            response: Gemini API 응답 객체

        Returns:
            응답 텍스트
        """
        # 응답 텍스트 추출
        if hasattr(response, 'text') and response.text:
            return response.text

        # candidates에서 추출
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                    return candidate.content.parts[0].text

        raise ValueError("No text found in LLM response")

    def estimate_batch_cost(
        self,
        num_stocks: int
    ) -> Dict[str, Any]:
        """
        배치 처리 비용 추정

        Args:
            num_stocks: 종목 수

        Returns:
            {
                'input_tokens': int,
                'output_tokens': int,
                'total_tokens': int,
                'cost_usd': float
            }
        """
        # 대략적 토큰 추정
        # - 시스템 프롬프트: 1500 토큰
        # - 종목당 입력: 200 토큰 (Overview/뉴스 포함)
        # - 종목당 출력: 300 토큰 (키워드 5-7개 + summary)
        input_tokens = 1500 + (num_stocks * 200)
        output_tokens = num_stocks * 300
        total_tokens = input_tokens + output_tokens

        # Gemini 2.5 Flash 가격 (2025년 1월 기준)
        # Input: $0.30 / 1M tokens
        # Output: $1.20 / 1M tokens
        INPUT_COST_PER_1M = 0.30
        OUTPUT_COST_PER_1M = 1.20

        input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M

        total_cost = input_cost + output_cost

        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'input_cost_usd': round(input_cost, 6),
            'output_cost_usd': round(output_cost, 6),
            'total_cost_usd': round(total_cost, 6),
        }


# 동기 래퍼 함수 (Celery 태스크용)
def generate_keywords_sync_v2(
    mover_date: date,
    mover_type: str,
    language: str = "ko",
    max_stocks: int = 20,
    enable_enrichment: bool = True
) -> List[Dict[str, Any]]:
    """
    동기 키워드 생성 함수 (Celery 태스크용)

    Args:
        mover_date: Market Movers 날짜
        mover_type: 'gainers', 'losers', 'actives'
        language: 키워드 언어
        max_stocks: 최대 처리 종목 수
        enable_enrichment: Overview/뉴스 보강 활성화

    Returns:
        [{'symbol', 'keywords', 'summary'}, ...]
    """
    generator = EnhancedKeywordGenerator(
        language=language,
        enable_enrichment=enable_enrichment
    )

    # asyncio 이벤트 루프 실행
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    results = loop.run_until_complete(
        generator.generate_keywords_for_movers(
            mover_date=mover_date,
            mover_type=mover_type,
            max_stocks=max_stocks
        )
    )

    return results
