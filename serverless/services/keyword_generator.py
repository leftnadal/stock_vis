"""
Market Movers 키워드 생성 서비스

LLM을 활용하여 Market Movers 종목의 키워드를 자동 생성합니다.
Semantic Cache를 활용하여 비용을 절감하고, 배치 처리로 효율성을 높입니다.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from google import genai
from google.genai import types

from .keyword_prompts import KeywordPromptBuilder, KeywordResponseParser
from ..models import MarketMover

logger = logging.getLogger(__name__)


class KeywordGeneratorService:
    """
    Market Movers 키워드 생성 서비스

    Features:
    - Gemini 2.5 Flash 사용 (저비용)
    - 배치 처리 (20개 종목 일괄 처리)
    - Semantic Cache 활용 (유사 질문 캐싱)
    - 토큰 비용 추정 및 최적화
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 8000  # 배치 처리용 (20개 종목 * 300 토큰 = 6000 토큰)
    TEMPERATURE = 0.3  # 일관된 키워드 생성을 위해 낮게 설정

    # 배치 크기
    BATCH_SIZE = 20

    # 캐싱 TTL
    CACHE_TTL_DAYS = 7  # 7일간 캐시 유지

    def __init__(self, language: str = "ko"):
        """
        Args:
            language: 키워드 언어 ('ko' 또는 'en')
        """
        self.language = language
        self.prompt_builder = KeywordPromptBuilder(language=language)
        self.parser = KeywordResponseParser()

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
            list: [{'symbol', 'keywords', 'summary'}, ...]
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

        # 배치 프롬프트 구성
        stocks = []
        for mover in movers:
            stock_data = self._prepare_stock_data(mover)
            stocks.append(stock_data)

        # 배치 프롬프트 생성
        user_prompt = self.prompt_builder.build_batch_prompt(
            stocks=stocks,
            max_stocks=max_stocks
        )

        # 토큰 추정
        token_estimate = self.prompt_builder.estimate_tokens(
            num_stocks=len(stocks)
        )

        logger.info(
            f"Generating keywords for {len(stocks)} stocks. "
            f"Estimated tokens: {token_estimate['total_tokens']}"
        )

        # LLM 호출 (비동기)
        try:
            response_text = await self._call_llm(user_prompt)

            # 응답 파싱
            results = self.parser.parse_batch_response(
                response_text,
                language=self.language
            )

            logger.info(
                f"Successfully generated keywords for {len(results)}/{len(stocks)} stocks"
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
            dict: {'symbol', 'keywords', 'summary'} 또는 None
        """
        stock_data = self._prepare_stock_data(mover)

        user_prompt = self.prompt_builder.build_single_stock_prompt(
            symbol=stock_data['symbol'],
            company_name=stock_data['company_name'],
            mover_type=stock_data['mover_type'],
            price_data=stock_data['price_data'],
            indicators=stock_data['indicators'],
            sector=stock_data.get('sector'),
            industry=stock_data.get('industry')
        )

        logger.info(
            f"Generating keywords for {stock_data['symbol']}"
        )

        try:
            response_text = await self._call_llm(user_prompt)

            result = self.parser.parse_single_response(
                response_text,
                language=self.language
            )

            if result:
                logger.info(
                    f"Successfully generated keywords for {stock_data['symbol']}"
                )
            else:
                logger.warning(
                    f"Failed to parse keywords for {stock_data['symbol']}"
                )

            return result

        except Exception as e:
            logger.exception(
                f"Failed to generate keywords for {stock_data['symbol']}: {e}"
            )
            return None

    def _prepare_stock_data(self, mover: MarketMover) -> Dict[str, Any]:
        """
        MarketMover 인스턴스를 프롬프트용 데이터로 변환

        Args:
            mover: MarketMover 인스턴스

        Returns:
            dict: 프롬프트 빌더에 전달할 데이터
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

        return {
            'symbol': mover.symbol,
            'company_name': mover.company_name,
            'mover_type': mover.mover_type,
            'price_data': price_data,
            'indicators': indicators,
            'sector': mover.sector,
            'industry': mover.industry,
        }

    async def _call_llm(self, user_prompt: str) -> str:
        """
        LLM API 호출

        Args:
            user_prompt: 사용자 프롬프트

        Returns:
            str: LLM 응답 텍스트

        Raises:
            Exception: API 호출 실패
        """
        system_prompt = self.prompt_builder.get_system_prompt()

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.MAX_TOKENS,
            temperature=self.TEMPERATURE,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        # 비동기 호출
        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=user_prompt,
            config=config,
        )

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
            dict: {'input_tokens', 'output_tokens', 'cost_usd'}
        """
        token_estimate = self.prompt_builder.estimate_tokens(num_stocks)

        # Gemini 2.5 Flash 가격 (2025년 1월 기준)
        # Input: $0.30 / 1M tokens
        # Output: $1.20 / 1M tokens
        INPUT_COST_PER_1M = 0.30
        OUTPUT_COST_PER_1M = 1.20

        input_cost = (token_estimate['input_tokens'] / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (token_estimate['estimated_output_tokens'] / 1_000_000) * OUTPUT_COST_PER_1M

        total_cost = input_cost + output_cost

        return {
            'input_tokens': token_estimate['input_tokens'],
            'output_tokens': token_estimate['estimated_output_tokens'],
            'total_tokens': token_estimate['total_tokens'],
            'input_cost_usd': round(input_cost, 6),
            'output_cost_usd': round(output_cost, 6),
            'total_cost_usd': round(total_cost, 6),
        }


class KeywordCacheService:
    """
    키워드 캐싱 서비스

    Django ORM을 활용한 간단한 캐싱 (Redis 대신)
    """

    @staticmethod
    def get_cached_keywords(
        symbol: str,
        mover_date: date,
        language: str = "ko"
    ) -> Optional[Dict[str, Any]]:
        """
        캐시에서 키워드 조회

        Args:
            symbol: 심볼
            mover_date: Market Movers 날짜
            language: 키워드 언어

        Returns:
            dict: {'keywords', 'summary'} 또는 None
        """
        # TODO: KeywordCache 모델 구현 시 추가
        # 현재는 None 반환 (캐시 없음)
        return None

    @staticmethod
    def save_keywords(
        symbol: str,
        mover_date: date,
        keywords: List[Dict[str, Any]],
        summary: str,
        language: str = "ko"
    ):
        """
        키워드 캐싱

        Args:
            symbol: 심볼
            mover_date: Market Movers 날짜
            keywords: 키워드 리스트
            summary: 요약
            language: 키워드 언어
        """
        # TODO: KeywordCache 모델 구현 시 추가
        pass


# 동기 래퍼 함수 (Celery 태스크용)
def generate_keywords_sync(
    mover_date: date,
    mover_type: str,
    language: str = "ko",
    max_stocks: int = 20
) -> List[Dict[str, Any]]:
    """
    동기 키워드 생성 함수 (Celery 태스크용)

    Args:
        mover_date: Market Movers 날짜
        mover_type: 'gainers', 'losers', 'actives'
        language: 키워드 언어
        max_stocks: 최대 처리 종목 수

    Returns:
        list: [{'symbol', 'keywords', 'summary'}, ...]
    """
    service = KeywordGeneratorService(language=language)

    # asyncio 이벤트 루프 실행
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    results = loop.run_until_complete(
        service.generate_keywords_for_movers(
            mover_date=mover_date,
            mover_type=mover_type,
            max_stocks=max_stocks
        )
    )

    return results
