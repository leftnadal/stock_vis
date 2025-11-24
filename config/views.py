"""
Root URL views for the Stock-Vis API
"""
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


def api_root(request):
    """
    Stock-Vis API Root
    인공지능이 도와주는 투자분석 플랫폼 API
    """
    # Accept header를 확인하여 JSON 요청인지 판단
    if 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse({
        'message': 'Welcome to Stock-Vis API',
        'description': '인공지능이 도와주는 투자분석 플랫폼',
        'version': 'v1.0.0',
        'endpoints': {
            'admin': '/admin/',
            'users': {
                'base': '/api/v1/users/',
                'jwt': {
                    'signup': '/api/v1/users/jwt/signup/',
                    'login': '/api/v1/users/jwt/login/',
                    'logout': '/api/v1/users/jwt/logout/',
                    'refresh': '/api/v1/users/jwt/refresh/',
                    'verify': '/api/v1/users/jwt/verify/',
                },
                'portfolio': {
                    'list': '/api/v1/users/portfolio/',
                    'table': '/api/v1/users/portfolio/table/',
                    'summary': '/api/v1/users/portfolio/summary/',
                    'detail': '/api/v1/users/portfolio/{id}/',
                },
                'favorites': '/api/v1/users/favorites/',
            },
            'stocks': {
                'base': '/api/v1/stocks/',
                'api': {
                    'chart': '/api/v1/stocks/api/chart/{symbol}/',
                    'overview': '/api/v1/stocks/api/overview/{symbol}/',
                    'search': '/api/v1/stocks/api/search/symbols/',
                    'indicators': '/api/v1/stocks/api/indicators/{symbol}/',
                    'financial': {
                        'balance_sheet': '/api/v1/stocks/api/balance-sheet/{symbol}/',
                        'income_statement': '/api/v1/stocks/api/income-statement/{symbol}/',
                        'cash_flow': '/api/v1/stocks/api/cashflow/{symbol}/',
                    }
                }
            },
            'analysis': {
                'base': '/api/v1/analysis/',
                'economic_indicators': '/api/v1/analysis/economic-indicators/',
            }
        },
        'documentation': {
            'github': 'https://github.com/your-repo/stock-vis',
            'postman': 'Available upon request',
        },
        'status': 'operational',
        'timestamp': request.META.get('HTTP_DATE', ''),
    })
    else:
        # 브라우저 요청인 경우 HTML 템플릿 렌더링
        return render(request, 'api_root.html')


def health_check(request):
    """
    Health check endpoint for monitoring
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'Stock-Vis API',
        'database': check_database_connection(),
        'cache': check_cache_connection(),
    })


def check_database_connection():
    """Check if database is accessible"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return 'connected'
    except Exception:
        return 'disconnected'


def check_cache_connection():
    """Check if cache is accessible"""
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 1)
        if cache.get('health_check') == 'ok':
            return 'connected'
        return 'disconnected'
    except Exception:
        return 'disconnected'