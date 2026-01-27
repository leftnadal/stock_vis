"""
AnalysisPipelineV2 - RAG 기반 분석 파이프라인

5-Stage Pipeline:
1. Entity Extraction (Haiku)
2. Hybrid Search (Vector + BM25 + Graph)
3. Reranking + GraphRAG Scoring
4. Context Compression (Haiku)
5. LLM Analysis (Sonnet 4.5)

SSE Event Flow:
extracting → entities_extracted → searching → search_complete →
ranking → ranking_complete → compressing → compression_complete →
analyzing → streaming → complete
"""

import time
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List

from asgiref.sync import sync_to_async
from django.db import close_old_connections

from ..models import AnalysisSession, AnalysisMessage
from .entity_extractor import EntityExtractor, EntityNormalizer
from .hybrid_search import HybridSearchService, SearchWeights, MetadataFilterBuilder
from .reranker import CrossEncoderReranker
from .context_compressor import QuestionAwareCompressor
from .llm_service import LLMServiceLite, ResponseParser

logger = logging.getLogger(__name__)


class AnalysisPipelineV2:
    """
    RAG 기반 분석 파이프라인 V2

    Features:
        - 엔티티 추출 기반 검색
        - Hybrid Search (Vector + BM25 + Graph)
        - Cross-Encoder 재순위화
        - Context Compression (Haiku)
        - LLM 분석 (Sonnet 4.5)

    SSE Phase Events:
        - extracting: 엔티티 추출 중
        - entities_extracted: 엔티티 추출 완료
        - searching: 문서 검색 중
        - search_complete: 검색 완료
        - ranking: 문서 재순위화 중
        - ranking_complete: 재순위화 완료
        - compressing: 컨텍스트 압축 중
        - compression_complete: 압축 완료
        - analyzing: LLM 분석 시작
        - streaming: LLM 응답 스트리밍
        - complete: 분석 완료
        - error: 에러 발생
    """

    def __init__(
        self,
        session: AnalysisSession,
        documents: Optional[List[dict]] = None,
        search_weights: Optional[SearchWeights] = None,
        rerank_top_k: int = 10,
        final_top_k: int = 5
    ):
        """
        Args:
            session: AnalysisSession 인스턴스
            documents: 검색할 문서 리스트 (None이면 Neo4j/DB에서 조회)
            search_weights: Hybrid Search 가중치
            rerank_top_k: Reranking 전 선별할 문서 수
            final_top_k: 최종 압축 후 사용할 문서 수
        """
        self.session = session
        self.documents = documents or []

        # Services 초기화
        self.entity_extractor = EntityExtractor()
        self.entity_normalizer = EntityNormalizer()
        self.hybrid_search = HybridSearchService(weights=search_weights)
        self.reranker = CrossEncoderReranker()
        self.compressor = QuestionAwareCompressor()
        self.llm = LLMServiceLite()

        # 설정
        self.rerank_top_k = rerank_top_k
        self.final_top_k = final_top_k

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
                - {'phase': 'extracting', 'message': str}
                - {'phase': 'entities_extracted', 'entities': {...}, 'message': str}
                - {'phase': 'searching', 'message': str}
                - {'phase': 'search_complete', 'results_count': int, 'message': str}
                - {'phase': 'ranking', 'message': str}
                - {'phase': 'ranking_complete', 'top_k': int, 'message': str}
                - {'phase': 'compressing', 'message': str}
                - {'phase': 'compression_complete', 'stats': {...}, 'message': str}
                - {'phase': 'analyzing', 'message': str}
                - {'phase': 'streaming', 'chunk': str}
                - {'phase': 'complete', 'data': {...}}
                - {'phase': 'error', 'error': {...}}
        """
        start_time = time.time()
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        try:
            # ========== Stage 1: Entity Extraction ==========
            yield {
                'phase': 'extracting',
                'message': '질문에서 엔티티를 추출하고 있습니다...'
            }

            entities = await self.entity_extractor.extract(question)
            normalized_symbols = self.entity_normalizer.normalize_stocks(entities['stocks'])

            yield {
                'phase': 'entities_extracted',
                'entities': {
                    'stocks': normalized_symbols,
                    'metrics': entities['metrics'],
                    'concepts': entities['concepts'],
                    'timeframe': entities['timeframe']
                },
                'message': f"엔티티 추출 완료: 종목 {len(normalized_symbols)}개"
            }

            # ========== Stage 2: Hybrid Search ==========
            yield {
                'phase': 'searching',
                'message': '관련 문서를 검색하고 있습니다...'
            }

            # 문서가 제공되지 않았으면 DB/Neo4j에서 조회
            if not self.documents:
                self.documents = await self._fetch_documents(normalized_symbols)

            # Metadata 필터링 (추출된 심볼 기준)
            metadata_filter = None
            if normalized_symbols:
                metadata_filter = MetadataFilterBuilder().add_symbols(normalized_symbols)

            # Hybrid Search 수행
            search_results = self.hybrid_search.search(
                query=question,
                documents=self.documents,
                top_k=self.rerank_top_k,
                symbol=normalized_symbols[0] if normalized_symbols else None,
                metadata_filter=metadata_filter,
                use_graph=True
            )

            # 결과 변환 (doc_id → document)
            search_docs = self._resolve_search_results(search_results)

            yield {
                'phase': 'search_complete',
                'results_count': len(search_docs),
                'message': f"검색 완료: {len(search_docs)}개 문서 발견"
            }

            # 검색 결과가 없으면 빈 바구니 모드로 전환
            if not search_docs:
                logger.info("No search results, falling back to empty context mode")
                yield {
                    'phase': 'analyzing',
                    'message': 'AI 분석을 시작합니다...'
                }

                # LLM에 빈 컨텍스트 전달
                async for event in self._llm_analyze_empty(question, max_retries):
                    yield event

                return

            # ========== Stage 3: Reranking ==========
            yield {
                'phase': 'ranking',
                'message': '문서 관련성을 재평가하고 있습니다...'
            }

            reranked_docs = self.reranker.rerank(
                question=question,
                documents=search_docs,
                top_k=self.final_top_k
            )

            yield {
                'phase': 'ranking_complete',
                'top_k': len(reranked_docs),
                'message': f"재순위화 완료: Top-{len(reranked_docs)} 선별"
            }

            # ========== Stage 4: Context Compression ==========
            yield {
                'phase': 'compressing',
                'message': '컨텍스트를 압축하고 있습니다...'
            }

            compressed_docs = await self.compressor.compress(
                documents=reranked_docs,
                question=question
            )

            # 압축 통계
            total_original = sum(doc['original_tokens'] for doc in compressed_docs)
            total_compressed = sum(doc['compressed_tokens'] for doc in compressed_docs)
            avg_ratio = total_compressed / max(total_original, 1)

            yield {
                'phase': 'compression_complete',
                'stats': {
                    'documents': len(compressed_docs),
                    'original_tokens': total_original,
                    'compressed_tokens': total_compressed,
                    'compression_ratio': avg_ratio
                },
                'message': f"압축 완료: {total_original} → {total_compressed} 토큰 ({avg_ratio:.2%})"
            }

            # ========== Stage 5: LLM Analysis ==========
            yield {
                'phase': 'analyzing',
                'message': 'AI 분석을 시작합니다...'
            }

            # 압축된 컨텍스트 구성
            context = self._build_compressed_context(compressed_docs, entities)

            # 사용자 메시지 저장
            await self._save_message(
                role=AnalysisMessage.Role.USER,
                content=question,
                suggestions=[],
                input_tokens=0,
                output_tokens=0
            )

            # LLM 스트리밍
            async for event in self.llm.generate_stream(
                context=context,
                question=question,
                max_retries=max_retries
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

                    await self._save_message(
                        role=AnalysisMessage.Role.SYSTEM,
                        content=f"[에러] {event['message']}",
                        suggestions=[],
                        input_tokens=0,
                        output_tokens=0
                    )
                    return

            # 응답 파싱
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

            # 탐험 경로 업데이트
            if suggestions:
                await self._update_exploration_path(suggestions)

            # 완료
            elapsed_ms = int((time.time() - start_time) * 1000)

            yield {
                'phase': 'complete',
                'data': {
                    'content': cleaned_content,
                    'suggestions': suggestions,
                    'basket_actions': basket_actions,
                    'usage': {
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens
                    },
                    'latency_ms': elapsed_ms,
                    'pipeline_stats': {
                        'entities': len(normalized_symbols),
                        'search_results': len(search_docs),
                        'reranked': len(reranked_docs),
                        'compressed': len(compressed_docs),
                        'compression_ratio': avg_ratio
                    }
                }
            }

        except Exception as e:
            logger.exception(f"PipelineV2 error: {e}")

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

    async def _fetch_documents(self, symbols: List[str]) -> List[dict]:
        """
        DB/Neo4j에서 문서 조회

        Args:
            symbols: 종목 심볼 리스트

        Returns:
            문서 리스트
        """
        if not symbols:
            logger.warning("No symbols to fetch documents")
            return []

        # TODO: 실제 구현 필요
        # - stocks 앱에서 재무제표, 뉴스 등 조회
        # - Neo4j에서 관계 정보 조회
        # - 적절한 형식으로 문서 리스트 구성

        logger.warning("Document fetching not implemented, using empty list")
        return []

    def _resolve_search_results(self, search_results: List[Dict[str, Any]]) -> List[tuple]:
        """
        Hybrid Search 결과를 문서 튜플 리스트로 변환

        Args:
            search_results: [{'doc_id': str, 'score': float, 'scores': {...}}, ...]

        Returns:
            [(doc, score, breakdown), ...]
        """
        resolved = []

        for result in search_results:
            doc_id = result['doc_id']

            # doc_id로 문서 찾기
            doc = self._find_document_by_id(doc_id)
            if doc is None:
                logger.warning(f"Document not found for doc_id: {doc_id}")
                continue

            resolved.append((
                doc,
                result['score'],
                result['scores']
            ))

        return resolved

    def _find_document_by_id(self, doc_id: str) -> Optional[dict]:
        """
        doc_id로 문서 찾기

        Args:
            doc_id: 문서 ID

        Returns:
            문서 딕셔너리 (없으면 None)
        """
        for doc in self.documents:
            # id 필드가 있으면 직접 비교
            if 'id' in doc and str(doc['id']) == doc_id:
                return doc

            # id가 없으면 symbol+date+type 조합으로 생성하여 비교
            parts = []
            if 'symbol' in doc:
                parts.append(doc['symbol'].upper())
            if 'date' in doc or 'created_at' in doc:
                parts.append(doc.get('date', doc.get('created_at', '')))
            if 'type' in doc:
                parts.append(doc['type'])

            if parts and '_'.join(parts) == doc_id:
                return doc

        return None

    def _build_compressed_context(
        self,
        compressed_docs: List[dict],
        entities: dict
    ) -> str:
        """
        압축된 문서로 컨텍스트 구성

        Args:
            compressed_docs: 압축된 문서 리스트
            entities: 추출된 엔티티

        Returns:
            컨텍스트 문자열
        """
        from datetime import date

        today = date.today().strftime('%Y년 %m월 %d일')

        context_parts = [
            "=== 분석 컨텍스트 ===",
            f"분석 기준일: {today}",
            f"검색된 문서 수: {len(compressed_docs)}",
            ""
        ]

        # 추출된 엔티티
        if entities.get('stocks'):
            context_parts.append(f"관련 종목: {', '.join(entities['stocks'])}")
        if entities.get('metrics'):
            context_parts.append(f"관련 지표: {', '.join(entities['metrics'])}")
        if entities.get('timeframe'):
            context_parts.append(f"시간 범위: {entities['timeframe']}")

        context_parts.append("")
        context_parts.append("=== 관련 문서 (압축됨) ===")
        context_parts.append("")

        # 압축된 문서들
        for i, doc in enumerate(compressed_docs, 1):
            title = doc.get('title', f'문서 {i}')
            compressed_text = doc['compressed']

            context_parts.append(f"[문서 {i}] {title}")
            context_parts.append(compressed_text)
            context_parts.append("")

        return '\n'.join(context_parts)

    async def _llm_analyze_empty(
        self,
        question: str,
        max_retries: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        빈 컨텍스트로 LLM 분석 (검색 결과가 없을 때)

        Args:
            question: 사용자 질문
            max_retries: 최대 재시도 횟수

        Yields:
            LLM 이벤트
        """
        from datetime import date

        today = date.today().strftime('%Y년 %m월 %d일')
        empty_context = f"""=== 분석 컨텍스트 ===
분석 기준일: {today}
검색된 문서 수: 0

현재 관련 데이터가 없습니다.
일반적인 투자 관점에서 간략히 답변하고, 필요한 데이터를 바구니에 추가하도록 제안해주세요.
"""

        full_response = ""
        input_tokens = 0
        output_tokens = 0

        # 사용자 메시지 저장
        await self._save_message(
            role=AnalysisMessage.Role.USER,
            content=question,
            suggestions=[],
            input_tokens=0,
            output_tokens=0
        )

        # LLM 스트리밍
        async for event in self.llm.generate_stream(
            context=empty_context,
            question=question,
            max_retries=max_retries
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

        # 응답 파싱
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

        # 완료
        yield {
            'phase': 'complete',
            'data': {
                'content': cleaned_content,
                'suggestions': suggestions,
                'basket_actions': basket_actions,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                },
                'pipeline_stats': {
                    'entities': 0,
                    'search_results': 0,
                    'reranked': 0,
                    'compressed': 0,
                    'compression_ratio': 0.0
                }
            }
        }

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


# ========== Event Type Constants ==========

class PipelineV2EventType:
    """파이프라인 V2 이벤트 타입 상수"""
    EXTRACTING = 'extracting'
    ENTITIES_EXTRACTED = 'entities_extracted'
    SEARCHING = 'searching'
    SEARCH_COMPLETE = 'search_complete'
    RANKING = 'ranking'
    RANKING_COMPLETE = 'ranking_complete'
    COMPRESSING = 'compressing'
    COMPRESSION_COMPLETE = 'compression_complete'
    ANALYZING = 'analyzing'
    STREAMING = 'streaming'
    COMPLETE = 'complete'
    ERROR = 'error'
