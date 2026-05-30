"""
Users 앱 추가 View 테스트

기존 test_jwt_auth/test_portfolio/test_serializers/test_watchlist 에서 다루지 않은
세션 기반 인증 + Favorites + 포트폴리오 부가 뷰 + UserInterest 보강 테스트
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from packages.shared.stocks.models import Stock
from packages.shared.users.models import (
    Portfolio,
    UserInterest,
)

User = get_user_model()

pytestmark = pytest.mark.unit


# ------------------------------------------------------------------
# Me / 세션 기반 인증
# ------------------------------------------------------------------

class TestMeView:
    """현재 로그인 사용자 정보 조회/수정 (Me view)"""

    @pytest.mark.django_db
    def test_me_get_authenticated(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자
        When: GET /api/v1/users/me/
        Then: 200 OK + 본인 프로필 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'test@example.com'
        assert response.data['nick_name'] == '테스트유저'

    @pytest.mark.django_db
    def test_me_get_unauthenticated(self, api_client):
        """
        Given: 비인증
        When: GET /api/v1/users/me/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_me_patch_updates_nickname(self, api_client, authenticated_user):
        """
        Given: 인증 + nick_name 변경 데이터
        When: PATCH /api/v1/users/me/
        Then: 200 OK + DB 반영
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.patch(
            '/api/v1/users/me/', {'nick_name': '새닉네임'}
        )

        assert response.status_code == status.HTTP_200_OK
        authenticated_user.refresh_from_db()
        assert authenticated_user.nick_name == '새닉네임'

    @pytest.mark.django_db
    def test_me_put_ignores_readonly_fields(self, api_client, authenticated_user):
        """
        Given: is_staff=True 로 변경 시도
        When: PUT /api/v1/users/me/
        Then: 200 OK 이지만 is_staff 는 read_only 라 변경 안됨
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.put(
            '/api/v1/users/me/', {'is_staff': True, 'nick_name': '변경됨'}
        )

        assert response.status_code == status.HTTP_200_OK
        authenticated_user.refresh_from_db()
        assert authenticated_user.is_staff is False
        assert authenticated_user.nick_name == '변경됨'


class TestPublicUserView:
    """공개 사용자 프로필 조회 (PublicUser view)"""

    @pytest.mark.django_db
    def test_public_user_returns_limited_fields(self, api_client, authenticated_user):
        """
        Given: 존재하는 사용자
        When: GET /api/v1/users/@testuser/  (비인증 허용)
        Then: 200 OK + email 미포함 (UserSerializer)
        """
        response = api_client.get(f'/api/v1/users/@{authenticated_user.username}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'email' not in response.data
        assert response.data['nick_name'] == '테스트유저'

    @pytest.mark.django_db
    def test_public_user_not_found(self, api_client):
        """
        Given: 존재하지 않는 사용자명
        When: GET /api/v1/users/@nobody/
        Then: 404
        """
        response = api_client.get('/api/v1/users/@nobody/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSessionLogIn:
    """세션 기반 로그인 (LogIn view)"""

    @pytest.mark.django_db
    def test_session_login_success(self, api_client, authenticated_user):
        """
        Given: 올바른 자격증명
        When: POST /api/v1/users/login/
        Then: 200 OK + ok 메시지
        """
        response = api_client.post(
            '/api/v1/users/login/',
            {'username': 'testuser', 'password': 'testpass123'},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['ok'] == 'Welcome!'
        assert response.data['user']['email'] == 'test@example.com'

    @pytest.mark.django_db
    def test_session_login_wrong_password(self, api_client, authenticated_user):
        """
        Given: 잘못된 비밀번호
        When: POST /api/v1/users/login/
        Then: 401 Unauthorized
        """
        response = api_client.post(
            '/api/v1/users/login/',
            {'username': 'testuser', 'password': 'wrong'},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_session_login_missing_fields(self, api_client):
        """
        Given: username/password 누락
        When: POST /api/v1/users/login/
        Then: 400 Bad Request (ParseError)
        """
        response = api_client.post('/api/v1/users/login/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSessionLogOut:
    """세션 기반 로그아웃"""

    @pytest.mark.django_db
    def test_session_logout_authenticated(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자
        When: POST /api/v1/users/logout/
        Then: 200 OK
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.post('/api/v1/users/logout/')

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_session_logout_unauthenticated(self, api_client):
        """
        Given: 비인증
        When: POST /api/v1/users/logout/
        Then: 401 Unauthorized
        """
        response = api_client.post('/api/v1/users/logout/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestSessionChangePassword:
    """세션 기반 비밀번호 변경 (ChangePassword view)"""

    @pytest.mark.django_db
    def test_change_password_success(self, api_client, authenticated_user):
        """
        Given: 올바른 현재 비밀번호 + 새 비밀번호
        When: PUT /api/v1/users/change_password/
        Then: 200 OK + 비밀번호 변경 반영
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.put(
            '/api/v1/users/change_password/',
            {'old_password': 'testpass123', 'new_password': 'newpass456'},
        )

        assert response.status_code == status.HTTP_200_OK
        authenticated_user.refresh_from_db()
        assert authenticated_user.check_password('newpass456')

    @pytest.mark.django_db
    def test_change_password_missing_fields(self, api_client, authenticated_user):
        """
        Given: 인증되었으나 필드 누락
        When: PUT /api/v1/users/change_password/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.put(
            '/api/v1/users/change_password/', {'old_password': 'testpass123'}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_change_password_wrong_current(self, api_client, authenticated_user):
        """
        Given: 잘못된 현재 비밀번호
        When: PUT /api/v1/users/change_password/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.put(
            '/api/v1/users/change_password/',
            {'old_password': 'wrong', 'new_password': 'newpass456'},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ------------------------------------------------------------------
# Favorites: views.py 가 stocks.serializers.StockSerializer / Stock.id 를
# 참조하지만 두 심볼 모두 현재 코드베이스에 존재하지 않아 production 에서도
# 500 으로 실패한다. 소스 수정 금지 규칙에 따라 해당 엔드포인트 테스트는 생략.
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# Portfolio 부가 뷰
# ------------------------------------------------------------------

class TestPortfolioDetailTableView:
    """포트폴리오 상세 테이블 뷰"""

    @pytest.mark.django_db
    def test_table_with_summary(self, api_client, authenticated_user, portfolio):
        """
        Given: 포트폴리오 1건 보유
        When: GET /api/v1/users/portfolio/table/
        Then: 200 OK + portfolios + summary 키 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/table/')

        assert response.status_code == status.HTTP_200_OK
        assert 'portfolios' in response.data
        assert 'summary' in response.data
        assert response.data['summary']['total_stocks'] == 1
        assert response.data['summary']['is_profitable'] is True

    @pytest.mark.django_db
    def test_table_empty(self, api_client, authenticated_user):
        """
        Given: 보유 없음
        When: GET /api/v1/users/portfolio/table/
        Then: 200 OK + total_stocks=0
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/table/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['total_stocks'] == 0
        assert response.data['portfolios'] == []

    @pytest.mark.django_db
    def test_quick_update_target_price(self, api_client, authenticated_user, portfolio):
        """
        Given: 인증 사용자의 포트폴리오
        When: PATCH /api/v1/users/portfolio/{pk}/quick-update/ (target_price 수정)
        Then: 200 OK + target_price 갱신
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.patch(
            f'/api/v1/users/portfolio/{portfolio.pk}/quick-update/',
            {'target_price': '200.00'},
        )

        assert response.status_code == status.HTTP_200_OK
        portfolio.refresh_from_db()
        assert portfolio.target_price == Decimal('200.0000')

    @pytest.mark.django_db
    def test_quick_update_disallowed_field_ignored(
        self, api_client, authenticated_user, portfolio
    ):
        """
        Given: quantity 같은 비허용 필드 변경 시도
        When: PATCH quick-update
        Then: 200 OK 이지만 quantity 는 변경되지 않음 (allow list 외 무시)
        """
        original_quantity = portfolio.quantity
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.patch(
            f'/api/v1/users/portfolio/{portfolio.pk}/quick-update/',
            {'quantity': '999', 'notes': '메모만 변경'},
        )

        assert response.status_code == status.HTTP_200_OK
        portfolio.refresh_from_db()
        assert portfolio.quantity == original_quantity
        assert portfolio.notes == '메모만 변경'

    @pytest.mark.django_db
    def test_quick_update_other_user_portfolio(
        self, api_client, authenticated_user, other_user, stock_msft
    ):
        """
        Given: 다른 사용자의 포트폴리오
        When: PATCH quick-update
        Then: 404
        """
        other_portfolio = Portfolio.objects.create(
            user=other_user,
            stock=stock_msft,
            quantity=Decimal('5'),
            average_price=Decimal('350.00'),
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.patch(
            f'/api/v1/users/portfolio/{other_portfolio.pk}/quick-update/',
            {'target_price': '400.00'},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPortfolioBySymbolView:
    """심볼로 포트폴리오 조회"""

    @pytest.mark.django_db
    def test_by_symbol_uppercase(self, api_client, authenticated_user, portfolio):
        """
        Given: AAPL 보유
        When: GET /api/v1/users/portfolio/symbol/AAPL/
        Then: 200 OK + 해당 데이터
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/symbol/AAPL/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['stock_symbol'] == 'AAPL'

    @pytest.mark.django_db
    def test_by_symbol_lowercase_normalized(
        self, api_client, authenticated_user, portfolio
    ):
        """
        Given: AAPL 보유
        When: GET /api/v1/users/portfolio/symbol/aapl/  (소문자)
        Then: 200 OK (symbol.upper() 처리)
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/symbol/aapl/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['stock_symbol'] == 'AAPL'

    @pytest.mark.django_db
    def test_by_symbol_not_owned(self, api_client, authenticated_user, stock_msft):
        """
        Given: MSFT 미보유
        When: GET /api/v1/users/portfolio/symbol/MSFT/
        Then: 404 Not Found
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/symbol/MSFT/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStockDataStatusView:
    """주식 데이터 수집 상태 폴링 엔드포인트"""

    @pytest.mark.django_db
    def test_status_returns_dict(self, api_client, authenticated_user):
        """
        Given: 인증 사용자
        When: GET /api/v1/users/portfolio/symbol/AAPL/status/  (utils mock)
        Then: 200 OK + utils.get_stock_data_status 반환값 그대로
        """
        api_client.force_authenticate(user=authenticated_user)

        with patch('packages.shared.users.utils.get_stock_data_status') as mocked:
            mocked.return_value = {'symbol': 'AAPL', 'status': 'ready', 'progress': 100}
            response = api_client.get('/api/v1/users/portfolio/symbol/AAPL/status/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'symbol': 'AAPL', 'status': 'ready', 'progress': 100}

    @pytest.mark.django_db
    def test_status_unauthenticated(self, api_client):
        """
        Given: 비인증
        When: GET /api/v1/users/portfolio/symbol/AAPL/status/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/portfolio/symbol/AAPL/status/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRefreshStockDataView:
    """단일 주식 데이터 수동 갱신"""

    @pytest.mark.django_db
    def test_refresh_not_in_portfolio(self, api_client, authenticated_user, stock_msft):
        """
        Given: 보유하지 않은 종목
        When: POST /api/v1/users/portfolio/symbol/MSFT/refresh/
        Then: 404 Not Found (보유 검사 실패)
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.post('/api/v1/users/portfolio/symbol/MSFT/refresh/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_refresh_success_mocked(self, api_client, authenticated_user, portfolio):
        """
        Given: AAPL 보유 + utils.fetch_stock_data_sync mock 성공
        When: POST refresh
        Then: 200 OK + 응답에 메시지/data 포함
        """
        api_client.force_authenticate(user=authenticated_user)

        with patch('packages.shared.users.utils.fetch_stock_data_sync') as mocked:
            mocked.return_value = {'success': True, 'data': {'price': 150.0}, 'errors': []}
            response = api_client.post('/api/v1/users/portfolio/symbol/AAPL/refresh/')

        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data
        assert response.data['data']['price'] == 150.0


# ------------------------------------------------------------------
# UserInterest
# ------------------------------------------------------------------

class TestUserInterestList:
    """UserInterest 목록/생성"""

    @pytest.mark.django_db
    def test_list_empty(self, api_client, authenticated_user):
        """
        Given: 관심사 없음
        When: GET /api/v1/users/interests/
        Then: 200 OK + 빈 리스트
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    @pytest.mark.django_db
    def test_list_only_own(self, api_client, authenticated_user, other_user):
        """
        Given: 다른 사용자의 관심사 존재
        When: GET /api/v1/users/interests/
        Then: 자신의 관심사만 반환
        """
        UserInterest.objects.create(
            user=other_user,
            interest_type='sector',
            value='Technology',
            display_name='Technology',
        )
        UserInterest.objects.create(
            user=authenticated_user,
            interest_type='sector',
            value='Healthcare',
            display_name='Healthcare',
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['value'] == 'Healthcare'

    @pytest.mark.django_db
    def test_create_interest_invalid_payload(self, api_client, authenticated_user):
        """
        Given: 'interests' 필드 누락
        When: POST /api/v1/users/interests/
        Then: 400 Bad Request (ValidationError)
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.post('/api/v1/users/interests/', {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_interest_skips_existing(self, api_client, authenticated_user):
        """
        Given: 동일 (user, type, value) 가 이미 존재
        When: POST 로 같은 값 재추가
        Then: skipped 에 포함, created 는 비어있음
        """
        UserInterest.objects.create(
            user=authenticated_user,
            interest_type='sector',
            value='Technology',
            display_name='Technology',
        )

        api_client.force_authenticate(user=authenticated_user)

        payload = {
            'interests': [
                {
                    'interest_type': 'sector',
                    'value': 'Technology',
                    'display_name': 'Technology',
                }
            ]
        }

        with patch(
            'packages.shared.users.views.UserInterestListCreateView._link_category',
            return_value=None,
        ):
            response = api_client.post(
                '/api/v1/users/interests/', payload, format='json'
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['created'] == []
        assert 'Technology' in response.data['skipped']


class TestUserInterestDelete:
    """UserInterest 삭제"""

    @pytest.mark.django_db
    def test_delete_own_interest(self, api_client, authenticated_user):
        """
        Given: 자신의 관심사
        When: DELETE /api/v1/users/interests/{pk}/
        Then: 204 + DB 제거
        """
        interest = UserInterest.objects.create(
            user=authenticated_user,
            interest_type='theme',
            value='ai',
            display_name='AI',
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(f'/api/v1/users/interests/{interest.pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserInterest.objects.filter(pk=interest.pk).exists()

    @pytest.mark.django_db
    def test_delete_other_user_interest(
        self, api_client, authenticated_user, other_user
    ):
        """
        Given: 다른 사용자의 관심사
        When: DELETE 시도
        Then: 404 Not Found
        """
        other_interest = UserInterest.objects.create(
            user=other_user,
            interest_type='sector',
            value='Technology',
            display_name='Technology',
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(f'/api/v1/users/interests/{other_interest.pk}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert UserInterest.objects.filter(pk=other_interest.pk).exists()
