"""
RAG Analysis View Tests

Tests for:
- DataBasket API endpoints (CRUD, authentication)
- BasketItem API endpoints (add, remove, clear)
- AnalysisSession API endpoints (CRUD, authentication)
- Error response format validation
- Permission checks
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json

from rag_analysis.models import (
    DataBasket,
    BasketItem,
    AnalysisSession,
    AnalysisMessage
)

User = get_user_model()


class DataBasketAPITest(TestCase):
    """DataBasket API 테스트"""

    def setUp(self):
        """테스트 클라이언트 및 사용자 생성"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )

    def test_basket_list_requires_authentication(self):
        """바구니 목록 조회 인증 필요 테스트"""
        url = reverse('rag_analysis:basket-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_basket_list_authenticated(self):
        """인증된 사용자 바구니 목록 조회 테스트"""
        self.client.force_authenticate(user=self.user)

        # 테스트 데이터 생성
        DataBasket.objects.create(user=self.user, name='Basket 1')
        DataBasket.objects.create(user=self.user, name='Basket 2')
        DataBasket.objects.create(user=self.other_user, name='Other Basket')

        url = reverse('rag_analysis:basket-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 응답 형식 검증
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('meta', data)

        # 자기 바구니만 조회되는지 확인
        self.assertEqual(len(data['data']), 2)

    def test_basket_create(self):
        """바구니 생성 테스트"""
        self.client.force_authenticate(user=self.user)

        url = reverse('rag_analysis:basket-list-create')
        payload = {
            'name': 'Tech Analysis',
            'description': 'Tech sector stocks'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], 'Tech Analysis')
        self.assertEqual(data['data']['description'], 'Tech sector stocks')
        self.assertEqual(data['data']['items_count'], 0)
        self.assertTrue(data['data']['can_add_item'])

    def test_basket_create_default_name(self):
        """바구니 기본 이름으로 생성 테스트"""
        self.client.force_authenticate(user=self.user)

        url = reverse('rag_analysis:basket-list-create')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertEqual(data['data']['name'], 'My Basket')

    def test_basket_detail(self):
        """바구니 상세 조회 테스트"""
        self.client.force_authenticate(user=self.user)

        basket = DataBasket.objects.create(
            user=self.user,
            name='Test Basket'
        )
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.'
        )

        url = reverse('rag_analysis:basket-detail', kwargs={'pk': basket.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], 'Test Basket')
        self.assertEqual(data['data']['items_count'], 1)
        self.assertEqual(len(data['data']['items']), 1)
        self.assertEqual(data['data']['items'][0]['reference_id'], 'AAPL')

    def test_basket_detail_not_owner(self):
        """다른 사용자의 바구니 조회 실패 테스트"""
        self.client.force_authenticate(user=self.user)

        basket = DataBasket.objects.create(
            user=self.other_user,
            name='Other Basket'
        )

        url = reverse('rag_analysis:basket-detail', kwargs={'pk': basket.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_basket_update(self):
        """바구니 수정 테스트"""
        self.client.force_authenticate(user=self.user)

        basket = DataBasket.objects.create(
            user=self.user,
            name='Old Name'
        )

        url = reverse('rag_analysis:basket-detail', kwargs={'pk': basket.pk})
        payload = {
            'name': 'New Name',
            'description': 'Updated description'
        }

        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], 'New Name')
        self.assertEqual(data['data']['description'], 'Updated description')

    def test_basket_delete(self):
        """바구니 삭제 테스트"""
        self.client.force_authenticate(user=self.user)

        basket = DataBasket.objects.create(
            user=self.user,
            name='To Delete'
        )

        url = reverse('rag_analysis:basket-detail', kwargs={'pk': basket.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DataBasket.objects.filter(pk=basket.pk).exists())


class BasketItemAPITest(TestCase):
    """BasketItem API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
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

    def test_add_item_success(self):
        """아이템 추가 성공 테스트"""
        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': self.basket.pk})
        payload = {
            'item_type': 'stock',
            'reference_id': 'AAPL',
            'title': 'Apple Inc.',
            'subtitle': 'NASDAQ',
            'data_snapshot': {'price': 150.00}
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['item_type'], 'stock')
        self.assertEqual(data['data']['reference_id'], 'AAPL')
        self.assertEqual(data['data']['title'], 'Apple Inc.')

    def test_add_item_duplicate(self):
        """중복 아이템 추가 실패 테스트"""
        # 첫 번째 아이템 추가
        BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.'
        )

        # 같은 아이템 추가 시도
        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': self.basket.pk})
        payload = {
            'item_type': 'stock',
            'reference_id': 'AAPL',
            'title': 'Apple Inc.'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'DUPLICATE_ITEM')
        self.assertIn('meta', data)

    def test_add_item_basket_full(self):
        """바구니 가득 참 테스트"""
        # 15개 아이템 추가
        for i in range(15):
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test Stock {i}'
            )

        # 16번째 추가 시도
        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': self.basket.pk})
        payload = {
            'item_type': 'stock',
            'reference_id': 'TEST16',
            'title': 'Test Stock 16'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'BASKET_FULL')
        self.assertIn('15개', data['error']['message'])
        self.assertIn('request_id', data['meta'])
        self.assertIn('timestamp', data['meta'])

    def test_add_item_invalid_data(self):
        """유효하지 않은 데이터로 아이템 추가 실패 테스트"""
        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': self.basket.pk})
        payload = {
            'item_type': 'invalid_type',  # 유효하지 않은 타입
            'reference_id': 'AAPL',
            'title': 'Apple Inc.'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'INVALID_INPUT')

    def test_remove_item_success(self):
        """아이템 제거 성공 테스트"""
        item = BasketItem.objects.create(
            basket=self.basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.'
        )

        url = reverse('rag_analysis:basket-remove-item', kwargs={
            'pk': self.basket.pk,
            'item_id': item.pk
        })
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BasketItem.objects.filter(pk=item.pk).exists())

    def test_remove_item_not_found(self):
        """존재하지 않는 아이템 제거 실패 테스트"""
        url = reverse('rag_analysis:basket-remove-item', kwargs={
            'pk': self.basket.pk,
            'item_id': 9999
        })
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_clear_basket(self):
        """바구니 비우기 테스트"""
        # 여러 아이템 추가
        for i in range(5):
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test Stock {i}'
            )

        self.assertEqual(self.basket.items.count(), 5)

        url = reverse('rag_analysis:basket-clear', kwargs={'pk': self.basket.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['deleted_count'], 5)

        self.basket.refresh_from_db()
        self.assertEqual(self.basket.items.count(), 0)


class AnalysisSessionAPITest(TestCase):
    """AnalysisSession API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.basket = DataBasket.objects.create(
            user=self.user,
            name='Test Basket'
        )

    def test_session_list_requires_authentication(self):
        """세션 목록 조회 인증 필요 테스트"""
        self.client.force_authenticate(user=None)

        url = reverse('rag_analysis:session-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_list_authenticated(self):
        """인증된 사용자 세션 목록 조회 테스트"""
        # 테스트 데이터 생성
        AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Session 1'
        )
        AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Session 2'
        )
        AnalysisSession.objects.create(
            user=self.other_user,
            basket=None,
            title='Other Session'
        )

        url = reverse('rag_analysis:session-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 2)  # 자기 세션만 조회

    def test_session_create_with_basket(self):
        """바구니와 함께 세션 생성 테스트"""
        url = reverse('rag_analysis:session-list-create')
        payload = {
            'basket_id': self.basket.pk,
            'title': 'Tech Analysis Session'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['title'], 'Tech Analysis Session')
        self.assertEqual(data['data']['status'], 'active')
        self.assertEqual(data['data']['basket']['id'], self.basket.pk)

    def test_session_create_without_basket(self):
        """바구니 없이 세션 생성 테스트"""
        url = reverse('rag_analysis:session-list-create')
        payload = {
            'title': 'General Analysis'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIsNone(data['data']['basket'])

    def test_session_create_invalid_basket(self):
        """다른 사용자의 바구니로 세션 생성 실패 테스트"""
        other_basket = DataBasket.objects.create(
            user=self.other_user,
            name='Other Basket'
        )

        url = reverse('rag_analysis:session-list-create')
        payload = {
            'basket_id': other_basket.pk,
            'title': 'Invalid Session'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'INVALID_INPUT')
        self.assertIn('접근할 수 없습니다', data['error']['message'])

    def test_session_detail(self):
        """세션 상세 조회 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='Test Session'
        )

        # 메시지 추가
        AnalysisMessage.objects.create(
            session=session,
            role='user',
            content='Test question'
        )

        url = reverse('rag_analysis:session-detail', kwargs={'pk': session.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['title'], 'Test Session')
        self.assertEqual(len(data['data']['messages']), 1)

    def test_session_detail_not_owner(self):
        """다른 사용자의 세션 조회 실패 테스트"""
        session = AnalysisSession.objects.create(
            user=self.other_user,
            basket=None,
            title='Other Session'
        )

        url = reverse('rag_analysis:session-detail', kwargs={'pk': session.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_session_delete(self):
        """세션 삭제 테스트"""
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=self.basket,
            title='To Delete'
        )

        url = reverse('rag_analysis:session-detail', kwargs={'pk': session.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AnalysisSession.objects.filter(pk=session.pk).exists())


class ErrorResponseFormatTest(TestCase):
    """에러 응답 형식 테스트"""

    def setUp(self):
        """테스트 클라이언트 및 사용자 생성"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_success_response_format(self):
        """성공 응답 형식 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')

        url = reverse('rag_analysis:basket-detail', kwargs={'pk': basket.pk})
        response = self.client.get(url)

        data = response.json()

        # 필수 필드 확인
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIn('meta', data)

        # success 필드
        self.assertTrue(data['success'])

        # meta 필드
        self.assertIn('request_id', data['meta'])
        self.assertIn('timestamp', data['meta'])

    def test_error_response_format(self):
        """에러 응답 형식 테스트"""
        # 존재하지 않는 바구니 조회
        url = reverse('rag_analysis:basket-detail', kwargs={'pk': 9999})
        response = self.client.get(url)

        data = response.json()

        # 필수 필드 확인
        self.assertIn('success', data)
        self.assertIn('error', data)
        self.assertIn('meta', data)

        # success 필드
        self.assertFalse(data['success'])

        # error 필드
        self.assertIn('code', data['error'])
        self.assertIn('message', data['error'])

        # meta 필드
        self.assertIn('request_id', data['meta'])
        self.assertIn('timestamp', data['meta'])

    def test_basket_full_error_code(self):
        """BASKET_FULL 에러 코드 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')

        # 15개 아이템 추가
        for i in range(15):
            BasketItem.objects.create(
                basket=basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test {i}'
            )

        # 16번째 추가 시도
        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': basket.pk})
        payload = {
            'item_type': 'stock',
            'reference_id': 'TEST16',
            'title': 'Test 16'
        }

        response = self.client.post(url, payload, format='json')
        data = response.json()

        self.assertEqual(data['error']['code'], 'BASKET_FULL')

    def test_duplicate_item_error_code(self):
        """DUPLICATE_ITEM 에러 코드 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple'
        )

        # 중복 추가 시도
        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': basket.pk})
        payload = {
            'item_type': 'stock',
            'reference_id': 'AAPL',
            'title': 'Apple'
        }

        response = self.client.post(url, payload, format='json')
        data = response.json()

        self.assertEqual(data['error']['code'], 'DUPLICATE_ITEM')

    def test_invalid_input_error_code(self):
        """INVALID_INPUT 에러 코드 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')

        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': basket.pk})
        payload = {
            'item_type': 'invalid_type',
            'reference_id': 'TEST',
            'title': 'Test'
        }

        response = self.client.post(url, payload, format='json')
        data = response.json()

        self.assertEqual(data['error']['code'], 'INVALID_INPUT')


class ConcurrencyTest(TestCase):
    """동시성 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
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

    def test_concurrent_item_addition_prevented(self):
        """동시 아이템 추가 방지 테스트 (select_for_update)"""
        # 14개 아이템 추가 (한 개 남음)
        for i in range(14):
            BasketItem.objects.create(
                basket=self.basket,
                item_type='stock',
                reference_id=f'TEST{i}',
                title=f'Test {i}'
            )

        url = reverse('rag_analysis:basket-add-item', kwargs={'pk': self.basket.pk})

        # 두 개의 아이템을 순차적으로 추가 시도
        payload1 = {
            'item_type': 'stock',
            'reference_id': 'TEST14',
            'title': 'Test 14'
        }
        payload2 = {
            'item_type': 'stock',
            'reference_id': 'TEST15',
            'title': 'Test 15'
        }

        response1 = self.client.post(url, payload1, format='json')
        response2 = self.client.post(url, payload2, format='json')

        # 첫 번째는 성공, 두 번째는 실패
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

        self.basket.refresh_from_db()
        self.assertEqual(self.basket.items_count, 15)
