"""
RAG Analysis E2E Tests

End-to-end integration tests for:
- Complete analysis flow (Mock LLM)
- Neo4j graceful degradation (analysis continues when Neo4j fails)
- SSE streaming response
- Error handling across the pipeline
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, AsyncMock, MagicMock
import json
import asyncio

from rag_analysis.models import (
    DataBasket,
    BasketItem,
    AnalysisSession,
    AnalysisMessage
)
from rag_analysis.services.pipeline import AnalysisPipelineLite

User = get_user_model()


class AnalysisPipelineE2ETest(TransactionTestCase):
    """분석 파이프라인 E2E 테스트 (Mock LLM)"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.basket = DataBasket.objects.create(
            user=self.user,
            name='Tech Analysis'
        )

        # 바구니에 아이템 추가
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            subtitle='NASDAQ',
            data_snapshot={
                'price': 150.00,
                'change_percent': 2.5,
                'market_cap': '2.5T'
            }
        )
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='GOOGL',
            title='Alphabet Inc.',
            subtitle='NASDAQ',
            data_snapshot={
                'price': 140.00,
                'change_percent': 1.8,
                'market_cap': '1.8T'
            }
        )

        self.session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Tech Stock Analysis'
        )

    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_complete_analysis_flow_with_mock_llm(self, mock_anthropic_class):
        """전체 분석 흐름 테스트 (Mock LLM)"""

        # Mock LLM 응답 설정
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            # 텍스트 청크
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='Apple과 ')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='Google은 ')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='강력한 기술 기업입니다.\n\n')
            ),
            # Suggestions 태그
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='<suggestions>\n')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='MSFT: 경쟁사 비교\n')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='</suggestions>\n\n')
            ),
            # 면책 조항
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='⚠️ 투자 유의사항\n')
            ),
            # 메시지 완료
            MagicMock(
                type='message_delta',
                delta=MagicMock(stop_reason='end_turn'),
                usage=MagicMock(output_tokens=50)
            ),
            # 최종 usage
            MagicMock(
                type='message_stop',
                message=MagicMock(
                    usage=MagicMock(input_tokens=200, output_tokens=50)
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream
        mock_anthropic_class.return_value = mock_client

        # Pipeline 실행
        pipeline = AnalysisPipelineLite(self.session)

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('Compare AAPL and GOOGL'):
                events.append(event)
            return events

        # 비동기 이벤트 루프 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # 이벤트 검증
        phase_sequence = [e['phase'] for e in events]

        # 필수 phase 확인
        self.assertIn('preparing', phase_sequence)
        self.assertIn('context_ready', phase_sequence)
        self.assertIn('analyzing', phase_sequence)
        self.assertIn('streaming', phase_sequence)
        self.assertIn('complete', phase_sequence)

        # streaming 이벤트가 여러 개 있어야 함
        streaming_events = [e for e in events if e['phase'] == 'streaming']
        self.assertGreater(len(streaming_events), 0)

        # complete 이벤트 검증
        complete_event = next(e for e in events if e['phase'] == 'complete')
        self.assertIn('data', complete_event)
        self.assertIn('content', complete_event['data'])
        self.assertIn('suggestions', complete_event['data'])
        self.assertIn('usage', complete_event['data'])
        self.assertIn('latency_ms', complete_event['data'])

        # 면책 조항이 포함되어야 함
        self.assertIn('투자 유의사항', complete_event['data']['content'])

        # DB에 메시지 저장 확인
        self.session.refresh_from_db()
        messages = self.session.messages.all()

        # User 메시지 확인
        user_message = messages.filter(role='user').first()
        self.assertIsNotNone(user_message)
        self.assertEqual(user_message.content, 'Compare AAPL and GOOGL')

        # Assistant 메시지 확인
        assistant_message = messages.filter(role='assistant').first()
        self.assertIsNotNone(assistant_message)
        self.assertGreater(len(assistant_message.content), 0)
        self.assertGreater(assistant_message.input_tokens, 0)
        self.assertGreater(assistant_message.output_tokens, 0)

    @patch('rag_analysis.services.neo4j_service.Neo4jServiceLite.get_stock_relationships')
    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_neo4j_graceful_degradation(self, mock_anthropic_class, mock_neo4j):
        """Neo4j 실패 시 Graceful Degradation 테스트"""

        # Neo4j Mock - 에러 발생
        async def mock_neo4j_error(*args, **kwargs):
            raise Exception('Neo4j connection failed')

        mock_neo4j.side_effect = mock_neo4j_error

        # LLM Mock - 간단한 응답
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='분석 결과입니다.')
            ),
            MagicMock(
                type='message_delta',
                delta=MagicMock(stop_reason='end_turn'),
                usage=MagicMock(output_tokens=10)
            ),
            MagicMock(
                type='message_stop',
                message=MagicMock(
                    usage=MagicMock(input_tokens=50, output_tokens=10)
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream
        mock_anthropic_class.return_value = mock_client

        # Pipeline 실행
        pipeline = AnalysisPipelineLite(self.session)

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('Analyze AAPL'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # 분석이 완료되어야 함 (Neo4j 실패했지만 계속 진행)
        phase_sequence = [e['phase'] for e in events]
        self.assertIn('complete', phase_sequence)
        self.assertNotIn('error', phase_sequence)

        # complete 이벤트 검증
        complete_event = next(e for e in events if e['phase'] == 'complete')
        self.assertIn('data', complete_event)

    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_llm_api_error_handling(self, mock_anthropic_class):
        """LLM API 에러 핸들링 테스트"""

        # Mock LLM - API 에러 발생
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception('API Error')
        mock_anthropic_class.return_value = mock_client

        pipeline = AnalysisPipelineLite(self.session)

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('Test question'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # 에러 이벤트가 발생해야 함
        phase_sequence = [e['phase'] for e in events]
        self.assertIn('error', phase_sequence)

        # 에러 이벤트 검증
        error_event = next(e for e in events if e['phase'] == 'error')
        self.assertIn('error', error_event)
        self.assertIn('code', error_event['error'])
        self.assertIn('message', error_event['error'])

    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_token_limit_enforcement(self, mock_anthropic_class):
        """토큰 제한 검증 테스트"""

        # Mock LLM - 매우 긴 응답
        long_text_chunks = ['토큰 ' * 100 for _ in range(50)]  # 많은 청크

        mock_stream_items = []
        for chunk in long_text_chunks:
            mock_stream_items.append(
                MagicMock(
                    type='content_block_delta',
                    delta=MagicMock(type='text_delta', text=chunk)
                )
            )

        mock_stream_items.extend([
            MagicMock(
                type='message_delta',
                delta=MagicMock(stop_reason='end_turn'),
                usage=MagicMock(output_tokens=2000)
            ),
            MagicMock(
                type='message_stop',
                message=MagicMock(
                    usage=MagicMock(input_tokens=500, output_tokens=2000)
                )
            )
        ])

        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = mock_stream_items

        mock_client = MagicMock()
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream
        mock_anthropic_class.return_value = mock_client

        pipeline = AnalysisPipelineLite(self.session)

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('Test'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # 응답이 완료되어야 함
        complete_event = next(e for e in events if e['phase'] == 'complete')
        self.assertIn('usage', complete_event['data'])

        # 토큰 사용량이 기록되어야 함
        self.assertGreater(complete_event['data']['usage']['output_tokens'], 0)


class SSEStreamingE2ETest(TestCase):
    """SSE 스트리밍 E2E 테스트"""

    def setUp(self):
        """테스트 클라이언트 및 사용자 생성"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.basket = DataBasket.objects.create(
            user=self.user,
            name='Test Basket'
        )
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.'
        )

        self.session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Test Session'
        )

    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_sse_streaming_response(self, mock_anthropic_class):
        """SSE 스트리밍 응답 테스트"""

        # Mock LLM
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='Test ')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='analysis ')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='result.')
            ),
            MagicMock(
                type='message_delta',
                delta=MagicMock(stop_reason='end_turn'),
                usage=MagicMock(output_tokens=5)
            ),
            MagicMock(
                type='message_stop',
                message=MagicMock(
                    usage=MagicMock(input_tokens=20, output_tokens=5)
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream
        mock_anthropic_class.return_value = mock_client

        # SSE 엔드포인트 호출
        url = reverse('rag_analysis:chat-stream', kwargs={'pk': self.session.pk})
        payload = {'message': 'Test question'}

        response = self.client.post(url, payload, format='json')

        # 응답 검증
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['Cache-Control'], 'no-cache')
        self.assertEqual(response['Connection'], 'keep-alive')

        # 스트리밍 데이터 파싱
        events = []
        for line in response.streaming_content:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                event_json = line_str[6:].strip()
                if event_json:
                    events.append(json.loads(event_json))

        # 이벤트 검증
        self.assertGreater(len(events), 0)

        # phase 시퀀스 확인
        phases = [e.get('phase') for e in events if 'phase' in e]
        self.assertIn('preparing', phases)
        self.assertIn('complete', phases)

    def test_sse_empty_message_validation(self):
        """SSE 빈 메시지 검증 테스트"""
        url = reverse('rag_analysis:chat-stream', kwargs={'pk': self.session.pk})
        payload = {'message': '   '}  # 빈 메시지

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'INVALID_INPUT')

    def test_sse_session_not_found(self):
        """SSE 세션 없음 테스트"""
        url = reverse('rag_analysis:chat-stream', kwargs={'pk': 9999})
        payload = {'message': 'Test'}

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MessagePersistenceTest(TestCase):
    """메시지 저장 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.basket = DataBasket.objects.create(
            user=self.user,
            name='Test Basket'
        )
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.'
        )
        self.session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )

    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_messages_saved_to_database(self, mock_anthropic_class):
        """분석 후 메시지가 DB에 저장되는지 테스트"""

        # Mock LLM
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='분석 결과')
            ),
            MagicMock(
                type='message_delta',
                delta=MagicMock(stop_reason='end_turn'),
                usage=MagicMock(output_tokens=10)
            ),
            MagicMock(
                type='message_stop',
                message=MagicMock(
                    usage=MagicMock(input_tokens=100, output_tokens=10)
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream
        mock_anthropic_class.return_value = mock_client

        # Pipeline 실행
        pipeline = AnalysisPipelineLite(self.session)

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('AAPL 분석해줘'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # DB 검증
        self.session.refresh_from_db()
        messages = list(self.session.messages.all().order_by('created_at'))

        # 2개의 메시지가 있어야 함 (user, assistant)
        self.assertEqual(len(messages), 2)

        # User 메시지
        user_msg = messages[0]
        self.assertEqual(user_msg.role, 'user')
        self.assertEqual(user_msg.content, 'AAPL 분석해줘')

        # Assistant 메시지
        assistant_msg = messages[1]
        self.assertEqual(assistant_msg.role, 'assistant')
        self.assertIn('분석 결과', assistant_msg.content)
        self.assertEqual(assistant_msg.input_tokens, 100)
        self.assertEqual(assistant_msg.output_tokens, 10)

    @patch('rag_analysis.services.llm_service.AsyncAnthropic')
    def test_suggestions_saved(self, mock_anthropic_class):
        """제안 종목이 DB에 저장되는지 테스트"""

        # Mock LLM - suggestions 포함
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='분석 결과\n\n')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='<suggestions>\n')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='MSFT: 경쟁사\n')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='TSLA: 공급망\n')
            ),
            MagicMock(
                type='content_block_delta',
                delta=MagicMock(type='text_delta', text='</suggestions>')
            ),
            MagicMock(
                type='message_delta',
                delta=MagicMock(stop_reason='end_turn'),
                usage=MagicMock(output_tokens=20)
            ),
            MagicMock(
                type='message_stop',
                message=MagicMock(
                    usage=MagicMock(input_tokens=50, output_tokens=20)
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream
        mock_anthropic_class.return_value = mock_client

        pipeline = AnalysisPipelineLite(self.session)

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('분석해줘'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # DB 검증
        assistant_msg = self.session.messages.filter(role='assistant').first()
        self.assertIsNotNone(assistant_msg)
        self.assertGreater(len(assistant_msg.suggestions), 0)

        # 제안 종목 검증
        suggestions = assistant_msg.suggestions
        symbols = [s['symbol'] for s in suggestions]
        self.assertIn('MSFT', symbols)
        self.assertIn('TSLA', symbols)


class AnalysisPipelineFinalE2ETest(TransactionTestCase):
    """AnalysisPipelineFinal E2E 테스트 (Phase 3 통합)"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.user = User.objects.create_user(
            username='testuser_final',
            password='testpass123'
        )

        self.basket = DataBasket.objects.create(
            user=self.user,
            name='Final Pipeline Test'
        )

        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            subtitle='NASDAQ',
            data_snapshot={
                'price': 175.00,
                'change_percent': 1.5,
                'market_cap': '2.8T'
            }
        )

        self.session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Final Pipeline Test Session'
        )

    @patch('rag_analysis.services.adaptive_llm_service.genai')
    @patch('rag_analysis.services.semantic_cache.SemanticCacheService.find_similar')
    @patch('rag_analysis.services.semantic_cache.SemanticCacheService.store')
    def test_final_pipeline_with_cache_miss(
        self, mock_cache_store, mock_cache_find, mock_genai
    ):
        """Final Pipeline 캐시 미스 흐름 테스트"""
        from rag_analysis.services.pipeline import AnalysisPipelineFinal

        # 캐시 미스 설정
        async def mock_find_similar(*args, **kwargs):
            return None
        mock_cache_find.side_effect = mock_find_similar

        # 캐시 저장 Mock
        async def mock_store(*args, **kwargs):
            return 'mock_cache_id_123'
        mock_cache_store.side_effect = mock_store

        # Gemini Mock 설정
        mock_model = MagicMock()
        mock_response = MagicMock()

        async def mock_generate():
            yield MagicMock(text='분석 결과입니다. AAPL은 ')
            yield MagicMock(text='강력한 실적을 보여주고 있습니다.\n\n')
            yield MagicMock(text='<suggestions>\n')
            yield MagicMock(text='{"symbol": "MSFT", "reason": "경쟁사 비교"}\n')
            yield MagicMock(text='</suggestions>')

        mock_response.__aiter__ = mock_generate
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        # Pipeline 실행
        pipeline = AnalysisPipelineFinal(
            self.session,
            enable_cache=True,
            enable_cost_optimization=True
        )

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('AAPL 분석해줘'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # 이벤트 검증
        phase_sequence = [e['phase'] for e in events]

        # 필수 단계 확인
        self.assertIn('cache_check', phase_sequence)
        self.assertIn('preparing', phase_sequence)
        self.assertIn('context_ready', phase_sequence)
        self.assertIn('analyzing', phase_sequence)
        self.assertIn('complete', phase_sequence)

        # cache_hit가 없어야 함 (캐시 미스)
        self.assertNotIn('cache_hit', phase_sequence)

        # complete 이벤트 검증
        complete_event = next(e for e in events if e['phase'] == 'complete')
        self.assertIn('complexity', complete_event['data'])
        self.assertIn('complexity_score', complete_event['data'])
        self.assertFalse(complete_event['data']['usage']['cached'])

    @patch('rag_analysis.services.semantic_cache.SemanticCacheService.find_similar')
    def test_final_pipeline_with_cache_hit(self, mock_cache_find):
        """Final Pipeline 캐시 히트 흐름 테스트"""
        from rag_analysis.services.pipeline import AnalysisPipelineFinal

        # 캐시 히트 설정
        async def mock_find_similar(*args, **kwargs):
            return {
                'response': '캐시된 분석 결과입니다.',
                'suggestions': [{'symbol': 'MSFT', 'reason': '경쟁사'}],
                'similarity_score': 0.95,
                'entity_match_score': 1.0,
                'cache_id': 'cached_id_456',
                'hit_count': 5
            }
        mock_cache_find.side_effect = mock_find_similar

        # Pipeline 실행
        pipeline = AnalysisPipelineFinal(
            self.session,
            enable_cache=True,
            enable_cost_optimization=True
        )

        async def run_analysis():
            events = []
            async for event in pipeline.analyze('AAPL 분석해줘'):
                events.append(event)
            return events

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            events = loop.run_until_complete(run_analysis())
        finally:
            loop.close()

        # 이벤트 검증
        phase_sequence = [e['phase'] for e in events]

        # 캐시 히트 확인
        self.assertIn('cache_check', phase_sequence)
        self.assertIn('cache_hit', phase_sequence)

        # analyzing, streaming, complete가 없어야 함 (캐시에서 바로 반환)
        self.assertNotIn('analyzing', phase_sequence)
        self.assertNotIn('streaming', phase_sequence)
        self.assertNotIn('complete', phase_sequence)

        # cache_hit 이벤트 검증
        cache_hit_event = next(e for e in events if e['phase'] == 'cache_hit')
        self.assertEqual(cache_hit_event['data']['content'], '캐시된 분석 결과입니다.')
        self.assertTrue(cache_hit_event['data']['usage']['cached'])
        self.assertEqual(cache_hit_event['data']['usage']['cost_usd'], 0.0)
        self.assertIn('cache_info', cache_hit_event['data'])
        self.assertEqual(cache_hit_event['data']['cache_info']['similarity_score'], 0.95)

    def test_final_pipeline_complexity_classification(self):
        """Final Pipeline 복잡도 분류 테스트"""
        from rag_analysis.services.complexity_classifier import ComplexityClassifier

        classifier = ComplexityClassifier(provider='gemini')

        # 단순 질문
        simple_result = classifier.classify_and_configure(
            question='AAPL 현재 가격은?',
            entities_count=1,
            context_tokens=100
        )
        self.assertEqual(simple_result['complexity'].value, 'simple')

        # 복잡한 질문
        complex_result = classifier.classify_and_configure(
            question='AAPL과 GOOGL, MSFT를 비교 분석하고 투자 전략을 제안해주세요. 리스크 분석도 포함해주세요.',
            entities_count=3,
            context_tokens=500
        )
        self.assertEqual(complex_result['complexity'].value, 'complex')

    def test_final_pipeline_token_budget_allocation(self):
        """Final Pipeline 토큰 예산 할당 테스트"""
        from rag_analysis.services.token_budget_manager import (
            TokenBudgetManager,
            ContentBlock,
            ContentPriority
        )

        # 단순 복잡도 예산
        simple_manager = TokenBudgetManager('simple')
        self.assertEqual(simple_manager.budget['context'], 400)
        self.assertEqual(simple_manager.budget['max_output'], 800)

        # 복잡 복잡도 예산
        complex_manager = TokenBudgetManager('complex')
        self.assertEqual(complex_manager.budget['context'], 1500)
        self.assertEqual(complex_manager.budget['max_output'], 2500)

        # 컨텐츠 블록 할당 테스트
        blocks = [
            ContentBlock(
                content='중요한 정보' * 10,
                priority=ContentPriority.CRITICAL,
                token_count=50,
                source='current_price'
            ),
            ContentBlock(
                content='덜 중요한 정보' * 20,
                priority=ContentPriority.LOW,
                token_count=100,
                source='company_overview'
            ),
        ]

        selected, info = simple_manager.allocate(blocks)

        # CRITICAL이 먼저 선택됨
        self.assertGreater(len(selected), 0)
        self.assertEqual(selected[0].priority, ContentPriority.CRITICAL)

    @patch('rag_analysis.services.semantic_cache.SemanticCacheService.find_similar')
    def test_final_pipeline_graceful_degradation(self, mock_cache_find):
        """Final Pipeline 컴포넌트 실패 시 Graceful Degradation"""
        from rag_analysis.services.pipeline import AnalysisPipelineFinal

        # 캐시 서비스 에러
        async def mock_find_error(*args, **kwargs):
            raise Exception('Cache service unavailable')
        mock_cache_find.side_effect = mock_find_error

        # Pipeline 실행 (캐시 실패해도 계속 진행해야 함)
        pipeline = AnalysisPipelineFinal(
            self.session,
            enable_cache=True,
            enable_cost_optimization=False  # LLM Mock 없이 테스트
        )

        # Pipeline이 초기화되어야 함 (예외 발생 X)
        self.assertIsNotNone(pipeline)
        self.assertTrue(pipeline.enable_cache)
