"""
Users Serializer 유효성 검증 테스트

시리얼라이저 필드 검증, 유효성 검사, 계산된 필드 테스트
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from users.serializers import (
    UserSerializer,
    PrivateUserSerializer,
    PortfolioSerializer,
    PortfolioCreateUpdateSerializer,
    WatchlistCreateUpdateSerializer,
    WatchlistItemCreateSerializer,
)
from users.models import Portfolio

User = get_user_model()

pytestmark = pytest.mark.unit


class TestUserSerializer:
    """UserSerializer 필드 검증"""

    @pytest.mark.django_db
    def test_user_serializer_fields(self, authenticated_user):
        """
        Given: User 인스턴스
        When: UserSerializer로 직렬화
        Then: 제한된 필드만 포함 (id, user_name, nick_name, favorite_stock)
        """
        serializer = UserSerializer(authenticated_user)
        data = serializer.data

        assert set(data.keys()) == {'id', 'user_name', 'nick_name', 'favorite_stock'}
        assert 'email' not in data
        assert 'password' not in data

    @pytest.mark.django_db
    def test_private_user_serializer_fields(self, authenticated_user):
        """
        Given: User 인스턴스
        When: PrivateUserSerializer로 직렬화
        Then: 개인정보 포함 필드 반환
        """
        serializer = PrivateUserSerializer(authenticated_user)
        data = serializer.data

        assert 'email' in data
        assert 'is_superuser' in data
        assert 'is_staff' in data
        assert 'date_joined' in data
        assert data['email'] == 'test@example.com'

    @pytest.mark.django_db
    def test_private_user_serializer_read_only_fields(self, authenticated_user):
        """
        Given: PrivateUserSerializer에 read_only 필드 변경 시도
        When: 시리얼라이저로 업데이트
        Then: read_only 필드는 무시됨
        """
        serializer = PrivateUserSerializer(
            authenticated_user,
            data={'is_staff': True, 'nick_name': '변경됨'},
            partial=True,
        )

        assert serializer.is_valid()
        user = serializer.save()

        assert user.nick_name == '변경됨'
        assert user.is_staff is False  # read_only이므로 변경 안 됨


class TestPortfolioCreateUpdateSerializer:
    """PortfolioCreateUpdateSerializer 유효성 검증"""

    @pytest.mark.django_db
    def test_validate_quantity_zero(self, authenticated_user, stock_aapl):
        """
        Given: 수량이 0
        When: validate_quantity
        Then: ValidationError 발생
        """
        factory = APIRequestFactory()
        request = factory.post('/fake/')
        request.user = authenticated_user

        serializer = PortfolioCreateUpdateSerializer(
            data={'stock': 'AAPL', 'quantity': '0', 'average_price': '150.00'},
            context={'request': request},
        )

        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors

    @pytest.mark.django_db
    def test_validate_average_price_zero(self, authenticated_user, stock_aapl):
        """
        Given: 평균가가 0
        When: validate_average_price
        Then: ValidationError 발생
        """
        factory = APIRequestFactory()
        request = factory.post('/fake/')
        request.user = authenticated_user

        serializer = PortfolioCreateUpdateSerializer(
            data={'stock': 'AAPL', 'quantity': '10', 'average_price': '0'},
            context={'request': request},
        )

        assert not serializer.is_valid()
        assert 'average_price' in serializer.errors

    @pytest.mark.django_db
    def test_validate_stock_existing(self, authenticated_user, stock_aapl):
        """
        Given: DB에 존재하는 stock 심볼
        When: validate_stock
        Then: Stock 객체 반환 (외부 API 호출 없이)
        """
        factory = APIRequestFactory()
        request = factory.post('/fake/')
        request.user = authenticated_user

        serializer = PortfolioCreateUpdateSerializer(
            data={'stock': 'AAPL', 'quantity': '10', 'average_price': '150.00'},
            context={'request': request},
        )

        assert serializer.is_valid()
        assert serializer.validated_data['stock'] == stock_aapl

    @pytest.mark.django_db
    def test_validate_stock_case_insensitive(self, authenticated_user, stock_aapl):
        """
        Given: 소문자로 입력된 심볼
        When: validate_stock
        Then: upper() 변환 후 정상 검증
        """
        factory = APIRequestFactory()
        request = factory.post('/fake/')
        request.user = authenticated_user

        serializer = PortfolioCreateUpdateSerializer(
            data={'stock': 'aapl', 'quantity': '10', 'average_price': '150.00'},
            context={'request': request},
        )

        assert serializer.is_valid()
        assert serializer.validated_data['stock'].symbol == 'AAPL'


class TestPortfolioSerializer:
    """PortfolioSerializer 계산 필드 검증"""

    @pytest.mark.django_db
    def test_computed_fields(self, portfolio):
        """
        Given: Portfolio 인스턴스
        When: PortfolioSerializer로 직렬화
        Then: 계산된 필드(total_value, profit_loss 등) 포함
        """
        serializer = PortfolioSerializer(portfolio)
        data = serializer.data

        assert 'total_value' in data
        assert 'total_cost' in data
        assert 'profit_loss' in data
        assert 'profit_loss_percentage' in data
        assert 'is_profitable' in data
        assert data['stock_symbol'] == 'AAPL'
        assert data['is_profitable'] is True


class TestWatchlistCreateUpdateSerializer:
    """WatchlistCreateUpdateSerializer 유효성 검증"""

    @pytest.mark.django_db
    def test_validate_name_empty(self, authenticated_user):
        """
        Given: 빈 문자열 이름
        When: validate_name
        Then: ValidationError 발생
        """
        factory = APIRequestFactory()
        request = factory.post('/fake/')
        request.user = authenticated_user

        serializer = WatchlistCreateUpdateSerializer(
            data={'name': '   ', 'description': '설명'},
            context={'request': request},
        )

        assert not serializer.is_valid()
        assert 'name' in serializer.errors

    @pytest.mark.django_db
    def test_validate_name_strip(self, authenticated_user):
        """
        Given: 앞뒤 공백이 있는 이름
        When: validate_name
        Then: 공백 제거 후 반환
        """
        factory = APIRequestFactory()
        request = factory.post('/fake/')
        request.user = authenticated_user

        serializer = WatchlistCreateUpdateSerializer(
            data={'name': '  관심종목  '},
            context={'request': request},
        )

        assert serializer.is_valid()
        assert serializer.validated_data['name'] == '관심종목'


class TestWatchlistItemCreateSerializer:
    """WatchlistItemCreateSerializer 유효성 검증"""

    @pytest.mark.django_db
    def test_validate_target_entry_price_negative(self, stock_aapl):
        """
        Given: 음수 목표 진입가
        When: validate_target_entry_price
        Then: ValidationError 발생
        """
        serializer = WatchlistItemCreateSerializer(
            data={
                'stock': 'AAPL',
                'target_entry_price': '-10.00',
            },
        )

        assert not serializer.is_valid()
        assert 'target_entry_price' in serializer.errors

    @pytest.mark.django_db
    def test_validate_target_entry_price_null_allowed(self, stock_aapl):
        """
        Given: 목표 진입가 null
        When: validate
        Then: 유효함 (선택 필드)
        """
        serializer = WatchlistItemCreateSerializer(
            data={
                'stock': 'AAPL',
                'target_entry_price': None,
            },
        )

        assert serializer.is_valid()
