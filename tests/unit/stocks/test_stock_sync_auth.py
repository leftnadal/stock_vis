"""
StockSyncAPIView 인증 보안 테스트 (audit P0)

비인증 외부 API 트리거 차단 검증. cost amplification 공격 방지.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.unit


@pytest.fixture
def api_client():
    return APIClient()


class TestStockSyncAuth:
    @pytest.mark.django_db
    def test_anonymous_request_blocked(self, api_client):
        """
        Given: 비인증 클라이언트
        When: POST /api/v1/stocks/api/sync/AAPL/
        Then: 401 Unauthorized — 외부 API 호출 차단
        """
        response = api_client.post('/api/v1/stocks/api/sync/AAPL/', data={}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_authenticated_request_accepted(self, api_client, user):
        """
        Given: 인증된 사용자
        When: POST /api/v1/stocks/api/sync/AAPL/
        Then: 401이 아닌 다른 상태 (인증 통과)
        """
        api_client.force_authenticate(user=user)
        response = api_client.post('/api/v1/stocks/api/sync/AAPL/', data={}, format='json')

        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN
