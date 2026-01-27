# api_request/urls.py
"""
API Request URL Patterns

Provider Admin API 엔드포인트를 정의합니다.
"""

from django.urls import path
from .admin_views import (
    provider_status_view,
    rate_limit_status_view,
    cache_management_view,
    provider_test_view,
    provider_config_view,
    health_check_view,
)

app_name = 'api_request'

urlpatterns = [
    # Health Check (인증 불필요)
    path('health/', health_check_view, name='health-check'),

    # Provider Admin API (IsAdminUser 권한 필요)
    path('admin/providers/status/', provider_status_view, name='provider-status'),
    path('admin/providers/rate-limits/', rate_limit_status_view, name='rate-limits'),
    path('admin/providers/cache/', cache_management_view, name='cache-management'),
    path('admin/providers/test/', provider_test_view, name='provider-test'),
    path('admin/providers/config/', provider_config_view, name='provider-config'),
]
