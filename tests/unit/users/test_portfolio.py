"""
Portfolio CRUD 테스트

포트폴리오 생성, 조회, 수정, 삭제, 요약, 권한 테스트
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from packages.shared.users.models import Portfolio

User = get_user_model()

pytestmark = pytest.mark.unit


class TestPortfolioList:
    """포트폴리오 목록 조회 테스트"""

    @pytest.mark.django_db
    def test_list_portfolios(self, api_client, authenticated_user, portfolio):
        """
        Given: 포트폴리오 항목이 있는 인증된 사용자
        When: GET /api/v1/users/portfolio/
        Then: 사용자의 포트폴리오 목록 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['stock_symbol'] == 'AAPL'

    @pytest.mark.django_db
    def test_list_portfolios_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: GET /api/v1/users/portfolio/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/portfolio/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_list_portfolios_empty(self, api_client, authenticated_user):
        """
        Given: 포트폴리오가 없는 사용자
        When: GET /api/v1/users/portfolio/
        Then: 빈 리스트 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_list_portfolios_only_own(self, api_client, authenticated_user, other_user, stock_aapl):
        """
        Given: 다른 사용자의 포트폴리오가 존재
        When: GET /api/v1/users/portfolio/
        Then: 자신의 포트폴리오만 반환
        """
        # 다른 유저의 포트폴리오
        Portfolio.objects.create(
            user=other_user,
            stock=stock_aapl,
            quantity=Decimal('5'),
            average_price=Decimal('145.00'),
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


class TestPortfolioCreate:
    """포트폴리오 생성 테스트"""

    @pytest.mark.django_db
    @patch('packages.shared.users.utils.fetch_stock_data_background')
    def test_create_portfolio_success(self, mock_fetch, api_client, authenticated_user, stock_aapl):
        """
        Given: 유효한 포트폴리오 생성 데이터 (이미 존재하는 Stock)
        When: POST /api/v1/users/portfolio/
        Then: 201 Created
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'quantity': '10',
            'average_price': '145.50',
            'target_price': '180.00',
            'notes': '장기 보유 예정',
        }

        response = api_client.post('/api/v1/users/portfolio/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['stock_symbol'] == 'AAPL'
        assert Portfolio.objects.filter(
            user=authenticated_user, stock=stock_aapl
        ).exists()

    @pytest.mark.django_db
    @patch('packages.shared.users.utils.fetch_stock_data_background')
    def test_create_portfolio_duplicate_stock(self, mock_fetch, api_client, authenticated_user, portfolio):
        """
        Given: 이미 포트폴리오에 있는 종목
        When: POST /api/v1/users/portfolio/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'quantity': '5',
            'average_price': '155.00',
        }

        response = api_client.post('/api/v1/users/portfolio/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_portfolio_invalid_quantity(self, api_client, authenticated_user, stock_aapl):
        """
        Given: 수량이 0 이하
        When: POST /api/v1/users/portfolio/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'stock': 'AAPL',
            'quantity': '0',
            'average_price': '150.00',
        }

        response = api_client.post('/api/v1/users/portfolio/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPortfolioDetail:
    """포트폴리오 상세 조회/수정/삭제 테스트"""

    @pytest.mark.django_db
    def test_get_portfolio_detail(self, api_client, authenticated_user, portfolio):
        """
        Given: 인증된 사용자의 포트폴리오
        When: GET /api/v1/users/portfolio/{pk}/
        Then: 포트폴리오 상세 정보 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(f'/api/v1/users/portfolio/{portfolio.pk}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['stock_symbol'] == 'AAPL'
        assert 'profit_loss' in response.data
        assert 'profit_loss_percentage' in response.data

    @pytest.mark.django_db
    def test_update_portfolio(self, api_client, authenticated_user, portfolio):
        """
        Given: 인증된 사용자의 포트폴리오
        When: PUT /api/v1/users/portfolio/{pk}/
        Then: 포트폴리오 수정됨
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'quantity': '20',
            'average_price': '142.00',
            'notes': '추가 매수',
        }

        response = api_client.put(f'/api/v1/users/portfolio/{portfolio.pk}/', data)

        assert response.status_code == status.HTTP_200_OK

        portfolio.refresh_from_db()
        assert portfolio.quantity == Decimal('20')
        assert portfolio.notes == '추가 매수'

    @pytest.mark.django_db
    def test_delete_portfolio(self, api_client, authenticated_user, portfolio):
        """
        Given: 인증된 사용자의 포트폴리오
        When: DELETE /api/v1/users/portfolio/{pk}/
        Then: 204 No Content + 포트폴리오 삭제됨
        """
        api_client.force_authenticate(user=authenticated_user)
        pk = portfolio.pk

        response = api_client.delete(f'/api/v1/users/portfolio/{pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Portfolio.objects.filter(pk=pk).exists()

    @pytest.mark.django_db
    def test_access_other_user_portfolio(self, api_client, authenticated_user, other_user, stock_msft):
        """
        Given: 다른 사용자의 포트폴리오
        When: GET /api/v1/users/portfolio/{pk}/
        Then: 404 Not Found (소유자가 아님)
        """
        other_portfolio = Portfolio.objects.create(
            user=other_user,
            stock=stock_msft,
            quantity=Decimal('5'),
            average_price=Decimal('350.00'),
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get(f'/api/v1/users/portfolio/{other_portfolio.pk}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_delete_other_user_portfolio(self, api_client, authenticated_user, other_user, stock_msft):
        """
        Given: 다른 사용자의 포트폴리오
        When: DELETE /api/v1/users/portfolio/{pk}/
        Then: 404 Not Found
        """
        other_portfolio = Portfolio.objects.create(
            user=other_user,
            stock=stock_msft,
            quantity=Decimal('5'),
            average_price=Decimal('350.00'),
        )

        api_client.force_authenticate(user=authenticated_user)

        response = api_client.delete(f'/api/v1/users/portfolio/{other_portfolio.pk}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # 원본 데이터가 삭제되지 않았는지 확인
        assert Portfolio.objects.filter(pk=other_portfolio.pk).exists()

    @pytest.mark.django_db
    def test_get_nonexistent_portfolio(self, api_client, authenticated_user):
        """
        Given: 존재하지 않는 포트폴리오 ID
        When: GET /api/v1/users/portfolio/99999/
        Then: 404 Not Found
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPortfolioSummary:
    """포트폴리오 요약 테스트"""

    @pytest.mark.django_db
    def test_summary_empty(self, api_client, authenticated_user):
        """
        Given: 빈 포트폴리오
        When: GET /api/v1/users/portfolio/summary/
        Then: 기본값 반환 (total_stocks=0)
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_stocks'] == 0
        assert float(response.data['total_value']) == 0

    @pytest.mark.django_db
    def test_summary_with_portfolio(self, api_client, authenticated_user, portfolio):
        """
        Given: 포트폴리오에 종목이 있는 사용자
        When: GET /api/v1/users/portfolio/summary/
        Then: 올바른 요약 계산 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/portfolio/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_stocks'] == 1
        # total_value = 10 * 150.25 = 1502.5
        assert float(response.data['total_value']) == pytest.approx(1502.5, abs=0.1)
        # total_cost = 10 * 140.00 = 1400.0
        assert float(response.data['total_cost']) == pytest.approx(1400.0, abs=0.1)
        assert response.data['is_profitable'] is True

    @pytest.mark.django_db
    def test_summary_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: GET /api/v1/users/portfolio/summary/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/portfolio/summary/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPortfolioModel:
    """Portfolio 모델 프로퍼티 테스트"""

    @pytest.mark.django_db
    def test_profit_loss_calculation(self, portfolio):
        """
        Given: 평균가 140, 현재가 150.25, 수량 10
        When: profit_loss, profit_loss_percentage 조회
        Then: 올바른 수익/수익률 계산
        """
        # profit_loss = (150.25 - 140.00) * 10 = 102.5
        assert portfolio.profit_loss == pytest.approx(102.5, abs=0.1)
        # profit_loss_percentage = 102.5 / 1400 * 100 ≈ 7.32%
        assert portfolio.profit_loss_percentage == pytest.approx(7.32, abs=0.1)
        assert portfolio.is_profitable is True

    @pytest.mark.django_db
    def test_distance_from_target(self, portfolio):
        """
        Given: 목표가 180, 현재가 150.25
        When: distance_from_target 조회
        Then: 올바른 거리 계산
        """
        # ((180 - 150.25) / 150.25) * 100 ≈ 19.8%
        assert portfolio.distance_from_target == pytest.approx(19.8, abs=0.5)

    @pytest.mark.django_db
    def test_distance_from_stop_loss(self, portfolio):
        """
        Given: 손절가 120, 현재가 150.25
        When: distance_from_stop_loss 조회
        Then: 올바른 거리 계산
        """
        # ((150.25 - 120) / 150.25) * 100 ≈ 20.1%
        assert portfolio.distance_from_stop_loss == pytest.approx(20.1, abs=0.5)
