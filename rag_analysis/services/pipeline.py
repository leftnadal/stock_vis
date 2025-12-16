"""
AnalysisPipelineLite - 분석 파이프라인

데이터 준비 → LLM 분석 → 응답 파싱 → DB 저장 전체 흐름 관리
Semantic Cache 통합으로 유사 질문 재사용 지원
복잡도 기반 비용 최적화 통합 (Phase 3 Week 3)
"""

import time
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime, date

from asgiref.sync import sync_to_async
from django.db import close_old_connections

from ..models import AnalysisSession, AnalysisMessage
from .context import DateAwareContextFormatter
from .llm_service import LLMServiceLite, ResponseParser

logger = logging.getLogger(__name__)

# Semantic Cache 관련 설정
ENABLE_SEMANTIC_CACHE = True  # 캐시 활성화 플래그
ENABLE_COST_OPTIMIZATION = True  # 비용 최적화 활성화 플래그


class AnalysisPipelineLite:
    """
    분석 파이프라인 (Lite 버전)

    Phase 기반 이벤트 스트리밍:
    0. cache_check - 시맨틱 캐시 확인
    1. preparing - 데이터 준비 중
    2. context_ready - 컨텍스트 생성 완료
    3. analyzing - LLM 분석 시작
    4. streaming - LLM 응답 스트리밍
    5. complete - 분석 완료
    6. error - 에러 발생
    7. cache_hit - 캐시 히트 (즉시 응답)
    """

    def __init__(
        self,
        session: AnalysisSession,
        enable_cache: bool = True,
        enable_cost_optimization: bool = True
    ):
        """
        Args:
            session: AnalysisSession 인스턴스
            enable_cache: 시맨틱 캐시 사용 여부
            enable_cost_optimization: 비용 최적화 사용 여부
        """
        self.session = session
        self.llm = LLMServiceLite()
        self.enable_cache = enable_cache and ENABLE_SEMANTIC_CACHE
        self.enable_cost_optimization = enable_cost_optimization and ENABLE_COST_OPTIMIZATION

        # Neo4j는 lazy import (선택적 의존성)
        self._neo4j = None
        self._semantic_cache = None
        self._complexity_classifier = None
        self._cost_tracker = None

    @property
    def neo4j(self):
        """Neo4j 서비스 (지연 로딩)"""
        if self._neo4j is None:
            try:
                from .neo4j_service import Neo4jServiceLite
                self._neo4j = Neo4jServiceLite()
            except Exception as e:
                logger.warning(f"Neo4j service unavailable: {e}")
                self._neo4j = None
        return self._neo4j

    @property
    def semantic_cache(self):
        """시맨틱 캐시 서비스 (지연 로딩)"""
        if self._semantic_cache is None and self.enable_cache:
            try:
                from .semantic_cache import get_semantic_cache
                self._semantic_cache = get_semantic_cache()
            except Exception as e:
                logger.warning(f"Semantic cache unavailable: {e}")
                self._semantic_cache = None
        return self._semantic_cache

    @property
    def complexity_classifier(self):
        """복잡도 분류기 (지연 로딩)"""
        if self._complexity_classifier is None and self.enable_cost_optimization:
            try:
                from .complexity_classifier import get_complexity_classifier
                self._complexity_classifier = get_complexity_classifier()
            except Exception as e:
                logger.warning(f"Complexity classifier unavailable: {e}")
                self._complexity_classifier = None
        return self._complexity_classifier

    @property
    def cost_tracker(self):
        """비용 추적기 (지연 로딩)"""
        if self._cost_tracker is None:
            try:
                from .cost_tracker import get_cost_tracker
                self._cost_tracker = get_cost_tracker()
            except Exception as e:
                logger.warning(f"Cost tracker unavailable: {e}")
                self._cost_tracker = None
        return self._cost_tracker

    async def analyze(
        self,
        question: str,
        max_retries: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        분석 실행 (스트리밍)

        Args:
            question: 사용자 질문
            max_retries: LLM API 최대 재시도 횟수

        Yields:
            dict: Phase 이벤트
                - {'phase': 'cache_check', 'message': str}
                - {'phase': 'cache_hit', 'data': {...}}
                - {'phase': 'preparing', 'message': str}
                - {'phase': 'context_ready', 'message': str, 'context_length': int}
                - {'phase': 'analyzing', 'message': str}
                - {'phase': 'streaming', 'chunk': str}
                - {'phase': 'complete', 'data': {...}}
                - {'phase': 'error', 'error': {'code': str, 'message': str}}
        """
        start_time = time.time()
        full_response = ""
        input_tokens = 0
        output_tokens = 0
        entities: List[str] = []  # 캐시 저장용 엔티티 추적

        try:
            # Phase 0: 시맨틱 캐시 확인
            if self.enable_cache and self.semantic_cache:
                yield {
                    'phase': 'cache_check',
                    'message': '유사한 분석 결과를 확인하고 있습니다...'
                }

                # 바구니에서 엔티티(종목) 추출
                entities = await self._extract_basket_entities()

                # 캐시 검색
                cache_result = await self.semantic_cache.find_similar(
                    question=question,
                    entities=entities,
                    user_id=self.session.user_id if hasattr(self.session, 'user_id') else None
                )

                if cache_result:
                    # 캐시 히트!
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    # 사용자 메시지 저장
                    await self._save_message(
                        role=AnalysisMessage.Role.USER,
                        content=question,
                        suggestions=[],
                        input_tokens=0,
                        output_tokens=0
                    )

                    # 캐시된 응답 저장 (캐시 히트 표시)
                    await self._save_message(
                        role=AnalysisMessage.Role.ASSISTANT,
                        content=cache_result['response'],
                        suggestions=cache_result.get('suggestions', []),
                        input_tokens=0,
                        output_tokens=0
                    )

                    logger.info(
                        f"Cache HIT: similarity={cache_result['similarity_score']:.3f}, "
                        f"entity_match={cache_result.get('entity_match_score', 0):.3f}, "
                        f"latency={elapsed_ms}ms"
                    )

                    # 캐시 히트도 비용 추적 (비용 0)
                    if self.cost_tracker:
                        try:
                            await self.cost_tracker.log_usage(
                                user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                                session_id=self.session.id if hasattr(self.session, 'id') else None,
                                model='gemini-2.5-flash',
                                input_tokens=0,
                                output_tokens=0,
                                cached=True,
                                latency_ms=elapsed_ms
                            )
                        except Exception as e:
                            logger.warning(f"Failed to log cache hit: {e}")

                    yield {
                        'phase': 'cache_hit',
                        'data': {
                            'content': cache_result['response'],
                            'suggestions': cache_result.get('suggestions', []),
                            'basket_actions': [],
                            'usage': {
                                'input_tokens': 0,
                                'output_tokens': 0,
                                'cached': True,
                                'cost_usd': 0.0
                            },
                            'cache_info': {
                                'cache_id': cache_result.get('cache_id'),
                                'similarity_score': cache_result.get('similarity_score'),
                                'entity_match_score': cache_result.get('entity_match_score'),
                                'hit_count': cache_result.get('hit_count')
                            },
                            'latency_ms': elapsed_ms
                        }
                    }
                    return

            # Phase 1: 데이터 준비
            yield {
                'phase': 'preparing',
                'message': '데이터 바구니를 준비하고 있습니다...'
            }

            # Basket 조회 (sync → async 래핑)
            basket = await self._get_basket()

            # 엔티티 추출 (캐시 미사용 경로에서도 필요)
            if not entities:
                entities = await self._extract_basket_entities()

            # Phase 2: 컨텍스트 생성 (빈 바구니도 허용)
            if not basket or basket.items_count == 0:
                context = self._get_empty_basket_context()
            else:
                context = await self._format_context(basket)

            items_count = basket.items_count if basket else 0
            yield {
                'phase': 'context_ready',
                'message': f'분석 데이터 준비 완료 (아이템 {items_count}개)',
                'context_length': len(context)
            }

            # Phase 3: 복잡도 분류 및 LLM 분석 시작
            complexity = 'moderate'  # 기본값
            complexity_score = 0.5

            if self.enable_cost_optimization and self.complexity_classifier:
                try:
                    config = self.complexity_classifier.classify_and_configure(
                        question=question,
                        entities_count=len(entities),
                        context_tokens=len(context.split())
                    )
                    complexity = config['complexity'].value
                    complexity_score = config['complexity_score']

                    logger.info(
                        f"Complexity classified: {complexity} "
                        f"(score={complexity_score:.2f})"
                    )
                except Exception as e:
                    logger.warning(f"Complexity classification failed: {e}")

            yield {
                'phase': 'analyzing',
                'message': 'AI 분석을 시작합니다...',
                'complexity': complexity,
                'complexity_score': round(complexity_score, 2)
            }

            # 사용자 메시지 저장
            await self._save_message(
                role=AnalysisMessage.Role.USER,
                content=question,
                suggestions=[],
                input_tokens=0,
                output_tokens=0
            )

            # Phase 4: LLM 스트리밍 (복잡도 기반 설정 적용)
            async for event in self.llm.generate_stream(
                context=context,
                question=question,
                max_retries=max_retries,
                complexity=complexity
            ):
                if event['type'] == 'delta':
                    # 텍스트 청크 전달
                    chunk = event['content']
                    full_response += chunk

                    yield {
                        'phase': 'streaming',
                        'chunk': chunk
                    }

                elif event['type'] == 'final':
                    # 토큰 사용량 저장
                    input_tokens = event['input_tokens']
                    output_tokens = event['output_tokens']

                elif event['type'] == 'error':
                    # LLM 에러
                    yield {
                        'phase': 'error',
                        'error': {
                            'code': 'LLM_ERROR',
                            'message': event['message']
                        }
                    }

                    # 에러 메시지도 저장
                    await self._save_message(
                        role=AnalysisMessage.Role.SYSTEM,
                        content=f"[에러] {event['message']}",
                        suggestions=[],
                        input_tokens=0,
                        output_tokens=0
                    )
                    return

            # Phase 5: 응답 파싱
            cleaned_content, suggestions = ResponseParser.parse_suggestions(full_response)
            cleaned_content, basket_actions = ResponseParser.parse_basket_actions(cleaned_content)

            # Assistant 메시지 저장
            await self._save_message(
                role=AnalysisMessage.Role.ASSISTANT,
                content=cleaned_content,
                suggestions=suggestions,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            # 탐험 경로 업데이트 (suggestions 기반)
            if suggestions:
                await self._update_exploration_path(suggestions)

            # 캐시에 저장 (성공적인 응답만)
            cache_id = None
            if self.enable_cache and self.semantic_cache and cleaned_content:
                try:
                    cache_id = await self.semantic_cache.store(
                        question=question,
                        entities=entities,
                        response=cleaned_content,
                        suggestions=suggestions,
                        usage={
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens
                        },
                        user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                        session_id=self.session.id if hasattr(self.session, 'id') else None
                    )
                    if cache_id:
                        logger.info(f"Response cached: {cache_id}")
                except Exception as e:
                    logger.warning(f"Failed to store cache: {e}")

            # Phase 6: 완료
            elapsed_ms = int((time.time() - start_time) * 1000)

            # 비용 추적 (Phase 3 Week 3)
            cost_usd = 0.0
            if self.cost_tracker:
                try:
                    await self.cost_tracker.log_usage(
                        user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                        session_id=self.session.id if hasattr(self.session, 'id') else None,
                        model='gemini-2.5-flash',
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached=False,
                        latency_ms=elapsed_ms,
                        complexity=complexity
                    )
                    cost_usd = self.cost_tracker.calculate_cost(
                        'gemini-2.5-flash', input_tokens, output_tokens
                    )
                    logger.info(
                        f"Usage logged: {input_tokens}+{output_tokens} tokens, "
                        f"${cost_usd:.6f}, complexity={complexity}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to log usage: {e}")

            yield {
                'phase': 'complete',
                'data': {
                    'content': cleaned_content,
                    'suggestions': suggestions,
                    'basket_actions': basket_actions,
                    'usage': {
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'cached': False,
                        'cost_usd': cost_usd
                    },
                    'complexity': complexity,
                    'complexity_score': round(complexity_score, 2),
                    'cache_id': cache_id,
                    'latency_ms': elapsed_ms
                }
            }

        except Exception as e:
            # 예상치 못한 에러
            logger.exception(f"Pipeline error: {e}")

            yield {
                'phase': 'error',
                'error': {
                    'code': 'PIPELINE_ERROR',
                    'message': f'분석 중 오류가 발생했습니다: {str(e)}'
                }
            }

        finally:
            # DB 연결 정리
            await sync_to_async(close_old_connections)()

    # ========== Private Methods ==========

    def _get_empty_basket_context(self) -> str:
        """
        빈 바구니 컨텍스트 생성

        Returns:
            str: 빈 바구니 상황을 설명하는 컨텍스트
        """
        today = date.today().strftime('%Y년 %m월 %d일')
        return f"""=== 분석 데이터 바구니 ===
분석 기준일: {today}
총 아이템 수: 0개
남은 용량: 100 units

현재 바구니에 분석할 데이터가 없습니다.
사용자 질문에 대해 일반적인 투자 관점에서 답변하고,
관련 종목이나 데이터를 바구니에 추가하도록 제안해주세요.
"""

    @sync_to_async
    def _get_basket(self):
        """세션의 바구니 조회 (sync → async)"""
        close_old_connections()

        if not self.session.basket:
            return None

        # prefetch_related로 아이템 한 번에 로드
        from ..models import DataBasket
        return DataBasket.objects.prefetch_related('items').get(pk=self.session.basket.pk)

    async def _extract_basket_entities(self) -> List[str]:
        """
        바구니에서 종목 엔티티 추출

        Returns:
            List[str]: 종목 심볼 리스트
        """
        entities = []

        try:
            basket = await self._get_basket()
            if basket:
                items = await sync_to_async(list)(basket.items.all())
                for item in items:
                    # stock 타입 아이템에서 심볼 추출
                    if item.item_type == 'stock' and item.reference_id:
                        entities.append(item.reference_id.upper())
                    # overview 타입 (기업 정보)
                    elif item.item_type == 'overview' and item.reference_id:
                        entities.append(item.reference_id.upper())
                    # 데이터 스냅샷에서 심볼 추출 시도
                    elif item.data_snapshot and isinstance(item.data_snapshot, dict):
                        if 'symbol' in item.data_snapshot:
                            entities.append(item.data_snapshot['symbol'].upper())

        except Exception as e:
            logger.warning(f"Failed to extract basket entities: {e}")

        return list(set(entities))  # 중복 제거

    @sync_to_async
    def _format_context(self, basket):
        """컨텍스트 포맷팅 (sync → async)"""
        close_old_connections()
        formatter = DateAwareContextFormatter(basket)
        return formatter.format()

    @sync_to_async
    def _save_message(
        self,
        role: str,
        content: str,
        suggestions: list,
        input_tokens: int,
        output_tokens: int
    ):
        """메시지 저장 (sync → async)"""
        close_old_connections()

        AnalysisMessage.objects.create(
            session=self.session,
            role=role,
            content=content,
            suggestions=suggestions,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

    @sync_to_async
    def _update_exploration_path(self, suggestions: list):
        """탐험 경로 업데이트 (sync → async)"""
        close_old_connections()

        for suggestion in suggestions:
            self.session.add_exploration(
                entity_type='stock',
                entity_id=suggestion['symbol'],
                reason=suggestion['reason']
            )

    async def get_enhanced_context(
        self,
        symbol: str,
        include_graph: bool = True
    ) -> Dict[str, Any]:
        """
        Neo4j 그래프 데이터로 컨텍스트 확장

        Args:
            symbol: 종목 심볼
            include_graph: Neo4j 데이터 포함 여부

        Returns:
            dict: {
                'relationships': [...],
                'competitors': [...],
                'suppliers': [...],
                'customers': [...]
            }
        """
        if not include_graph or not self.neo4j:
            return {}

        try:
            return await sync_to_async(
                self.neo4j.get_stock_relationships
            )(symbol)

        except Exception as e:
            logger.warning(f"Failed to get graph context for {symbol}: {e}")
            return {}


class PipelineEventType:
    """파이프라인 이벤트 타입 상수"""
    CACHE_CHECK = 'cache_check'
    CACHE_HIT = 'cache_hit'
    PREPARING = 'preparing'
    CONTEXT_READY = 'context_ready'
    ANALYZING = 'analyzing'
    STREAMING = 'streaming'
    COMPLETE = 'complete'
    ERROR = 'error'


class PipelineErrorCode:
    """파이프라인 에러 코드 상수"""
    BASKET_NOT_FOUND = 'BASKET_NOT_FOUND'
    LLM_ERROR = 'LLM_ERROR'
    GRAPH_ERROR = 'GRAPH_ERROR'
    PIPELINE_ERROR = 'PIPELINE_ERROR'
    CACHE_ERROR = 'CACHE_ERROR'


class AnalysisPipelineFinal:
    """
    최종 분석 파이프라인 (Phase 3 통합 버전)

    모든 최적화 컴포넌트 통합:
    - Stage 0: 시맨틱 캐시 확인
    - Stage 1: 복잡도 분류
    - Stage 2: 토큰 예산 할당
    - Stage 3: 적응형 LLM 분석
    - Stage 4: 캐시 저장 및 비용 추적
    """

    def __init__(
        self,
        session: AnalysisSession,
        enable_cache: bool = True,
        enable_cost_optimization: bool = True,
        provider: str = 'gemini'
    ):
        """
        Args:
            session: AnalysisSession 인스턴스
            enable_cache: 시맨틱 캐시 사용 여부
            enable_cost_optimization: 비용 최적화 사용 여부
            provider: LLM 프로바이더 ('gemini' 또는 'claude')
        """
        self.session = session
        self.enable_cache = enable_cache and ENABLE_SEMANTIC_CACHE
        self.enable_cost_optimization = enable_cost_optimization and ENABLE_COST_OPTIMIZATION
        self.provider = provider

        # 지연 로딩 컴포넌트
        self._semantic_cache = None
        self._complexity_classifier = None
        self._token_budget_manager = None
        self._adaptive_llm = None
        self._cost_tracker = None

        logger.info(
            f"AnalysisPipelineFinal initialized: "
            f"cache={self.enable_cache}, cost_opt={self.enable_cost_optimization}, "
            f"provider={self.provider}"
        )

    # ========== Lazy Loaded Components ==========

    @property
    def semantic_cache(self):
        """시맨틱 캐시 (지연 로딩)"""
        if self._semantic_cache is None and self.enable_cache:
            try:
                from .semantic_cache import get_semantic_cache
                self._semantic_cache = get_semantic_cache()
            except Exception as e:
                logger.warning(f"Semantic cache unavailable: {e}")
        return self._semantic_cache

    @property
    def complexity_classifier(self):
        """복잡도 분류기 (지연 로딩)"""
        if self._complexity_classifier is None:
            try:
                from .complexity_classifier import get_complexity_classifier
                self._complexity_classifier = get_complexity_classifier(self.provider)
            except Exception as e:
                logger.warning(f"Complexity classifier unavailable: {e}")
        return self._complexity_classifier

    @property
    def token_budget_manager(self):
        """토큰 예산 관리자 (지연 로딩)"""
        # 복잡도에 따라 동적으로 생성됨
        return self._token_budget_manager

    @property
    def adaptive_llm(self):
        """적응형 LLM 서비스 (지연 로딩)"""
        if self._adaptive_llm is None:
            try:
                from .adaptive_llm_service import get_adaptive_llm_service
                self._adaptive_llm = get_adaptive_llm_service(
                    provider=self.provider,
                    enable_cost_tracking=self.enable_cost_optimization
                )
            except Exception as e:
                logger.warning(f"Adaptive LLM unavailable: {e}")
        return self._adaptive_llm

    @property
    def cost_tracker(self):
        """비용 추적기 (지연 로딩)"""
        if self._cost_tracker is None and self.enable_cost_optimization:
            try:
                from .cost_tracker import get_cost_tracker
                self._cost_tracker = get_cost_tracker()
            except Exception as e:
                logger.warning(f"Cost tracker unavailable: {e}")
        return self._cost_tracker

    async def analyze(
        self,
        question: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        최종 분석 파이프라인 실행

        Stages:
            0. 시맨틱 캐시 확인
            1. 복잡도 분류
            2. 토큰 예산 할당
            3. 적응형 LLM 분석
            4. 캐시 저장 및 비용 추적

        Args:
            question: 사용자 질문

        Yields:
            dict: Phase 이벤트
        """
        start_time = time.time()
        full_response = ""
        input_tokens = 0
        output_tokens = 0
        entities: List[str] = []
        complexity = 'moderate'
        complexity_score = 0.5
        model_used = 'gemini-2.5-flash'

        try:
            # ========== Stage 0: 시맨틱 캐시 확인 ==========
            if self.enable_cache and self.semantic_cache:
                yield {
                    'phase': 'cache_check',
                    'message': '유사한 분석 결과를 확인하고 있습니다...'
                }

                entities = await self._extract_basket_entities()

                cache_result = await self.semantic_cache.find_similar(
                    question=question,
                    entities=entities,
                    user_id=self.session.user_id if hasattr(self.session, 'user_id') else None
                )

                if cache_result:
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    await self._save_message(
                        role=AnalysisMessage.Role.USER,
                        content=question,
                        suggestions=[],
                        input_tokens=0,
                        output_tokens=0
                    )

                    await self._save_message(
                        role=AnalysisMessage.Role.ASSISTANT,
                        content=cache_result['response'],
                        suggestions=cache_result.get('suggestions', []),
                        input_tokens=0,
                        output_tokens=0
                    )

                    # 캐시 히트 비용 추적
                    if self.cost_tracker:
                        try:
                            await self.cost_tracker.log_usage(
                                user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                                session_id=self.session.id if hasattr(self.session, 'id') else None,
                                model=model_used,
                                input_tokens=0,
                                output_tokens=0,
                                cached=True,
                                latency_ms=elapsed_ms
                            )
                        except Exception as e:
                            logger.warning(f"Failed to log cache hit: {e}")

                    logger.info(
                        f"[Stage 0] Cache HIT: similarity={cache_result['similarity_score']:.3f}, "
                        f"latency={elapsed_ms}ms"
                    )

                    yield {
                        'phase': 'cache_hit',
                        'data': {
                            'content': cache_result['response'],
                            'suggestions': cache_result.get('suggestions', []),
                            'basket_actions': [],
                            'usage': {
                                'input_tokens': 0,
                                'output_tokens': 0,
                                'cached': True,
                                'cost_usd': 0.0
                            },
                            'cache_info': {
                                'cache_id': cache_result.get('cache_id'),
                                'similarity_score': cache_result.get('similarity_score'),
                                'entity_match_score': cache_result.get('entity_match_score'),
                                'hit_count': cache_result.get('hit_count')
                            },
                            'latency_ms': elapsed_ms
                        }
                    }
                    return

            # ========== Stage 1: 복잡도 분류 ==========
            yield {
                'phase': 'preparing',
                'message': '데이터 준비 및 복잡도 분석 중...'
            }

            basket = await self._get_basket()
            if not entities:
                entities = await self._extract_basket_entities()

            # 컨텍스트 생성 (전체)
            if not basket or basket.items_count == 0:
                full_context = self._get_empty_basket_context()
            else:
                full_context = await self._format_context(basket)

            context_tokens = len(full_context.split())

            # 복잡도 분류
            if self.complexity_classifier:
                try:
                    config = self.complexity_classifier.classify_and_configure(
                        question=question,
                        entities_count=len(entities),
                        context_tokens=context_tokens
                    )
                    complexity = config['complexity'].value
                    complexity_score = config['complexity_score']
                    model_used = config['model']

                    logger.info(
                        f"[Stage 1] Complexity: {complexity} "
                        f"(score={complexity_score:.2f}, model={model_used})"
                    )
                except Exception as e:
                    logger.warning(f"Complexity classification failed: {e}")

            # ========== Stage 2: 토큰 예산 할당 ==========
            optimized_context = full_context
            allocation_info = {}

            if self.enable_cost_optimization:
                try:
                    from .token_budget_manager import (
                        TokenBudgetManager,
                        ContentBlock,
                        ContentPriority
                    )

                    self._token_budget_manager = TokenBudgetManager(complexity)
                    budget = self._token_budget_manager.budget

                    # 컨텍스트가 예산을 초과하면 압축
                    if context_tokens > budget['context']:
                        content_blocks = self._create_content_blocks(basket, full_context)
                        selected_blocks, allocation_info = self._token_budget_manager.allocate(
                            content_blocks
                        )
                        optimized_context = self._token_budget_manager.build_context(selected_blocks)

                        logger.info(
                            f"[Stage 2] Token budget: {allocation_info.get('used', 0)}/"
                            f"{allocation_info.get('budget', 0)} tokens, "
                            f"{allocation_info.get('selected_count', 0)} blocks selected"
                        )
                    else:
                        logger.info(f"[Stage 2] Context within budget: {context_tokens} tokens")

                except Exception as e:
                    logger.warning(f"Token budget optimization failed: {e}")

            items_count = basket.items_count if basket else 0
            yield {
                'phase': 'context_ready',
                'message': f'분석 데이터 준비 완료 (아이템 {items_count}개)',
                'context_length': len(optimized_context),
                'allocation': allocation_info
            }

            # ========== Stage 3: 적응형 LLM 분석 ==========
            yield {
                'phase': 'analyzing',
                'message': 'AI 분석을 시작합니다...',
                'complexity': complexity,
                'complexity_score': round(complexity_score, 2),
                'model': model_used
            }

            await self._save_message(
                role=AnalysisMessage.Role.USER,
                content=question,
                suggestions=[],
                input_tokens=0,
                output_tokens=0
            )

            # 적응형 LLM 또는 기본 LLM 사용
            if self.adaptive_llm:
                async for event in self.adaptive_llm.generate_stream(
                    context=optimized_context,
                    question=question,
                    entities_count=len(entities),
                    user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                    session_id=self.session.id if hasattr(self.session, 'id') else None
                ):
                    if event['type'] == 'config':
                        # 모델 설정 업데이트
                        model_used = event['data'].get('model', model_used)
                        logger.info(f"[Stage 3] LLM config: {event['data']}")

                    elif event['type'] == 'delta':
                        chunk = event['content']
                        full_response += chunk
                        yield {
                            'phase': 'streaming',
                            'chunk': chunk
                        }

                    elif event['type'] == 'final':
                        input_tokens = event.get('input_tokens', 0)
                        output_tokens = event.get('output_tokens', 0)

                    elif event['type'] == 'error':
                        yield {
                            'phase': 'error',
                            'error': {
                                'code': 'LLM_ERROR',
                                'message': event['message']
                            }
                        }
                        return
            else:
                # 폴백: 기본 LLM 서비스 사용
                llm = LLMServiceLite()
                async for event in llm.generate_stream(
                    context=optimized_context,
                    question=question,
                    complexity=complexity
                ):
                    if event['type'] == 'delta':
                        chunk = event['content']
                        full_response += chunk
                        yield {
                            'phase': 'streaming',
                            'chunk': chunk
                        }
                    elif event['type'] == 'final':
                        input_tokens = event['input_tokens']
                        output_tokens = event['output_tokens']
                    elif event['type'] == 'error':
                        yield {
                            'phase': 'error',
                            'error': {
                                'code': 'LLM_ERROR',
                                'message': event['message']
                            }
                        }
                        return

            # ========== Stage 4: 캐시 저장 및 비용 추적 ==========
            cleaned_content, suggestions = ResponseParser.parse_suggestions(full_response)
            cleaned_content, basket_actions = ResponseParser.parse_basket_actions(cleaned_content)

            await self._save_message(
                role=AnalysisMessage.Role.ASSISTANT,
                content=cleaned_content,
                suggestions=suggestions,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            if suggestions:
                await self._update_exploration_path(suggestions)

            # 캐시 저장
            cache_id = None
            if self.enable_cache and self.semantic_cache and cleaned_content:
                try:
                    cache_id = await self.semantic_cache.store(
                        question=question,
                        entities=entities,
                        response=cleaned_content,
                        suggestions=suggestions,
                        usage={
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens
                        },
                        user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                        session_id=self.session.id if hasattr(self.session, 'id') else None
                    )
                    logger.info(f"[Stage 4] Response cached: {cache_id}")
                except Exception as e:
                    logger.warning(f"Failed to store cache: {e}")

            # 비용 추적
            elapsed_ms = int((time.time() - start_time) * 1000)
            cost_usd = 0.0

            if self.cost_tracker:
                try:
                    await self.cost_tracker.log_usage(
                        user_id=self.session.user_id if hasattr(self.session, 'user_id') else None,
                        session_id=self.session.id if hasattr(self.session, 'id') else None,
                        model=model_used,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached=False,
                        latency_ms=elapsed_ms,
                        complexity=complexity
                    )
                    cost_usd = self.cost_tracker.calculate_cost(
                        model_used, input_tokens, output_tokens
                    )
                    logger.info(
                        f"[Stage 4] Usage: {input_tokens}+{output_tokens} tokens, "
                        f"${cost_usd:.6f}, latency={elapsed_ms}ms"
                    )
                except Exception as e:
                    logger.warning(f"Failed to log usage: {e}")

            yield {
                'phase': 'complete',
                'data': {
                    'content': cleaned_content,
                    'suggestions': suggestions,
                    'basket_actions': basket_actions,
                    'usage': {
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'cached': False,
                        'cost_usd': cost_usd
                    },
                    'complexity': complexity,
                    'complexity_score': round(complexity_score, 2),
                    'model': model_used,
                    'cache_id': cache_id,
                    'latency_ms': elapsed_ms
                }
            }

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            yield {
                'phase': 'error',
                'error': {
                    'code': 'PIPELINE_ERROR',
                    'message': f'분석 중 오류가 발생했습니다: {str(e)}'
                }
            }

        finally:
            await sync_to_async(close_old_connections)()

    # ========== Private Methods ==========

    def _get_empty_basket_context(self) -> str:
        """빈 바구니 컨텍스트 생성"""
        today = date.today().strftime('%Y년 %m월 %d일')
        return f"""=== 분석 데이터 바구니 ===
분석 기준일: {today}
총 아이템 수: 0개
남은 용량: 100 units

현재 바구니에 분석할 데이터가 없습니다.
사용자 질문에 대해 일반적인 투자 관점에서 답변하고,
관련 종목이나 데이터를 바구니에 추가하도록 제안해주세요.
"""

    @sync_to_async
    def _get_basket(self):
        """세션의 바구니 조회 (sync → async)"""
        close_old_connections()

        if not self.session.basket:
            return None

        from ..models import DataBasket
        return DataBasket.objects.prefetch_related('items').get(pk=self.session.basket.pk)

    async def _extract_basket_entities(self) -> List[str]:
        """바구니에서 종목 엔티티 추출"""
        entities = []

        try:
            basket = await self._get_basket()
            if basket:
                items = await sync_to_async(list)(basket.items.all())
                for item in items:
                    if item.item_type == 'stock' and item.reference_id:
                        entities.append(item.reference_id.upper())
                    elif item.item_type == 'overview' and item.reference_id:
                        entities.append(item.reference_id.upper())
                    elif item.data_snapshot and isinstance(item.data_snapshot, dict):
                        if 'symbol' in item.data_snapshot:
                            entities.append(item.data_snapshot['symbol'].upper())

        except Exception as e:
            logger.warning(f"Failed to extract basket entities: {e}")

        return list(set(entities))

    @sync_to_async
    def _format_context(self, basket):
        """컨텍스트 포맷팅 (sync → async)"""
        close_old_connections()
        formatter = DateAwareContextFormatter(basket)
        return formatter.format()

    def _create_content_blocks(self, basket, full_context: str) -> List:
        """바구니 아이템을 ContentBlock으로 변환"""
        from .token_budget_manager import ContentBlock, ContentPriority

        blocks = []

        if not basket:
            return blocks

        try:
            # 기본 컨텍스트를 하나의 블록으로
            blocks.append(ContentBlock(
                content=full_context,
                priority=ContentPriority.MEDIUM,
                token_count=len(full_context.split()),
                source='basket_context'
            ))

        except Exception as e:
            logger.warning(f"Failed to create content blocks: {e}")

        return blocks

    @sync_to_async
    def _save_message(
        self,
        role: str,
        content: str,
        suggestions: list,
        input_tokens: int,
        output_tokens: int
    ):
        """메시지 저장 (sync → async)"""
        close_old_connections()

        AnalysisMessage.objects.create(
            session=self.session,
            role=role,
            content=content,
            suggestions=suggestions,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

    @sync_to_async
    def _update_exploration_path(self, suggestions: list):
        """탐험 경로 업데이트 (sync → async)"""
        close_old_connections()

        for suggestion in suggestions:
            self.session.add_exploration(
                entity_type='stock',
                entity_id=suggestion['symbol'],
                reason=suggestion['reason']
            )
