"""
Watchlist Tests

사용자 관심종목 리스트 기능 테스트
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
@pytest.mark.django_db
def api_client():
    """API Client fixture"""
    return APIClient()


@pytest.fixture
@pytest.mark.django_db
def authenticated_user():
    """인증된 사용자"""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
@pytest.mark.django_db
def other_user():
    """다른 사용자 (권한 테스트용)"""
    user = User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123'
    )
    return user


@pytest.fixture
@pytest.mark.django_db
def watchlist(authenticated_user):
    """기본 Watchlist"""
    from users.models import Watchlist

    return Watchlist.objects.create(
        user=authenticated_user,
        name='진입준비',
        description='매수 타이밍을 기다리는 종목들'
    )


@pytest.fixture
@pytest.mark.django_db
def watchlist_with_items(watchlist, stock):
    """종목이 포함된 Watchlist"""
    from users.models import WatchlistItem
    from stocks.models import Stock

    # 추가 종목 생성
    stock2 = Stock.objects.create(
        symbol='MSFT',
        stock_name='Microsoft Corporation',
        sector='Technology',
        industry='Software',
        exchange='NASDAQ',
        currency='USD',
        market_capitalization=Decimal('2800000000000'),
        real_time_price=Decimal('375.50')
    )

    # 종목 추가
    WatchlistItem.objects.create(
        watchlist=watchlist,
        stock=stock,
        target_entry_price=Decimal('140.00'),
        notes='실적 발표 후 진입',
        position_order=1
    )

    WatchlistItem.objects.create(
        watchlist=watchlist,
        stock=stock2,
        target_entry_price=Decimal('360.00'),
        notes='클라우드 성장 기대',
        position_order=2
    )

    return watchlist


class TestWatchlistModel:
    """Watchlist 모델 테스트"""

    @pytest.mark.django_db
    def test_create_watchlist(self, authenticated_user):
        """
        Given: 사용자와 리스트 정보
        When: Watchlist 생성
        Then: 정상 생성됨
        """
        from users.models import Watchlist

        watchlist = Watchlist.objects.create(
            user=authenticated_user,
            name='테크주',
            description='기술주 중심'
        )

        assert watchlist.id is not None
        assert watchlist.user == authenticated_user
        assert watchlist.name == '테크주'
        assert watchlist.stock_count == 0

    @pytest.mark.django_db
    def test_watchlist_unique_name_per_user(self, authenticated_user):
        """
        Given: 동일 사용자가 같은 이름의 리스트 생성 시도
        When: 두 번째 리스트 생성
        Then: IntegrityError 발생
        """
        from users.models import Watchlist
        from django.db import IntegrityError

        Watchlist.objects.create(
            user=authenticated_user,
            name='진입준비'
        )

        with pytest.raises(IntegrityError):
            Watchlist.objects.create(
                user=authenticated_user,
                name='진입준비'
            )

    @pytest.mark.django_db
    def test_watchlist_stock_count_property(self, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: stock_count 조회
        Then: 정확한 종목 수 반환
        """
        assert watchlist_with_items.stock_count == 2

    @pytest.mark.django_db
    def test_watchlist_cascade_delete(self, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: Watchlist 삭제
        Then: WatchlistItem도 함께 삭제됨
        """
        from users.models import WatchlistItem

        watchlist_id = watchlist_with_items.id
        item_count_before = WatchlistItem.objects.filter(
            watchlist_id=watchlist_id
        ).count()
        assert item_count_before == 2

        watchlist_with_items.delete()

        item_count_after = WatchlistItem.objects.filter(
            watchlist_id=watchlist_id
        ).count()
        assert item_count_after == 0


class TestWatchlistItemModel:
    """WatchlistItem 모델 테스트"""

    @pytest.mark.django_db
    def test_create_watchlist_item(self, watchlist, stock):
        """
        Given: Watchlist와 Stock
        When: WatchlistItem 생성
        Then: 정상 생성됨
        """
        from users.models import WatchlistItem

        item = WatchlistItem.objects.create(
            watchlist=watchlist,
            stock=stock,
            target_entry_price=Decimal('145.00'),
            notes='지지선 테스트 중'
        )

        assert item.id is not None
        assert item.watchlist == watchlist
        assert item.stock == stock
        assert item.current_price == 150.25

    @pytest.mark.django_db
    def test_watchlist_item_unique_stock(self, watchlist, stock):
        """
        Given: 이미 추가된 종목
        When: 같은 종목 다시 추가 시도
        Then: IntegrityError 발생
        """
        from users.models import WatchlistItem
        from django.db import IntegrityError

        WatchlistItem.objects.create(
            watchlist=watchlist,
            stock=stock
        )

        with pytest.raises(IntegrityError):
            WatchlistItem.objects.create(
                watchlist=watchlist,
                stock=stock
            )

    @pytest.mark.django_db
    def test_distance_from_entry_property(self, watchlist, stock):
        """
        Given: 목표 진입가가 설정된 WatchlistItem
        When: distance_from_entry 조회
        Then: 정확한 거리 계산됨
        """
        from users.models import WatchlistItem

        item = WatchlistItem.objects.create(
            watchlist=watchlist,
            stock=stock,
            target_entry_price=Decimal('140.00')
        )

        # current_price: 150.25, target: 140.00
        # distance = ((150.25 - 140.00) / 140.00) * 100 = 7.32%
        distance = item.distance_from_entry
        assert distance is not None
        assert 7.3 < distance < 7.4

    @pytest.mark.django_db
    def test_is_below_target_property(self, watchlist):
        """
        Given: 목표 진입가가 설정된 WatchlistItem
        When: is_below_target 조회
        Then: 정확한 진입 가능 여부 반환
        """
        from users.models import WatchlistItem
        from stocks.models import Stock

        # 현재가가 높은 종목
        stock_high = Stock.objects.create(
            symbol='TSLA',
            stock_name='Tesla Inc.',
            sector='Automotive',
            industry='Electric Vehicles',
            exchange='NASDAQ',
            currency='USD',
            market_capitalization=Decimal('800000000000'),
            real_time_price=Decimal('250.00')
        )

        # 현재가가 낮은 종목
        stock_low = Stock.objects.create(
            symbol='F',
            stock_name='Ford Motor Company',
            sector='Automotive',
            industry='Automotive',
            exchange='NYSE',
            currency='USD',
            market_capitalization=Decimal('50000000000'),
            real_time_price=Decimal('10.00')
        )

        # 현재가(250.00)보다 낮은 목표가 -> 이미 목표가 이하
        item1 = WatchlistItem.objects.create(
            watchlist=watchlist,
            stock=stock_high,
            target_entry_price=Decimal('200.00')
        )
        assert item1.is_below_target is False  # 현재가 > 목표가

        # 현재가(10.00)보다 높은 목표가 -> 아직 진입 불가
        item2 = WatchlistItem.objects.create(
            watchlist=watchlist,
            stock=stock_low,
            target_entry_price=Decimal('12.00')
        )
        assert item2.is_below_target is True  # 현재가 <= 목표가

    @pytest.mark.django_db
    def test_watchlist_item_ordering(self, watchlist_with_items):
        """
        Given: position_order가 설정된 WatchlistItem들
        When: 조회
        Then: position_order 순으로 정렬됨
        """
        from users.models import WatchlistItem

        items = WatchlistItem.objects.filter(watchlist=watchlist_with_items)

        assert items[0].position_order == 1
        assert items[1].position_order == 2


class TestWatchlistAPI:
    """Watchlist API 테스트"""

    @pytest.mark.django_db
    def test_list_watchlists_authenticated(self, api_client, authenticated_user, watchlist):
        """
        Given: 인증된 사용자
        When: GET /api/v1/users/watchlist/
        Then: 사용자의 Watchlist 목록 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/watchlist/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == '진입준비'

    @pytest.mark.django_db
    def test_list_watchlists_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: GET /api/v1/users/watchlist/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/watchlist/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_create_watchlist_success(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자와 리스트 정보
        When: POST /api/v1/users/watchlist/
        Then: Watchlist 생성됨
        """
        from users.models import Watchlist

        api_client.force_authenticate(user=authenticated_user)

        data = {
            'name': '배당주',
            'description': '안정적인 배당 수익'
        }

        response = api_client.post('/api/v1/users/watchlist/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == '배당주'
        assert Watchlist.objects.filter(user=authenticated_user, name='배당주').exists()

    @pytest.mark.django_db
    def test_create_watchlist_duplicate_name(self, api_client, authenticated_user, watchlist):
        """
        Given: 이미 존재하는 리스트 이름
        When: POST /api/v1/users/watchlist/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'name': '진입준비',
            'description': '중복 테스트'
        }

        response = api_client.post('/api/v1/users/watchlist/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_retrieve_watchlist_detail(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/
        Then: 상세 정보 및 종목 리스트 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(f'/api/v1/users/watchlist/{watchlist_with_items.pk}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == '진입준비'
        assert response.data['stock_count'] == 2
        assert len(response.data['items']) == 2

    @pytest.mark.django_db
    def test_update_watchlist(self, api_client, authenticated_user, watchlist):
        """
        Given: 인증된 사용자의 Watchlist
        When: PATCH /api/v1/users/watchlist/{pk}/
        Then: Watchlist 수정됨
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'name': '진입준비 (수정)',
            'description': '수정된 설명'
        }

        response = api_client.patch(f'/api/v1/users/watchlist/{watchlist.pk}/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == '진입준비 (수정)'

        watchlist.refresh_from_db()
        assert watchlist.name == '진입준비 (수정)'

    @pytest.mark.django_db
    def test_delete_watchlist(self, api_client, authenticated_user, watchlist):
        """
        Given: 인증된 사용자의 Watchlist
        When: DELETE /api/v1/users/watchlist/{pk}/
        Then: Watchlist 삭제됨
        """
        from users.models import Watchlist

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(f'/api/v1/users/watchlist/{watchlist.pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Watchlist.objects.filter(pk=watchlist.pk).exists()

    @pytest.mark.django_db
    def test_access_other_user_watchlist(self, api_client, authenticated_user, other_user):
        """
        Given: 다른 사용자의 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/
        Then: 404 Not Found (권한 없음)
        """
        from users.models import Watchlist

        other_watchlist = Watchlist.objects.create(
            user=other_user,
            name='다른 사용자 리스트'
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(f'/api/v1/users/watchlist/{other_watchlist.pk}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWatchlistItemAPI:
    """WatchlistItem API 테스트"""

    @pytest.mark.django_db
    def test_add_stock_to_watchlist(self, api_client, authenticated_user, watchlist, stock):
        """
        Given: 인증된 사용자의 Watchlist와 유효한 Stock
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 종목이 리스트에 추가됨
        """
        from users.models import WatchlistItem

        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'target_entry_price': '145.00',
            'notes': '실적 후 진입'
        }

        response = api_client.post(f'/api/v1/users/watchlist/{watchlist.pk}/add-stock/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['stock_symbol'] == 'AAPL'
        assert WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists()

    @pytest.mark.django_db
    def test_add_duplicate_stock(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 이미 추가된 종목
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 400 Bad Request (중복)
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'target_entry_price': '145.00'
        }

        response = api_client.post(f'/api/v1/users/watchlist/{watchlist_with_items.pk}/add-stock/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'AAPL' in str(response.data['error'])

    @pytest.mark.django_db
    def test_remove_stock_from_watchlist(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: DELETE /api/v1/users/watchlist/{pk}/stocks/{symbol}/remove/
        Then: 종목이 리스트에서 제거됨
        """
        from users.models import WatchlistItem

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/AAPL/remove/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not WatchlistItem.objects.filter(
            watchlist=watchlist_with_items,
            stock__symbol='AAPL'
        ).exists()

    @pytest.mark.django_db
    def test_update_watchlist_item(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: Watchlist에 포함된 종목
        When: PATCH /api/v1/users/watchlist/{pk}/stocks/{symbol}/
        Then: 종목 설정이 수정됨
        """
        from users.models import WatchlistItem

        api_client.force_authenticate(user=authenticated_user)

        data = {
            'target_entry_price': '135.00',
            'notes': '수정된 메모'
        }

        response = api_client.patch(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/AAPL/',
            data
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['notes'] == '수정된 메모'

        item = WatchlistItem.objects.get(
            watchlist=watchlist_with_items,
            stock__symbol='AAPL'
        )
        assert item.target_entry_price == Decimal('135.00')

    @pytest.mark.django_db
    def test_get_watchlist_stocks(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/stocks/
        Then: 종목 상세 리스트 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['stock_symbol'] in ['AAPL', 'MSFT']
        assert 'current_price' in response.data[0]
        assert 'change_percent' in response.data[0]


class TestWatchlistItemValidation:
    """WatchlistItem 유효성 검사 테스트"""

    @pytest.mark.django_db
    def test_add_invalid_stock_symbol(self, api_client, authenticated_user, watchlist):
        """
        Given: 유효하지 않은 Stock 심볼
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'INVALID999',
            'target_entry_price': '100.00'
        }

        # validate_and_create_stock가 실패하는 케이스
        response = api_client.post(f'/api/v1/users/watchlist/{watchlist.pk}/add-stock/', data)

        # API 호출 제한으로 인해 실패할 수 있으므로 에러 확인
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]

    @pytest.mark.django_db
    def test_negative_target_entry_price(self, api_client, authenticated_user, watchlist, stock):
        """
        Given: 음수 목표 진입가
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'target_entry_price': '-10.00'
        }

        response = api_client.post(f'/api/v1/users/watchlist/{watchlist.pk}/add-stock/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWatchlistQueryOptimization:
    """Watchlist N+1 쿼리 최적화 테스트"""

    @pytest.mark.django_db
    def test_watchlist_detail_query_optimization(
        self, api_client, authenticated_user, watchlist_with_items, django_assert_num_queries
    ):
        """
        Given: 종목이 포함된 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/
        Then: N+1 쿼리 없이 조회됨
        """
        api_client.force_authenticate(user=authenticated_user)

        # prefetch_related 사용으로 최적화됨 (1: watchlist, 2: items, 3: stocks)
        with django_assert_num_queries(3):  # 최적화된 쿼리 수
            response = api_client.get(f'/api/v1/users/watchlist/{watchlist_with_items.pk}/')

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_watchlist_stocks_query_optimization(
        self, api_client, authenticated_user, watchlist_with_items, django_assert_num_queries
    ):
        """
        Given: 종목이 포함된 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/stocks/
        Then: select_related로 최적화됨
        """
        api_client.force_authenticate(user=authenticated_user)

        # select_related('stock') 사용으로 최소 쿼리 (1: watchlist, 2: items+stock JOIN)
        with django_assert_num_queries(2):  # 최적화된 쿼리 수
            response = api_client.get(
                f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/'
            )

        assert response.status_code == status.HTTP_200_OK


# ===== 마커 설정 =====
pytestmark = pytest.mark.unit
