"""
HealthCheckView 보안 테스트 (audit P0)

헬스체크 응답에 raw exception 메시지 노출 차단 검증.
"""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.unit


@pytest.fixture
def api_client():
    return APIClient()


class TestHealthCheckSecurity:
    @pytest.mark.django_db
    def test_healthy_response_no_error_field(self, api_client):
        """
        Given: 정상 상태
        When: GET /api/v1/health/
        Then: 200 OK + error 필드 없음 (모든 컴포넌트 healthy)
        """
        response = api_client.get('/api/v1/health/')

        assert response.status_code == status.HTTP_200_OK
        for component in response.data["components"].values():
            assert "error" not in component, f"error 필드 노출됨: {component}"

    @pytest.mark.django_db
    def test_db_failure_does_not_leak_exception(self, api_client):
        """
        Given: DB connection 실패
        When: GET /api/v1/health/
        Then: status=degraded, components.database.status=unhealthy, error 필드 없음
        """
        with patch("django.db.connection.cursor") as mock_cursor:
            mock_cursor.return_value.__enter__.side_effect = RuntimeError(
                "secret connection string with password=hunter2"
            )

            response = api_client.get('/api/v1/health/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == "degraded"
            assert response.data["components"]["database"]["status"] == "unhealthy"
            assert "error" not in response.data["components"]["database"]

            body_str = str(response.data)
            assert "hunter2" not in body_str
            assert "secret connection" not in body_str

    @pytest.mark.django_db
    def test_cache_failure_does_not_leak_exception(self, api_client):
        """
        Given: Cache write 실패
        When: GET /api/v1/health/
        Then: cache.status=unhealthy, error 필드 없음
        """
        with patch("django.core.cache.cache.set") as mock_set:
            mock_set.side_effect = RuntimeError("internal redis host=secret.internal:6379")

            response = api_client.get('/api/v1/health/')

            assert response.data["components"]["cache"]["status"] == "unhealthy"
            assert "error" not in response.data["components"]["cache"]
            assert "secret.internal" not in str(response.data)
