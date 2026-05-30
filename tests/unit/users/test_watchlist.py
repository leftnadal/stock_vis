"""
Watchlist API 테스트 (users 앱)

users/views.py 의 Watchlist 관련 엔드포인트 단위 테스트
- WatchlistListCreateView
- WatchlistDetailView
- WatchlistItemAddView
- WatchlistItemRemoveView
- WatchlistItemUpdateView
- WatchlistStocksView
- WatchlistBulkAddView / WatchlistBulkRemoveView
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from packages.shared.users.models import Watchlist, WatchlistItem

User = get_user_model()

pytestmark = pytest.mark.unit


@pytest.fixture
@pytest.mark.django_db
def watchlist(authenticated_user):
    """기본 Watchlist fixture"""
    return Watchlist.objects.create(
        user=authenticated_user,
        name='진입준비',
        description='매수 타이밍을 기다리는 종목들',
    )


@pytest.fixture
@pytest.mark.django_db
def watchlist_with_items(watchlist, stock_aapl, stock_msft):
    """종목이 포함된 Watchlist fixture"""
    WatchlistItem.objects.create(
        watchlist=watchlist,
        stock=stock_aapl,
        target_entry_price=Decimal('140.00'),
        notes='실적 발표 후 진입',
        position_order=1,
    )
    WatchlistItem.objects.create(
        watchlist=watchlist,
        stock=stock_msft,
        target_entry_price=Decimal('360.00'),
        notes='클라우드 성장 기대',
        position_order=2,
    )
    return watchlist


class TestWatchlistList:
    """Watchlist 목록 조회/생성 테스트"""

    @pytest.mark.django_db
    def test_list_watchlists_authenticated(self, api_client, authenticated_user, watchlist):
        """
        Given: 인증된 사용자와 1개의 Watchlist
        When: GET /api/v1/users/watchlist/
        Then: 200 OK + 페이지네이션 응답에 Watchlist 1개 포함
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/watchlist/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'pagination' in response.data
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == '진입준비'

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
    def test_list_watchlists_empty(self, api_client, authenticated_user):
        """
        Given: Watchlist가 없는 인증 사용자
        When: GET /api/v1/users/watchlist/
        Then: 200 OK + 빈 results 리스트
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/watchlist/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []
        assert response.data['pagination']['count'] == 0

    @pytest.mark.django_db
    def test_list_watchlists_only_own(self, api_client, authenticated_user, other_user):
        """
        Given: 다른 사용자의 Watchlist 존재
        When: GET /api/v1/users/watchlist/
        Then: 자신의 Watchlist만 반환 (다른 사용자 데이터 격리)
        """
        Watchlist.objects.create(user=other_user, name='다른 유저 리스트')
        Watchlist.objects.create(user=authenticated_user, name='내 리스트')

        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/v1/users/watchlist/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == '내 리스트'


class TestWatchlistCreate:
    """Watchlist 생성 테스트"""

    @pytest.mark.django_db
    def test_create_watchlist_success(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자와 유효한 데이터
        When: POST /api/v1/users/watchlist/
        Then: 201 Created + DB에 저장됨
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'name': '배당주', 'description': '안정적인 배당 수익'}
        response = api_client.post('/api/v1/users/watchlist/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == '배당주'
        assert Watchlist.objects.filter(
            user=authenticated_user, name='배당주'
        ).exists()

    @pytest.mark.django_db
    def test_create_watchlist_duplicate_name(self, api_client, authenticated_user, watchlist):
        """
        Given: 동일한 이름의 Watchlist가 이미 존재
        When: POST /api/v1/users/watchlist/
        Then: 400 Bad Request (이름 중복)
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'name': '진입준비', 'description': '중복 시도'}
        response = api_client.post('/api/v1/users/watchlist/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_watchlist_empty_name(self, api_client, authenticated_user):
        """
        Given: 공백만 포함된 이름
        When: POST /api/v1/users/watchlist/
        Then: 400 Bad Request (시리얼라이저 유효성 실패)
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'name': '   ', 'description': ''}
        response = api_client.post('/api/v1/users/watchlist/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWatchlistDetail:
    """Watchlist 상세/수정/삭제 테스트"""

    @pytest.mark.django_db
    def test_retrieve_watchlist_detail(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 종목 2개가 포함된 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/
        Then: 200 OK + items 배열 포함
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == '진입준비'
        assert response.data['stock_count'] == 2
        assert len(response.data['items']) == 2

    @pytest.mark.django_db
    def test_update_watchlist(self, api_client, authenticated_user, watchlist):
        """
        Given: 인증된 사용자의 Watchlist
        When: PATCH /api/v1/users/watchlist/{pk}/
        Then: 200 OK + DB 값 갱신
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'name': '진입준비 (수정)', 'description': '수정된 설명'}
        response = api_client.patch(
            f'/api/v1/users/watchlist/{watchlist.pk}/', data
        )

        assert response.status_code == status.HTTP_200_OK
        watchlist.refresh_from_db()
        assert watchlist.name == '진입준비 (수정)'
        assert watchlist.description == '수정된 설명'

    @pytest.mark.django_db
    def test_delete_watchlist(self, api_client, authenticated_user, watchlist):
        """
        Given: 인증된 사용자의 Watchlist
        When: DELETE /api/v1/users/watchlist/{pk}/
        Then: 204 No Content + DB에서 제거
        """
        api_client.force_authenticate(user=authenticated_user)
        pk = watchlist.pk

        response = api_client.delete(f'/api/v1/users/watchlist/{pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Watchlist.objects.filter(pk=pk).exists()

    @pytest.mark.django_db
    def test_access_other_user_watchlist(self, api_client, authenticated_user, other_user):
        """
        Given: 다른 사용자의 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/
        Then: 404 Not Found (소유자 검사)
        """
        other_wl = Watchlist.objects.create(user=other_user, name='남의 리스트')

        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get(f'/api/v1/users/watchlist/{other_wl.pk}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_delete_other_user_watchlist(self, api_client, authenticated_user, other_user):
        """
        Given: 다른 사용자의 Watchlist
        When: DELETE /api/v1/users/watchlist/{pk}/
        Then: 404 + 원본 데이터 보존
        """
        other_wl = Watchlist.objects.create(user=other_user, name='남의 리스트')

        api_client.force_authenticate(user=authenticated_user)
        response = api_client.delete(f'/api/v1/users/watchlist/{other_wl.pk}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Watchlist.objects.filter(pk=other_wl.pk).exists()


class TestWatchlistItemAdd:
    """Watchlist 종목 추가 테스트"""

    @pytest.mark.django_db
    def test_add_stock_success(self, api_client, authenticated_user, watchlist, stock_aapl):
        """
        Given: 인증 사용자와 빈 Watchlist
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 201 Created + WatchlistItem 생성
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'target_entry_price': '145.00',
            'notes': '실적 후 진입',
        }
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist.pk}/add-stock/', data
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['stock_symbol'] == 'AAPL'
        assert WatchlistItem.objects.filter(
            watchlist=watchlist, stock=stock_aapl
        ).exists()

    @pytest.mark.django_db
    def test_add_stock_duplicate(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 이미 추가된 종목 (AAPL)
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 400 Bad Request + 에러 메시지에 심볼 포함
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'stock': 'AAPL', 'target_entry_price': '145.00'}
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/add-stock/',
            data,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'AAPL' in str(response.data.get('error', ''))

    @pytest.mark.django_db
    def test_add_stock_negative_price(self, api_client, authenticated_user, watchlist, stock_aapl):
        """
        Given: 음수 목표가
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 400 Bad Request (시리얼라이저 검증 실패)
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'stock': 'AAPL', 'target_entry_price': '-10.00'}
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist.pk}/add-stock/', data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_add_stock_to_other_user_watchlist(
        self, api_client, authenticated_user, other_user, stock_aapl
    ):
        """
        Given: 다른 사용자의 Watchlist
        When: POST /api/v1/users/watchlist/{pk}/add-stock/
        Then: 404 Not Found
        """
        other_wl = Watchlist.objects.create(user=other_user, name='남의 리스트')

        api_client.force_authenticate(user=authenticated_user)
        data = {'stock': 'AAPL'}
        response = api_client.post(
            f'/api/v1/users/watchlist/{other_wl.pk}/add-stock/', data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWatchlistItemRemove:
    """Watchlist 종목 제거 테스트"""

    @pytest.mark.django_db
    def test_remove_stock_success(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: DELETE /api/v1/users/watchlist/{pk}/stocks/{symbol}/remove/
        Then: 204 No Content + 해당 항목 제거
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/AAPL/remove/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not WatchlistItem.objects.filter(
            watchlist=watchlist_with_items, stock__symbol='AAPL'
        ).exists()

    @pytest.mark.django_db
    def test_remove_stock_lowercase_symbol(
        self, api_client, authenticated_user, watchlist_with_items
    ):
        """
        Given: 소문자 심볼로 제거 요청
        When: DELETE /api/v1/users/watchlist/{pk}/stocks/aapl/remove/
        Then: 204 No Content (symbol.upper() 처리)
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/aapl/remove/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_remove_nonexistent_stock(self, api_client, authenticated_user, watchlist):
        """
        Given: Watchlist에 없는 심볼
        When: DELETE /api/v1/users/watchlist/{pk}/stocks/NVDA/remove/
        Then: 404 Not Found
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(
            f'/api/v1/users/watchlist/{watchlist.pk}/stocks/NVDA/remove/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWatchlistItemUpdate:
    """Watchlist 종목 수정 테스트"""

    @pytest.mark.django_db
    def test_update_item_success(self, api_client, authenticated_user, watchlist_with_items):
        """
        Given: Watchlist에 포함된 AAPL 종목
        When: PATCH /api/v1/users/watchlist/{pk}/stocks/AAPL/
        Then: 200 OK + 목표가/메모 갱신
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'target_entry_price': '135.00', 'notes': '수정된 메모'}
        response = api_client.patch(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/AAPL/',
            data,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['notes'] == '수정된 메모'

        item = WatchlistItem.objects.get(
            watchlist=watchlist_with_items, stock__symbol='AAPL'
        )
        assert item.target_entry_price == Decimal('135.0000')

    @pytest.mark.django_db
    def test_update_item_negative_price(
        self, api_client, authenticated_user, watchlist_with_items
    ):
        """
        Given: 음수 목표가로 수정 시도
        When: PATCH /api/v1/users/watchlist/{pk}/stocks/AAPL/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'target_entry_price': '-100.00'}
        response = api_client.patch(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/AAPL/',
            data,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWatchlistStocksView:
    """WatchlistStocksView (실시간 가격 포함 종목 조회) 테스트"""

    @pytest.mark.django_db
    def test_get_stocks_with_pagination(
        self, api_client, authenticated_user, watchlist_with_items
    ):
        """
        Given: 종목 2개가 포함된 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/stocks/
        Then: 200 OK + 페이지네이션 + 실시간 가격 포함
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/stocks/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'pagination' in response.data
        assert len(response.data['results']) == 2
        assert 'current_price' in response.data['results'][0]

    @pytest.mark.django_db
    def test_get_stocks_other_user(self, api_client, authenticated_user, other_user):
        """
        Given: 다른 사용자의 Watchlist
        When: GET /api/v1/users/watchlist/{pk}/stocks/
        Then: 404 Not Found
        """
        other_wl = Watchlist.objects.create(user=other_user, name='남의 리스트')

        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get(
            f'/api/v1/users/watchlist/{other_wl.pk}/stocks/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWatchlistBulkOperations:
    """Bulk 추가/제거 테스트"""

    @pytest.mark.django_db
    def test_bulk_add_success(
        self, api_client, authenticated_user, watchlist, stock_aapl, stock_msft
    ):
        """
        Given: 빈 Watchlist + 2개 심볼
        When: POST /api/v1/users/watchlist/{pk}/bulk-add/
        Then: 201 Created + 두 종목 모두 추가
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'symbols': ['AAPL', 'MSFT'], 'target_entry_price': '100.00'}
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist.pk}/bulk-add/',
            data,
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['summary']['added_count'] == 2
        assert WatchlistItem.objects.filter(watchlist=watchlist).count() == 2

    @pytest.mark.django_db
    def test_bulk_add_with_duplicate(
        self, api_client, authenticated_user, watchlist_with_items, stock_aapl
    ):
        """
        Given: 이미 AAPL이 포함된 Watchlist
        When: POST bulk-add with [AAPL, NVDA(없는 종목)]
        Then: 200 OK + skipped/errors 분리 보고
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'symbols': ['AAPL', 'NVDA']}
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/bulk-add/',
            data,
            format='json',
        )

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
        )
        assert 'AAPL' in response.data['skipped']
        # NVDA는 Stock에 없으므로 errors에 들어감
        assert any(e['symbol'] == 'NVDA' for e in response.data['errors'])

    @pytest.mark.django_db
    def test_bulk_add_invalid_payload(self, api_client, authenticated_user, watchlist):
        """
        Given: symbols 필드가 리스트가 아님
        When: POST bulk-add
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'symbols': 'AAPL'}  # 문자열 (리스트 아님)
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist.pk}/bulk-add/', data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_bulk_remove_success(
        self, api_client, authenticated_user, watchlist_with_items
    ):
        """
        Given: AAPL, MSFT가 포함된 Watchlist
        When: POST /api/v1/users/watchlist/{pk}/bulk-remove/
        Then: 200 OK + 두 종목 모두 제거
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'symbols': ['AAPL', 'MSFT']}
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/bulk-remove/',
            data,
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['removed_count'] == 2
        assert WatchlistItem.objects.filter(
            watchlist=watchlist_with_items
        ).count() == 0

    @pytest.mark.django_db
    def test_bulk_remove_partial(
        self, api_client, authenticated_user, watchlist_with_items
    ):
        """
        Given: AAPL만 포함된 Watchlist
        When: POST bulk-remove with [AAPL, NOTEXIST]
        Then: removed에 AAPL, not_found에 NOTEXIST
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'symbols': ['AAPL', 'NOTEXIST']}
        response = api_client.post(
            f'/api/v1/users/watchlist/{watchlist_with_items.pk}/bulk-remove/',
            data,
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'AAPL' in response.data['removed']
        assert 'NOTEXIST' in response.data['not_found']


class TestWatchlistModel:
    """Watchlist 모델 프로퍼티/제약 테스트"""

    @pytest.mark.django_db
    def test_stock_count_property(self, watchlist_with_items):
        """
        Given: 종목 2개가 포함된 Watchlist
        When: stock_count 접근
        Then: 2 반환
        """
        assert watchlist_with_items.stock_count == 2

    @pytest.mark.django_db
    def test_cascade_delete_items(self, watchlist_with_items):
        """
        Given: 종목이 포함된 Watchlist
        When: Watchlist 삭제
        Then: 관련 WatchlistItem도 함께 삭제 (CASCADE)
        """
        wl_id = watchlist_with_items.id
        assert WatchlistItem.objects.filter(watchlist_id=wl_id).count() == 2

        watchlist_with_items.delete()

        assert WatchlistItem.objects.filter(watchlist_id=wl_id).count() == 0

    @pytest.mark.django_db
    def test_unique_name_per_user(self, authenticated_user, other_user):
        """
        Given: 동일 사용자가 같은 이름의 Watchlist를 두 번 생성 시도
        When: 두 번째 생성
        Then: IntegrityError 발생 (unique_together)
        다른 사용자는 동일 이름 사용 가능
        """
        from django.db import IntegrityError, transaction

        Watchlist.objects.create(user=authenticated_user, name='관심')

        # 다른 유저는 같은 이름 사용 가능
        Watchlist.objects.create(user=other_user, name='관심')

        # 동일 유저가 같은 이름 재사용 → 에러
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Watchlist.objects.create(user=authenticated_user, name='관심')
