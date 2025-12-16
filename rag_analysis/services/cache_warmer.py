"""
Cache Warmer - 캐시 사전 워밍

자주 묻는 질문 패턴을 미리 캐시에 저장하여 히트율을 높입니다.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from asgiref.sync import sync_to_async, async_to_sync

from django.conf import settings

from .semantic_cache import SemanticCacheService, get_semantic_cache
from .llm_service import LLMServiceLite
from .context import DateAwareContextFormatter

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    캐시 워머

    Features:
        - 인기 종목 × 일반 질문 패턴 조합
        - 주기적 캐시 갱신
        - 우선순위 기반 워밍
    """

    # 자주 묻는 질문 템플릿
    QUESTION_TEMPLATES = [
        "{symbol}의 현재 주가와 최근 동향은?",
        "{symbol}의 재무 상태는 어떤가요?",
        "{symbol}에 투자해도 괜찮을까요?",
        "{symbol}의 경쟁사 대비 장단점은?",
        "{symbol}의 매출과 영업이익 추이는?",
        "{symbol}의 PER, PBR 등 밸류에이션은?",
    ]

    # 인기 종목 (워밍 우선순위 순)
    POPULAR_SYMBOLS = [
        # 미국 빅테크
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        # 반도체
        "TSM", "AMD", "INTC", "AVGO",
        # 금융
        "JPM", "BAC", "GS",
        # 한국 주요 종목
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
    ]

    def __init__(self):
        """캐시 워머 초기화"""
        self.cache = get_semantic_cache()
        self.llm = LLMServiceLite()
        self._warmed_count = 0

    async def warm_cache(
        self,
        symbols: Optional[List[str]] = None,
        templates: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        캐시 워밍 실행

        Args:
            symbols: 워밍할 종목 리스트 (None이면 POPULAR_SYMBOLS 사용)
            templates: 질문 템플릿 (None이면 QUESTION_TEMPLATES 사용)
            limit: 최대 워밍 수

        Returns:
            {
                'warmed_count': int,
                'failed_count': int,
                'skipped_count': int,
                'duration_seconds': float
            }
        """
        start_time = datetime.now()
        symbols = symbols or self.POPULAR_SYMBOLS
        templates = templates or self.QUESTION_TEMPLATES

        warmed = 0
        failed = 0
        skipped = 0

        # 종목 × 질문 조합 생성
        combinations = []
        for symbol in symbols:
            for template in templates:
                if len(combinations) >= limit:
                    break
                question = template.format(symbol=symbol)
                combinations.append((symbol, question))
            if len(combinations) >= limit:
                break

        logger.info(f"Starting cache warming: {len(combinations)} questions")

        for symbol, question in combinations:
            try:
                # 이미 캐시에 있는지 확인
                existing = await self.cache.find_similar(
                    question=question,
                    entities=[symbol]
                )

                if existing:
                    skipped += 1
                    continue

                # LLM 응답 생성
                result = await self._generate_response(symbol, question)

                if result:
                    # 캐시에 저장
                    cache_id = await self.cache.store(
                        question=question,
                        entities=[symbol],
                        response=result['content'],
                        suggestions=result.get('suggestions', []),
                        usage=result.get('usage', {})
                    )

                    if cache_id:
                        warmed += 1
                        logger.debug(f"Warmed: {question[:50]}...")
                    else:
                        failed += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Cache warming failed for {question[:50]}: {e}")
                failed += 1

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Cache warming complete: "
            f"warmed={warmed}, failed={failed}, skipped={skipped}, "
            f"duration={duration:.1f}s"
        )

        return {
            'warmed_count': warmed,
            'failed_count': failed,
            'skipped_count': skipped,
            'duration_seconds': duration
        }

    async def _generate_response(
        self,
        symbol: str,
        question: str
    ) -> Optional[Dict[str, Any]]:
        """
        LLM 응답 생성

        Args:
            symbol: 종목 심볼
            question: 질문

        Returns:
            {
                'content': str,
                'suggestions': list,
                'usage': dict
            }
        """
        try:
            # 심플한 컨텍스트 생성 (바구니 없이)
            context = self._get_minimal_context(symbol)

            # LLM 스트리밍으로 응답 수집
            full_response = ""
            usage = {'input_tokens': 0, 'output_tokens': 0}

            async for event in self.llm.generate_stream(
                context=context,
                question=question,
                max_retries=2
            ):
                if event['type'] == 'delta':
                    full_response += event['content']
                elif event['type'] == 'final':
                    usage = {
                        'input_tokens': event.get('input_tokens', 0),
                        'output_tokens': event.get('output_tokens', 0)
                    }
                elif event['type'] == 'error':
                    logger.warning(f"LLM error during warming: {event['message']}")
                    return None

            # 응답 파싱
            from .llm_service import ResponseParser
            content, suggestions = ResponseParser.parse_suggestions(full_response)

            return {
                'content': content,
                'suggestions': suggestions,
                'usage': usage
            }

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return None

    def _get_minimal_context(self, symbol: str) -> str:
        """
        최소 컨텍스트 생성 (워밍용)

        Args:
            symbol: 종목 심볼

        Returns:
            컨텍스트 문자열
        """
        today = datetime.now().strftime('%Y년 %m월 %d일')

        return f"""=== 분석 데이터 바구니 ===
분석 기준일: {today}
총 아이템 수: 1개

## 분석 대상 종목
- {symbol}

참고: 상세 데이터 없이 일반적인 분석 요청입니다.
해당 종목에 대한 일반적인 투자 관점을 제공하고,
필요한 추가 데이터를 바구니에 담도록 안내해주세요.
"""

    async def warm_for_user(
        self,
        user_id: int,
        recent_symbols: List[str],
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        사용자 맞춤 캐시 워밍

        사용자가 최근 조회한 종목 기반으로 캐시를 미리 생성합니다.

        Args:
            user_id: 사용자 ID
            recent_symbols: 최근 조회 종목 리스트
            limit: 최대 워밍 수

        Returns:
            워밍 결과
        """
        # 사용자 관심 종목에 대해 기본 질문만 워밍
        basic_templates = [
            "{symbol}의 현재 상황은?",
            "{symbol} 투자 전망은?",
        ]

        return await self.warm_cache(
            symbols=recent_symbols[:limit // 2],
            templates=basic_templates,
            limit=limit
        )


def run_cache_warming_sync(
    symbols: Optional[List[str]] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    동기 방식 캐시 워밍 (Celery 태스크용)

    Args:
        symbols: 워밍할 종목 리스트
        limit: 최대 워밍 수

    Returns:
        워밍 결과
    """
    warmer = CacheWarmer()
    return async_to_sync(warmer.warm_cache)(symbols=symbols, limit=limit)


# 인기 질문 패턴 (히트율 분석용)
COMMON_QUESTION_PATTERNS = [
    # 기본 정보
    r"(.+)의?\s*(현재|최근)?\s*(주가|가격|시세)",
    r"(.+)\s*투자\s*(괜찮|좋|추천)",
    r"(.+)의?\s*전망",
    r"(.+)의?\s*재무\s*(상태|현황|분석)",

    # 밸류에이션
    r"(.+)의?\s*(PER|PBR|PSR|밸류에이션)",
    r"(.+)\s*(저평가|고평가)",

    # 비교 분석
    r"(.+)와?\s*(.+)\s*비교",
    r"(.+)의?\s*경쟁사",

    # 재무
    r"(.+)의?\s*(매출|영업이익|순이익|실적)",
    r"(.+)의?\s*배당",
]
