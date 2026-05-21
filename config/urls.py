"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from . import views


urlpatterns = [
    # Root and health check
    path('', views.api_root, name='api-root'),
    path('health/', views.health_check, name='health-check'),

    # Admin
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/v1/users/', include("users.urls")),
    path('api/v1/stocks/', include("stocks.urls")),
    path('api/v1/news/', include("news.api.urls")),
    path('api/v1/macro/', include("macro.urls")),  # 거시경제 대시보드
    path('api/v1/rag/', include("rag_analysis.urls")),  # RAG 분석
    path('api/v1/serverless/', include("serverless.urls")),  # Market Movers (AWS 전환 대상)
    path('api/v1/thesis/', include("thesis.urls")),  # Thesis Control (가설 통제실)
    path('api/v1/validation/', include("validation.api.urls")),  # 1차 검증
    path('api/v1/chainsight/', include("chainsight.api.urls")),  # Chain Sight 그래프 탐색
    path('api/v1/sec-pipeline/', include("sec_pipeline.urls")),  # SEC Pipeline 대시보드

    # Provider Admin API
    path('api/v1/', include('api_request.urls')),

    # Portfolio Coach (slice 1: E1+GARP) — 순수 Django view
    path('api/', include('portfolio.urls')),

    # Portfolio Coach DRF API (Slice 13 Part 1+) — 별도 endpoint
    path('api/', include('portfolio.api.urls', namespace='portfolio_api')),

    # Market Pulse v2 (PR-I/J)
    path('api/v2/market-pulse/', include('marketpulse.api.urls')),

    # OpenAPI / Swagger / ReDoc (drf-spectacular, Market Pulse v2)
    path('api/v2/schema/', SpectacularAPIView.as_view(), name='schema-v2'),
    path(
        'api/v2/swagger/',
        SpectacularSwaggerView.as_view(url_name='schema-v2'),
        name='swagger-v2',
    ),
    path(
        'api/v2/redoc/',
        SpectacularRedocView.as_view(url_name='schema-v2'),
        name='redoc-v2',
    ),
]
