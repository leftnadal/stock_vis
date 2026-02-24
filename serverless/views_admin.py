"""
Admin Dashboard API Views

관리자 전용 대시보드 엔드포인트 (IsAdminUser 권한).
"""
import re
import time
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from django.core.cache import cache

from serverless.services.admin_status_service import AdminStatusService
from serverless.models import AdminActionLog

logger = logging.getLogger(__name__)

# ========================================
# Admin Actions 레지스트리
# ========================================

ADMIN_ACTIONS = {
    # Stocks 탭
    'sync_eod_prices': {
        'task': 'stocks.tasks.sync_sp500_eod_prices',
        'label': 'EOD 가격 동기화',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'aggregate_weekly': {
        'task': 'stocks.tasks.aggregate_weekly_prices',
        'label': '주간 가격 집계',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'sync_financials_batch': {
        'task': 'stocks.tasks.sync_sp500_financials',
        'label': '재무제표 배치 동기화',
        'cooldown_seconds': 600,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'sync_financials_bulk': {
        'task': 'stocks.tasks.bulk_sync_sp500_financials',
        'label': '재무제표 벌크 동기화',
        'cooldown_seconds': 3600,
        'dangerous': True,
        'cost_estimate': '~3,018 FMP API 호출 (일일 한도 30%)',
        'params': [],
        'required_params': [],
    },
    'sync_single_financials': {
        'task': 'stocks.tasks.update_financials_with_provider',
        'label': '단일 종목 재무제표 동기화',
        'cooldown_seconds': 10,
        'dangerous': False,
        'params': ['symbol'],
        'required_params': ['symbol'],
    },
    # Market Pulse 탭
    'sync_movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'label': 'Market Movers 동기화',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'generate_keywords': {
        'task': 'serverless.tasks.keyword_generation_pipeline',
        'label': 'AI 키워드 생성',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    # Screener 탭
    'sync_breadth': {
        'task': 'serverless.tasks.calculate_daily_market_breadth',
        'label': 'Market Breadth 계산',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'sync_heatmap': {
        'task': 'serverless.tasks.calculate_daily_sector_heatmap',
        'label': 'Sector Heatmap 계산',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    # Chain Sight 탭
    'sync_etf_holdings': {
        'task': 'serverless.tasks.sync_etf_holdings',
        'label': 'ETF Holdings 동기화',
        'cooldown_seconds': 600,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    # News 탭
    'collect_news': {
        'task': 'news.tasks.collect_daily_news',
        'label': '뉴스 수집',
        'cooldown_seconds': 600,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'extract_news_keywords': {
        'task': 'news.tasks.extract_daily_news_keywords',
        'label': '뉴스 키워드 추출',
        'cooldown_seconds': 300,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
    'collect_category_news': {
        'task': 'news.tasks.collect_category_news',
        'label': '카테고리 뉴스 수집',
        'cooldown_seconds': 600,
        'dangerous': False,
        'params': ['category_id'],
        'required_params': [],
    },
    # System 탭
    'sync_sp500_constituents': {
        'task': 'stocks.tasks.sync_sp500_constituents',
        'label': 'SP500 구성종목 동기화',
        'cooldown_seconds': 3600,
        'dangerous': False,
        'params': [],
        'required_params': [],
    },
}


class AdminOverviewView(APIView):
    """
    개요 대시보드

    GET /api/v1/serverless/admin/dashboard/overview/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            data = AdminStatusService.get_overview_summary()
            return Response(data)
        except Exception as e:
            logger.error(f"Admin overview error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminStocksView(APIView):
    """
    주식 데이터 상태

    GET /api/v1/serverless/admin/dashboard/stocks/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            data = AdminStatusService.get_stocks_status()
            return Response(data)
        except Exception as e:
            logger.error(f"Admin stocks error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminScreenerView(APIView):
    """
    스크리너 상태

    GET /api/v1/serverless/admin/dashboard/screener/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            data = AdminStatusService.get_screener_status()
            return Response(data)
        except Exception as e:
            logger.error(f"Admin screener error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminMarketPulseView(APIView):
    """
    Market Pulse 상태

    GET /api/v1/serverless/admin/dashboard/market-pulse/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            data = AdminStatusService.get_market_pulse_status()
            return Response(data)
        except Exception as e:
            logger.error(f"Admin market pulse error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminNewsView(APIView):
    """
    뉴스 데이터 상태

    GET /api/v1/serverless/admin/dashboard/news/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            data = AdminStatusService.get_news_status()
            return Response(data)
        except Exception as e:
            logger.error(f"Admin news error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminSystemView(APIView):
    """
    시스템 상태

    GET /api/v1/serverless/admin/dashboard/system/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            data = AdminStatusService.get_system_status()
            return Response(data)
        except Exception as e:
            logger.error(f"Admin system error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminTaskLogsView(APIView):
    """
    Celery 태스크 로그 조회

    GET /api/v1/serverless/admin/dashboard/tasks/?task_name=&status=&hours=24&limit=50
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            task_name = request.GET.get('task_name', None)
            task_status = request.GET.get('status', None)
            hours = int(request.GET.get('hours', 24))
            limit = min(int(request.GET.get('limit', 50)), 200)

            data = AdminStatusService.get_task_logs(
                task_name=task_name,
                task_status=task_status,
                hours=hours,
                limit=limit,
            )
            return Response(data)
        except Exception as e:
            logger.error(f"Admin task logs error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminActionView(APIView):
    """
    Admin Actions (Celery 태스크 트리거)

    GET  /admin/dashboard/actions/ — 사용 가능한 액션 목록 + 쿨다운 잔여시간
    POST /admin/dashboard/actions/ — 액션 실행
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        actions = {}
        for key, meta in ADMIN_ACTIONS.items():
            cooldown_key = f'admin_action_cooldown:{key}'
            cached_expiry = cache.get(cooldown_key)
            remaining = max(0, int(cached_expiry - time.time())) if cached_expiry else 0
            actions[key] = {
                'label': meta['label'],
                'dangerous': meta['dangerous'],
                'cooldown_seconds': meta['cooldown_seconds'],
                'cooldown_remaining': remaining,
                'params': meta.get('params', []),
                'required_params': meta.get('required_params', []),
            }
            if meta.get('cost_estimate'):
                actions[key]['cost_estimate'] = meta['cost_estimate']
        return Response({'actions': actions})

    def post(self, request):
        action_type = request.data.get('action')
        params = request.data.get('params', {})
        confirm = request.data.get('confirm', False)

        # 1. 레지스트리 검증
        if action_type not in ADMIN_ACTIONS:
            return Response(
                {'error': f'Unknown action: {action_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meta = ADMIN_ACTIONS[action_type]

        # 2. 위험 액션 확인
        if meta['dangerous'] and not confirm:
            resp = {
                'error': '위험 액션입니다. confirm: true 필요.',
                'requires_confirm': True,
                'label': meta['label'],
            }
            if meta.get('cost_estimate'):
                resp['cost_estimate'] = meta['cost_estimate']
            return Response(resp, status=status.HTTP_400_BAD_REQUEST)

        # 3. 필수 파라미터 검증
        for rp in meta.get('required_params', []):
            if rp not in params:
                return Response(
                    {'error': f'필수 파라미터 누락: {rp}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 4. 원자적 쿨다운 체크
        cooldown_key = f'admin_action_cooldown:{action_type}'
        expiry_time = time.time() + meta['cooldown_seconds']
        if not cache.add(cooldown_key, expiry_time, timeout=meta['cooldown_seconds']):
            cached_expiry = cache.get(cooldown_key)
            remaining = max(0, int(cached_expiry - time.time())) if cached_expiry else 0
            return Response(
                {
                    'error': f'쿨다운 중입니다. {remaining}초 후 다시 시도하세요.',
                    'cooldown_remaining': remaining,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # 5. send_task로 디스패치
        try:
            from config.celery import app
            # 허용된 파라미터만 필터링
            allowed_params = set(meta.get('params', []))
            filtered_params = {k: v for k, v in params.items() if k in allowed_params}
            result = app.send_task(meta['task'], kwargs=filtered_params)
        except Exception as e:
            # 쿨다운 롤백
            cache.delete(cooldown_key)
            logger.error(f"Admin action dispatch error: {e}", exc_info=True)
            return Response(
                {'error': f'태스크 디스패치 실패: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 6. 감사 로그 저장
        AdminActionLog.objects.create(
            action=action_type,
            label=meta['label'],
            user=request.user,
            params=filtered_params,
            task_id=result.id,
            status='dispatched',
        )

        logger.info(f"Admin action dispatched: {action_type} by {request.user} → task_id={result.id}")

        return Response({
            'success': True,
            'data': {
                'task_id': result.id,
                'action': action_type,
                'label': meta['label'],
                'message': f'{meta["label"]} 태스크가 시작되었습니다.',
            },
        })


class AdminTaskStatusView(APIView):
    """
    태스크 상태 폴링

    GET /admin/dashboard/actions/status/<task_id>/
    """
    permission_classes = [IsAdminUser]

    def get(self, request, task_id):
        # 1차: django_celery_results DB에서 조회
        try:
            from django_celery_results.models import TaskResult
            task_result = TaskResult.objects.get(task_id=task_id)

            # 감사 로그 업데이트
            final_status = 'success' if task_result.status == 'SUCCESS' else 'failure'
            AdminActionLog.objects.filter(task_id=task_id).update(
                status=final_status,
                result_summary=str(task_result.result)[:500] if task_result.result else '',
            )

            return Response({
                'task_id': task_id,
                'status': task_result.status,
                'result': str(task_result.result)[:500] if task_result.result else None,
                'date_done': task_result.date_done.isoformat() if task_result.date_done else None,
                'traceback': task_result.traceback or None,
            })
        except TaskResult.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"TaskResult lookup error: {e}")

        # 2차: AsyncResult로 PENDING/STARTED 상태 확인
        try:
            from celery.result import AsyncResult
            res = AsyncResult(task_id)
            return Response({
                'task_id': task_id,
                'status': res.state,
                'result': None,
                'date_done': None,
                'traceback': None,
            })
        except Exception as e:
            logger.warning(f"AsyncResult lookup error: {e}")
            return Response({
                'task_id': task_id,
                'status': 'UNKNOWN',
                'result': None,
                'date_done': None,
                'traceback': None,
            })


class AdminNewsCategoryView(APIView):
    """
    뉴스 수집 카테고리 CRUD

    GET  /admin/dashboard/news/categories/ — 카테고리 목록
    POST /admin/dashboard/news/categories/ — 카테고리 생성
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from news.models import NewsCollectionCategory

        categories = NewsCollectionCategory.objects.all()
        result = []
        for cat in categories:
            symbols = cat.resolve_symbols()
            result.append({
                'id': cat.id,
                'name': cat.name,
                'category_type': cat.category_type,
                'value': cat.value,
                'is_active': cat.is_active,
                'priority': cat.priority,
                'max_symbols': cat.max_symbols,
                'resolved_symbol_count': len(symbols),
                'resolved_symbols_preview': symbols[:5],
                'last_collected_at': cat.last_collected_at.isoformat() if cat.last_collected_at else None,
                'last_article_count': cat.last_article_count,
                'last_symbol_count': cat.last_symbol_count,
                'total_collections': cat.total_collections,
                'last_error': cat.last_error,
                'created_at': cat.created_at.isoformat(),
                'updated_at': cat.updated_at.isoformat(),
            })
        return Response({'categories': result})

    def post(self, request):
        from news.models import NewsCollectionCategory
        from stocks.models import SP500Constituent

        name = request.data.get('name', '').strip()
        category_type = request.data.get('category_type', '')
        value = request.data.get('value', '').strip()
        is_active = request.data.get('is_active', True)
        priority = request.data.get('priority', 'medium')
        max_symbols = request.data.get('max_symbols', 20)

        # 필수 필드 검증
        if not name:
            return Response({'error': '이름은 필수입니다'}, status=status.HTTP_400_BAD_REQUEST)
        if not value:
            return Response({'error': '값은 필수입니다'}, status=status.HTTP_400_BAD_REQUEST)

        # category_type 검증
        if category_type not in ('sector', 'sub_sector', 'custom'):
            return Response({'error': '유효하지 않은 카테고리 타입'}, status=status.HTTP_400_BAD_REQUEST)

        # priority 검증
        if priority not in ('high', 'medium', 'low'):
            return Response({'error': '유효하지 않은 우선순위'}, status=status.HTTP_400_BAD_REQUEST)

        # sector/sub_sector → SP500Constituent 존재 여부 확인
        if category_type == 'sector':
            if not SP500Constituent.objects.filter(sector=value, is_active=True).exists():
                return Response({'error': f'존재하지 않는 섹터: {value}'}, status=status.HTTP_400_BAD_REQUEST)
        elif category_type == 'sub_sector':
            if not SP500Constituent.objects.filter(sub_sector=value, is_active=True).exists():
                return Response({'error': f'존재하지 않는 서브섹터: {value}'}, status=status.HTTP_400_BAD_REQUEST)
        elif category_type == 'custom':
            if not re.match(r'^[A-Za-z0-9,.\s-]+$', value):
                return Response({'error': '심볼 형식이 올바르지 않습니다'}, status=status.HTTP_400_BAD_REQUEST)
            symbols = [s.strip() for s in value.split(',') if s.strip()]
            if not symbols:
                return Response({'error': '최소 1개 심볼 필요'}, status=status.HTTP_400_BAD_REQUEST)

        cat = NewsCollectionCategory.objects.create(
            name=name,
            category_type=category_type,
            value=value,
            is_active=is_active,
            priority=priority,
            max_symbols=max_symbols,
        )

        symbols = cat.resolve_symbols()
        return Response({
            'id': cat.id,
            'name': cat.name,
            'category_type': cat.category_type,
            'value': cat.value,
            'is_active': cat.is_active,
            'priority': cat.priority,
            'max_symbols': cat.max_symbols,
            'resolved_symbol_count': len(symbols),
            'resolved_symbols_preview': symbols[:5],
            'last_collected_at': None,
            'last_article_count': 0,
            'last_symbol_count': 0,
            'total_collections': 0,
            'last_error': '',
            'created_at': cat.created_at.isoformat(),
            'updated_at': cat.updated_at.isoformat(),
        }, status=status.HTTP_201_CREATED)


class AdminNewsCategoryDetailView(APIView):
    """
    뉴스 수집 카테고리 상세 (PUT/DELETE)

    PUT    /admin/dashboard/news/categories/<id>/ — 수정
    DELETE /admin/dashboard/news/categories/<id>/ — 삭제
    """
    permission_classes = [IsAdminUser]

    def put(self, request, category_id):
        from news.models import NewsCollectionCategory
        from stocks.models import SP500Constituent

        try:
            cat = NewsCollectionCategory.objects.get(id=category_id)
        except NewsCollectionCategory.DoesNotExist:
            return Response({'error': '카테고리를 찾을 수 없습니다'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'name' in data:
            cat.name = data['name'].strip()
        if 'is_active' in data:
            cat.is_active = data['is_active']
        if 'priority' in data:
            if data['priority'] not in ('high', 'medium', 'low'):
                return Response({'error': '유효하지 않은 우선순위'}, status=status.HTTP_400_BAD_REQUEST)
            cat.priority = data['priority']
        if 'max_symbols' in data:
            cat.max_symbols = data['max_symbols']

        # category_type + value 변경 시 검증
        if 'category_type' in data or 'value' in data:
            ct = data.get('category_type', cat.category_type)
            val = data.get('value', cat.value).strip()

            if ct not in ('sector', 'sub_sector', 'custom'):
                return Response({'error': '유효하지 않은 카테고리 타입'}, status=status.HTTP_400_BAD_REQUEST)

            if ct == 'sector':
                if not SP500Constituent.objects.filter(sector=val, is_active=True).exists():
                    return Response({'error': f'존재하지 않는 섹터: {val}'}, status=status.HTTP_400_BAD_REQUEST)
            elif ct == 'sub_sector':
                if not SP500Constituent.objects.filter(sub_sector=val, is_active=True).exists():
                    return Response({'error': f'존재하지 않는 서브섹터: {val}'}, status=status.HTTP_400_BAD_REQUEST)
            elif ct == 'custom':
                if not re.match(r'^[A-Za-z0-9,.\s-]+$', val):
                    return Response({'error': '심볼 형식이 올바르지 않습니다'}, status=status.HTTP_400_BAD_REQUEST)
                if not [s.strip() for s in val.split(',') if s.strip()]:
                    return Response({'error': '최소 1개 심볼 필요'}, status=status.HTTP_400_BAD_REQUEST)

            cat.category_type = ct
            cat.value = val

        cat.save()
        symbols = cat.resolve_symbols()

        return Response({
            'id': cat.id,
            'name': cat.name,
            'category_type': cat.category_type,
            'value': cat.value,
            'is_active': cat.is_active,
            'priority': cat.priority,
            'max_symbols': cat.max_symbols,
            'resolved_symbol_count': len(symbols),
            'resolved_symbols_preview': symbols[:5],
            'last_collected_at': cat.last_collected_at.isoformat() if cat.last_collected_at else None,
            'last_article_count': cat.last_article_count,
            'last_symbol_count': cat.last_symbol_count,
            'total_collections': cat.total_collections,
            'last_error': cat.last_error,
            'created_at': cat.created_at.isoformat(),
            'updated_at': cat.updated_at.isoformat(),
        })

    def delete(self, request, category_id):
        from news.models import NewsCollectionCategory

        try:
            cat = NewsCollectionCategory.objects.get(id=category_id)
        except NewsCollectionCategory.DoesNotExist:
            return Response({'error': '카테고리를 찾을 수 없습니다'}, status=status.HTTP_404_NOT_FOUND)

        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminNewsSectorOptionsView(APIView):
    """
    Sector/Sub-Sector 옵션 목록 (드롭다운용)

    GET /admin/dashboard/news/sector-options/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from stocks.models import SP500Constituent
        from django.db.models import Count

        sectors = list(
            SP500Constituent.objects.filter(is_active=True)
            .values('sector')
            .annotate(count=Count('id'))
            .order_by('sector')
        )

        sub_sectors = list(
            SP500Constituent.objects.filter(is_active=True)
            .exclude(sub_sector='')
            .values('sub_sector', 'sector')
            .annotate(count=Count('id'))
            .order_by('sector', 'sub_sector')
        )

        return Response({
            'sectors': [
                {'value': s['sector'], 'count': s['count']}
                for s in sectors
            ],
            'sub_sectors': [
                {'value': s['sub_sector'], 'sector': s['sector'], 'count': s['count']}
                for s in sub_sectors
            ],
        })
