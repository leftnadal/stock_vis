"""
RAG Analysis Model Tests

Tests for:
- DataBasket CRUD operations
- BasketItem 15-item limit enforcement
- BasketItem unique_together constraint
- AnalysisSession creation and exploration tracking
- AnalysisMessage creation and token tracking
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import datetime

from rag_analysis.models import (
    DataBasket,
    BasketItem,
    AnalysisSession,
    AnalysisMessage
)

User = get_user_model()


class DataBasketModelTest(TestCase):
    """DataBasket 모델 테스트"""

    def setUp(self):
        """테스트 사용자 생성"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_basket_creation(self):
        """바구니 생성 테스트"""
        basket = DataBasket.objects.create(
            user=self.user,
            name='Test Basket',
            description='Test description'
        )

        self.assertEqual(basket.name, 'Test Basket')
        self.assertEqual(basket.description, 'Test description')
        self.assertEqual(basket.user, self.user)
        self.assertEqual(basket.items_count, 0)
        self.assertTrue(basket.can_add_item())

    def test_basket_default_name(self):
        """바구니 기본 이름 테스트"""
        basket = DataBasket.objects.create(user=self.user)
        self.assertEqual(basket.name, 'My Basket')

    def test_basket_str_representation(self):
        """바구니 문자열 표현 테스트"""
        basket = DataBasket.objects.create(
            user=self.user,
            name='Investment Analysis'
        )
        expected = f"{self.user.username}s Investment Analysis"
        self.assertEqual(str(basket), expected)

    def test_basket_ordering(self):
        """바구니 정렬 테스트 (최근 업데이트 순)"""
        basket1 = DataBasket.objects.create(user=self.user, name='First')
        basket2 = DataBasket.objects.create(user=self.user, name='Second')

        baskets = DataBasket.objects.all()
        self.assertEqual(baskets[0], basket2)  # 최근 생성된 것이 먼저
        self.assertEqual(baskets[1], basket1)

    def test_items_count_property(self):
        """아이템 개수 속성 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')

        # 아이템 추가 전
        self.assertEqual(basket.items_count, 0)

        # 아이템 추가
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )

        # 캐시 갱신을 위해 다시 조회
        basket.refresh_from_db()
        self.assertEqual(basket.items_count, 1)

    def test_can_add_item_true(self):
        """아이템 추가 가능 상태 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')

        # 14개 추가
        for i in range(14):
            BasketItem.objects.create(
                basket=basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test Stock {i}',
                data_snapshot={}
            )

        basket.refresh_from_db()
        self.assertTrue(basket.can_add_item())

    def test_can_add_item_false(self):
        """아이템 추가 불가능 상태 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')

        # 15개 추가 (MAX_ITEMS)
        for i in range(15):
            BasketItem.objects.create(
                basket=basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test Stock {i}',
                data_snapshot={}
            )

        basket.refresh_from_db()
        self.assertFalse(basket.can_add_item())

    def test_max_items_constant(self):
        """MAX_ITEMS 상수 테스트"""
        self.assertEqual(DataBasket.MAX_ITEMS, 15)


class BasketItemModelTest(TestCase):
    """BasketItem 모델 테스트"""

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

    def test_item_creation_stock(self):
        """주식 아이템 생성 테스트"""
        item = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            subtitle='NASDAQ',
            data_snapshot={'price': 150.00, 'change': 2.5}
        )

        self.assertEqual(item.basket, self.basket)
        self.assertEqual(item.item_type, 'stock')
        self.assertEqual(item.reference_id, 'AAPL')
        self.assertEqual(item.title, 'Apple Inc.')
        self.assertEqual(item.subtitle, 'NASDAQ')
        self.assertEqual(item.data_snapshot['price'], 150.00)
        self.assertIsNotNone(item.snapshot_date)

    def test_item_creation_all_types(self):
        """모든 아이템 타입 생성 테스트"""
        types = ['stock', 'news', 'financial', 'macro']

        for item_type in types:
            item = BasketItem.objects.create(
                basket=self.basket,
                item_type=item_type,
                reference_id=f'TEST_{item_type}',
                title=f'Test {item_type} item',
                data_snapshot={}
            )
            self.assertEqual(item.item_type, item_type)

    def test_item_type_display(self):
        """아이템 타입 표시명 테스트"""
        item = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )
        self.assertEqual(item.get_item_type_display(), '종목')

    def test_item_str_representation(self):
        """아이템 문자열 표현 테스트"""
        item = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )
        expected = "종목: Apple Inc."
        self.assertEqual(str(item), expected)

    def test_item_unique_together_constraint(self):
        """unique_together 제약 조건 테스트"""
        # 첫 번째 아이템 생성
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )

        # 같은 바구니에 같은 아이템 중복 추가 시도
        with self.assertRaises(IntegrityError):
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id='AAPL',
                title='Apple Inc. (Duplicate)',
                data_snapshot={}
            )

    def test_item_different_basket_same_reference(self):
        """다른 바구니에는 같은 아이템 추가 가능 테스트"""
        basket2 = DataBasket.objects.create(
            user=self.user,
            name='Test Basket 2'
        )

        # 첫 번째 바구니에 추가
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )

        # 두 번째 바구니에 같은 아이템 추가 (성공해야 함)
        item2 = BasketItem.objects.create(
            basket=basket2,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )

        self.assertIsNotNone(item2.id)
        self.assertEqual(BasketItem.objects.count(), 2)

    def test_item_15_limit_validation(self):
        """15개 제한 검증 테스트"""
        # 15개 추가 (성공)
        for i in range(15):
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test Stock {i}',
                data_snapshot={}
            )

        self.basket.refresh_from_db()
        self.assertEqual(self.basket.items_count, 15)

        # 16번째 추가 시도 (ValidationError 발생)
        with self.assertRaises(ValidationError) as context:
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id='TEST16',
                title='Test Stock 16',
                data_snapshot={}
            )

        # 에러 메시지 확인
        self.assertIn('바구니에는 최대', str(context.exception))
        self.assertIn('15개', str(context.exception))

    def test_item_limit_boundary(self):
        """경계값 테스트: 정확히 15개까지는 가능"""
        # 14개 추가
        for i in range(14):
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test Stock {i}',
                data_snapshot={}
            )

        # 15번째 추가 (성공해야 함)
        item15 = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='TEST15',
            title='Test Stock 15',
            data_snapshot={}
        )

        self.assertIsNotNone(item15.id)
        self.basket.refresh_from_db()
        self.assertEqual(self.basket.items_count, 15)

    def test_item_ordering(self):
        """아이템 정렬 테스트 (생성 순서)"""
        item1 = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple',
            data_snapshot={}
        )
        item2 = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='GOOGL',
            title='Google',
            data_snapshot={}
        )

        items = self.basket.items.all()
        self.assertEqual(items[0], item1)  # 먼저 생성된 것이 먼저
        self.assertEqual(items[1], item2)

    def test_item_default_data_snapshot(self):
        """data_snapshot 기본값 테스트"""
        item = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={}
        )
        self.assertEqual(item.data_snapshot, {})


class AnalysisSessionModelTest(TestCase):
    """AnalysisSession 모델 테스트"""

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

    def test_session_creation(self):
        """세션 생성 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Investment Analysis'
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.basket, self.basket)
        self.assertEqual(session.title, 'Investment Analysis')
        self.assertEqual(session.status, 'active')
        self.assertEqual(session.exploration_path, [])

    def test_session_default_status(self):
        """세션 기본 상태 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )
        self.assertEqual(session.status, AnalysisSession.Status.ACTIVE)

    def test_session_str_representation(self):
        """세션 문자열 표현 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )
        expected = f"Session {session.id} - {self.user.username}"
        self.assertEqual(str(session), expected)

    def test_session_status_choices(self):
        """세션 상태 선택지 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )

        # ACTIVE
        session.status = 'active'
        session.save()
        self.assertEqual(session.status, 'active')

        # COMPLETED
        session.status = 'completed'
        session.save()
        self.assertEqual(session.status, 'completed')

        # ERROR
        session.status = 'error'
        session.save()
        self.assertEqual(session.status, 'error')

    def test_session_without_basket(self):
        """바구니 없이 세션 생성 테스트 (NULL 가능)"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=None,
            title='General Analysis'
        )

        self.assertIsNone(session.basket)
        self.assertEqual(session.title, 'General Analysis')

    def test_session_basket_cascade_on_delete(self):
        """바구니 삭제 시 세션 처리 테스트 (SET_NULL)"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )

        basket_id = self.basket.id
        self.basket.delete()

        session.refresh_from_db()
        self.assertIsNone(session.basket)

    def test_add_exploration(self):
        """탐험 경로 추가 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )

        # 탐험 경로 추가
        session.add_exploration(
            entity_type='stock',
            entity_id='AAPL',
            reason='User selected from basket'
        )

        session.refresh_from_db()
        self.assertEqual(len(session.exploration_path), 1)

        exploration = session.exploration_path[0]
        self.assertEqual(exploration['type'], 'stock')
        self.assertEqual(exploration['id'], 'AAPL')
        self.assertEqual(exploration['reason'], 'User selected from basket')
        self.assertIn('timestamp', exploration)

    def test_add_multiple_explorations(self):
        """여러 탐험 경로 추가 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )

        # 여러 탐험 추가
        session.add_exploration('stock', 'AAPL', 'Initial selection')
        session.add_exploration('stock', 'TSLA', 'Competitor analysis')
        session.add_exploration('stock', 'NVDA', 'Supply chain exploration')

        session.refresh_from_db()
        self.assertEqual(len(session.exploration_path), 3)

        # 순서 확인
        self.assertEqual(session.exploration_path[0]['id'], 'AAPL')
        self.assertEqual(session.exploration_path[1]['id'], 'TSLA')
        self.assertEqual(session.exploration_path[2]['id'], 'NVDA')

    def test_session_ordering(self):
        """세션 정렬 테스트 (최근 업데이트 순)"""
        session1 = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='First'
        )
        session2 = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Second'
        )

        sessions = AnalysisSession.objects.all()
        self.assertEqual(sessions[0], session2)  # 최근 것이 먼저
        self.assertEqual(sessions[1], session1)


class AnalysisMessageModelTest(TestCase):
    """AnalysisMessage 모델 테스트"""

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
        self.session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket
        )

    def test_message_creation_user(self):
        """사용자 메시지 생성 테스트"""
        message = AnalysisMessage.objects.create(
            session=self.session,
            role='user',
            content='Analyze AAPL stock'
        )

        self.assertEqual(message.session, self.session)
        self.assertEqual(message.role, 'user')
        self.assertEqual(message.content, 'Analyze AAPL stock')
        self.assertEqual(message.suggestions, [])
        self.assertEqual(message.input_tokens, 0)
        self.assertEqual(message.output_tokens, 0)

    def test_message_creation_assistant(self):
        """어시스턴트 메시지 생성 테스트"""
        suggestions = [
            {'symbol': 'TSLA', 'reason': 'Competitor'},
            {'symbol': 'NVDA', 'reason': 'Supplier'}
        ]

        message = AnalysisMessage.objects.create(
            session=self.session,
            role='assistant',
            content='Apple shows strong fundamentals...',
            suggestions=suggestions,
            input_tokens=150,
            output_tokens=300
        )

        self.assertEqual(message.role, 'assistant')
        self.assertEqual(len(message.suggestions), 2)
        self.assertEqual(message.input_tokens, 150)
        self.assertEqual(message.output_tokens, 300)

    def test_message_role_choices(self):
        """메시지 역할 선택지 테스트"""
        roles = ['user', 'assistant', 'system']

        for role in roles:
            message = AnalysisMessage.objects.create(
                session=self.session,
                role=role,
                content=f'Test {role} message'
            )
            self.assertEqual(message.role, role)

    def test_message_str_representation(self):
        """메시지 문자열 표현 테스트"""
        message = AnalysisMessage.objects.create(
            session=self.session,
            role='user',
            content='This is a very long message that should be truncated to 50 characters maximum'
        )

        str_repr = str(message)
        self.assertIn('사용자:', str_repr)
        self.assertTrue(len(str_repr) < 100)  # 50자 + 메타데이터
        self.assertIn('...', str_repr)  # 잘림 표시

    def test_message_ordering(self):
        """메시지 정렬 테스트 (생성 순서)"""
        msg1 = AnalysisMessage.objects.create(
            session=self.session,
            role='user',
            content='First message'
        )
        msg2 = AnalysisMessage.objects.create(
            session=self.session,
            role='assistant',
            content='Second message'
        )

        messages = self.session.messages.all()
        self.assertEqual(messages[0], msg1)  # 먼저 생성된 것이 먼저
        self.assertEqual(messages[1], msg2)

    def test_message_token_tracking(self):
        """토큰 사용량 추적 테스트"""
        message = AnalysisMessage.objects.create(
            session=self.session,
            role='assistant',
            content='Analysis result',
            input_tokens=500,
            output_tokens=1200
        )

        self.assertEqual(message.input_tokens, 500)
        self.assertEqual(message.output_tokens, 1200)

        # 총 토큰 계산
        total_tokens = message.input_tokens + message.output_tokens
        self.assertEqual(total_tokens, 1700)

    def test_message_default_suggestions(self):
        """suggestions 기본값 테스트"""
        message = AnalysisMessage.objects.create(
            session=self.session,
            role='user',
            content='Test'
        )
        self.assertEqual(message.suggestions, [])

    def test_session_cascade_delete(self):
        """세션 삭제 시 메시지도 삭제 테스트"""
        AnalysisMessage.objects.create(
            session=self.session,
            role='user',
            content='Test message'
        )

        message_count_before = AnalysisMessage.objects.count()
        self.assertEqual(message_count_before, 1)

        # 세션 삭제
        self.session.delete()

        # 메시지도 함께 삭제되어야 함
        message_count_after = AnalysisMessage.objects.count()
        self.assertEqual(message_count_after, 0)


class ModelIntegrationTest(TestCase):
    """모델 간 통합 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_complete_analysis_flow(self):
        """전체 분석 흐름 통합 테스트"""
        # 1. 바구니 생성
        basket = DataBasket.objects.create(
            user=self.user,
            name='Tech Analysis'
        )

        # 2. 바구니에 아이템 추가
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={'price': 150.00}
        )
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='GOOGL',
            title='Alphabet Inc.',
            data_snapshot={'price': 140.00}
        )

        # 3. 분석 세션 생성
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=basket,
            title='Tech Stock Analysis'
        )

        # 4. 사용자 질문 메시지
        user_msg = AnalysisMessage.objects.create(
            session=session,
            role='user',
            content='Compare AAPL and GOOGL'
        )

        # 5. 탐험 경로 추가
        session.add_exploration('stock', 'AAPL', 'User selected')
        session.add_exploration('stock', 'GOOGL', 'User selected')

        # 6. 어시스턴트 응답 메시지
        assistant_msg = AnalysisMessage.objects.create(
            session=session,
            role='assistant',
            content='Both are strong tech companies...',
            suggestions=[
                {'symbol': 'MSFT', 'reason': 'Similar market cap'},
                {'symbol': 'AMZN', 'reason': 'Cloud competitor'}
            ],
            input_tokens=200,
            output_tokens=400
        )

        # 7. 세션 완료
        session.status = 'completed'
        session.save()

        # 검증
        basket.refresh_from_db()
        session.refresh_from_db()

        self.assertEqual(basket.items_count, 2)
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(len(session.exploration_path), 2)
        self.assertEqual(session.status, 'completed')

        # 메시지 순서 확인
        messages = list(session.messages.all())
        self.assertEqual(messages[0].role, 'user')
        self.assertEqual(messages[1].role, 'assistant')

    def test_user_deletion_cascade(self):
        """사용자 삭제 시 연관 데이터 삭제 테스트"""
        # 데이터 생성
        basket = DataBasket.objects.create(user=self.user, name='Test')
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple',
            data_snapshot={}
        )
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=basket
        )
        AnalysisMessage.objects.create(
            session=session,
            role='user',
            content='Test'
        )

        # 사용자 삭제
        self.user.delete()

        # 모든 연관 데이터가 삭제되어야 함
        self.assertEqual(DataBasket.objects.count(), 0)
        self.assertEqual(BasketItem.objects.count(), 0)
        self.assertEqual(AnalysisSession.objects.count(), 0)
        self.assertEqual(AnalysisMessage.objects.count(), 0)
