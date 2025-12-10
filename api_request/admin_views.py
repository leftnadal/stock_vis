# api_request/admin_views.py
"""
Provider Admin API Endpoints

Provider 상태 확인, Rate Limit 관리, 캐시 관리를 위한 Admin API입니다.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status

from .providers.factory import (
    ProviderFactory,
    ProviderType,
    EndpointType,
    print_current_config,
    get_provider,
)
from .rate_limiter import get_all_rate_limit_status, get_rate_limiter, RateLimiter
from .cache.decorators import (
    invalidate_provider_cache,
    invalidate_symbol_cache,
    CacheStats,
)

logger = logging.getLogger(__name__)


class ProviderStatusView(APIView):
    """
    Provider 상태 조회 API

    GET /api/v1/admin/providers/status/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """모든 Provider의 현재 상태 조회"""
        try:
            from django.conf import settings

            status_data = {
                "providers": {},
                "feature_flags": settings.STOCK_PROVIDERS,
                "fallback_enabled": settings.PROVIDER_FALLBACK_ENABLED,
            }

            # 각 엔드포인트별 provider 상태
            for endpoint in EndpointType:
                try:
                    provider = ProviderFactory.get_provider(endpoint)
                    status_data["providers"][endpoint.value] = {
                        "provider": provider.PROVIDER_NAME,
                        "available": provider.is_available(),
                        "rate_limit": provider.get_rate_limit_status(),
                    }
                except Exception as e:
                    status_data["providers"][endpoint.value] = {
                        "error": str(e)
                    }

            return Response(status_data)

        except Exception as e:
            logger.error(f"Provider status error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RateLimitStatusView(APIView):
    """
    Rate Limit 상태 조회 API

    GET /api/v1/admin/providers/rate-limits/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """모든 Provider의 Rate Limit 상태"""
        try:
            return Response(get_all_rate_limit_status())
        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Rate Limit 카운터 리셋"""
        provider = request.data.get("provider")
        if not provider:
            return Response(
                {"error": "provider is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            limiter = get_rate_limiter(provider)
            limiter.reset()
            return Response({
                "message": f"Rate limit reset for {provider}",
                "status": limiter.get_status()
            })
        except Exception as e:
            logger.error(f"Rate limit reset error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheManagementView(APIView):
    """
    캐시 관리 API

    GET /api/v1/admin/providers/cache/
    DELETE /api/v1/admin/providers/cache/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """캐시 통계 조회"""
        try:
            return Response(CacheStats.get_stats())
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """캐시 무효화"""
        provider = request.data.get("provider")
        symbol = request.data.get("symbol")

        try:
            deleted_count = 0

            if symbol:
                deleted_count = invalidate_symbol_cache(symbol)
                message = f"Invalidated cache for symbol: {symbol}"
            elif provider:
                deleted_count = invalidate_provider_cache(provider)
                message = f"Invalidated cache for provider: {provider}"
            else:
                # 전체 캐시 통계 리셋
                CacheStats.reset()
                message = "Cache stats reset"

            return Response({
                "message": message,
                "deleted_count": deleted_count
            })

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProviderTestView(APIView):
    """
    Provider 연결 테스트 API

    POST /api/v1/admin/providers/test/
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """특정 Provider 연결 테스트"""
        provider_name = request.data.get("provider", "alpha_vantage")
        symbol = request.data.get("symbol", "AAPL")

        try:
            # Provider 타입 결정
            provider_type = ProviderType(provider_name)
            provider = ProviderFactory._get_or_create_provider(provider_type)

            # 간단한 시세 조회 테스트
            response = provider.get_quote(symbol)

            return Response({
                "provider": provider_name,
                "symbol": symbol,
                "success": response.success,
                "cached": response.cached,
                "data": {
                    "price": str(response.data.price) if response.data else None,
                    "change": str(response.data.change) if response.data else None,
                } if response.success else None,
                "error": response.error if not response.success else None,
            })

        except ValueError as e:
            return Response(
                {"error": f"Invalid provider: {provider_name}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Provider test error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProviderConfigView(APIView):
    """
    Provider 설정 조회 API

    GET /api/v1/admin/providers/config/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """현재 Provider 설정 조회"""
        try:
            from django.conf import settings

            return Response({
                "feature_flags": settings.STOCK_PROVIDERS,
                "cache_ttl": settings.PROVIDER_CACHE_TTL,
                "rate_limits": settings.PROVIDER_RATE_LIMITS,
                "fallback_enabled": settings.PROVIDER_FALLBACK_ENABLED,
            })

        except Exception as e:
            logger.error(f"Provider config error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthCheckView(APIView):
    """
    시스템 헬스 체크 API

    GET /api/v1/health/
    """
    permission_classes = []  # 인증 불필요

    def get(self, request):
        """시스템 전체 헬스 체크"""
        from django.db import connection
        from django.core.cache import cache
        from django.utils import timezone

        health_status = {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "components": {}
        }

        # Database 체크
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["components"]["database"] = {
                "status": "healthy",
                "type": "postgresql"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"

        # Redis/Cache 체크
        try:
            cache.set("health_check", "ok", 10)
            if cache.get("health_check") == "ok":
                health_status["components"]["cache"] = {
                    "status": "healthy",
                    "type": "redis"
                }
            else:
                raise Exception("Cache read/write failed")
        except Exception as e:
            health_status["components"]["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"

        # Provider 체크
        try:
            provider = ProviderFactory.get_provider(EndpointType.QUOTE)
            health_status["components"]["provider"] = {
                "status": "healthy",
                "active": provider.PROVIDER_NAME
            }
        except Exception as e:
            health_status["components"]["provider"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        return Response(health_status)


# URL 패턴용 (urls.py에서 사용)
provider_status_view = ProviderStatusView.as_view()
rate_limit_status_view = RateLimitStatusView.as_view()
cache_management_view = CacheManagementView.as_view()
provider_test_view = ProviderTestView.as_view()
provider_config_view = ProviderConfigView.as_view()
health_check_view = HealthCheckView.as_view()
