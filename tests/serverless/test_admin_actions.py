"""
Admin Dashboard Actions API 테스트

AdminActionView, AdminTaskStatusView, _suggest_action 헬퍼를 검증합니다.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status as http_status
from django.contrib.auth import get_user_model
from django.core.cache import cache

from serverless.models import AdminActionLog
from serverless.services.admin_status_service import _suggest_action

User = get_user_model()


class TestAdminActionView:
    """AdminActionView 테스트 (GET/POST)"""

    @pytest.fixture
    def api_client(self):
        """API 클라이언트"""
        return APIClient()

    @pytest.fixture
    @pytest.mark.django_db
    def admin_user(self):
        """관리자 사용자"""
        return User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

    @pytest.fixture
    @pytest.mark.django_db
    def normal_user(self):
        """일반 사용자"""
        return User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123'
        )

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """각 테스트 전후 캐시 초기화"""
        cache.clear()
        yield
        cache.clear()

    # ========================================
    # GET /admin/dashboard/actions/ 테스트
    # ========================================

    @pytest.mark.django_db
    def test_get_actions_list_success(self, api_client, admin_user):
        """GET: 사용 가능한 액션 목록 반환"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/')

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert 'actions' in data
        actions = data['actions']

        # 주요 액션 존재 확인
        assert 'sync_eod_prices' in actions
        assert 'sync_movers' in actions
        assert 'generate_keywords' in actions
        assert 'sync_financials_bulk' in actions

        # 액션 필드 확인
        sync_eod = actions['sync_eod_prices']
        assert sync_eod['label'] == 'EOD 가격 동기화'
        assert sync_eod['dangerous'] is False
        assert sync_eod['cooldown_seconds'] == 300
        assert sync_eod['cooldown_remaining'] == 0
        assert sync_eod['params'] == []
        assert sync_eod['required_params'] == []

        # 위험 액션 확인
        bulk_sync = actions['sync_financials_bulk']
        assert bulk_sync['dangerous'] is True
        assert 'cost_estimate' in bulk_sync

    @pytest.mark.django_db
    def test_get_actions_list_with_cooldown(self, api_client, admin_user):
        """GET: 쿨다운 잔여시간 포함"""
        # 쿨다운 설정
        cooldown_key = 'admin_action_cooldown:sync_eod_prices'
        expiry_time = time.time() + 120  # 120초 남음
        cache.set(cooldown_key, expiry_time, timeout=120)

        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/')

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        actions = data['actions']

        sync_eod = actions['sync_eod_prices']
        # 쿨다운 잔여시간이 100초 이상 남아있어야 함
        assert sync_eod['cooldown_remaining'] >= 100

    @pytest.mark.django_db
    def test_get_actions_list_forbidden_for_normal_user(self, api_client, normal_user):
        """GET: 일반 사용자 접근 금지 (403)"""
        api_client.force_authenticate(user=normal_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/')

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_get_actions_list_unauthorized(self, api_client):
        """GET: 비인증 사용자 접근 금지 (401)"""
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/')

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    # ========================================
    # POST /admin/dashboard/actions/ 테스트
    # ========================================

    @pytest.mark.django_db
    @patch('config.celery.app')
    def test_post_action_dispatch_success(self, mock_app, api_client, admin_user):
        """POST: 정상 액션 디스패치 (200 + task_id)"""
        # Mock send_task
        mock_result = MagicMock()
        mock_result.id = 'test-task-id-12345'
        mock_app.send_task.return_value = mock_result

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_eod_prices', 'params': {}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True
        assert data['data']['task_id'] == 'test-task-id-12345'
        assert data['data']['action'] == 'sync_eod_prices'
        assert data['data']['label'] == 'EOD 가격 동기화'
        assert '태스크가 시작되었습니다' in data['data']['message']

        # send_task 호출 확인
        mock_app.send_task.assert_called_once_with(
            'stocks.tasks.sync_sp500_eod_prices',
            kwargs={}
        )

        # AdminActionLog 생성 확인
        log = AdminActionLog.objects.get(task_id='test-task-id-12345')
        assert log.action == 'sync_eod_prices'
        assert log.label == 'EOD 가격 동기화'
        assert log.user == admin_user
        assert log.status == 'dispatched'

    @pytest.mark.django_db
    def test_post_action_unknown_action(self, api_client, admin_user):
        """POST: 알 수 없는 액션 (400)"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'invalid_action', 'params': {}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'Unknown action' in data['error']

    @pytest.mark.django_db
    def test_post_dangerous_action_without_confirm(self, api_client, admin_user):
        """POST: 위험 액션 confirm 없이 호출 (400 + requires_confirm)"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_financials_bulk', 'params': {}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'requires_confirm' in data
        assert data['requires_confirm'] is True
        assert 'cost_estimate' in data
        assert 'confirm: true' in data['error']

    @pytest.mark.django_db
    @patch('config.celery.app')
    def test_post_dangerous_action_with_confirm(self, mock_app, api_client, admin_user):
        """POST: 위험 액션 confirm=true 시 정상 실행 (200)"""
        mock_result = MagicMock()
        mock_result.id = 'test-bulk-task-id'
        mock_app.send_task.return_value = mock_result

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_financials_bulk', 'params': {}, 'confirm': True},
            format='json'
        )

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True
        assert data['data']['task_id'] == 'test-bulk-task-id'

        # send_task 호출 확인
        mock_app.send_task.assert_called_once_with(
            'stocks.tasks.bulk_sync_sp500_financials',
            kwargs={}
        )

    @pytest.mark.django_db
    def test_post_action_missing_required_param(self, api_client, admin_user):
        """POST: 필수 파라미터 누락 (400)"""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_single_financials', 'params': {}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert '필수 파라미터 누락' in data['error']
        assert 'symbol' in data['error']

    @pytest.mark.django_db
    @patch('config.celery.app')
    def test_post_action_with_params(self, mock_app, api_client, admin_user):
        """POST: 파라미터 포함 액션 (symbol 전달)"""
        mock_result = MagicMock()
        mock_result.id = 'test-task-with-params'
        mock_app.send_task.return_value = mock_result

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_single_financials', 'params': {'symbol': 'AAPL'}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True

        # send_task에 symbol 파라미터 전달 확인
        mock_app.send_task.assert_called_once_with(
            'stocks.tasks.update_financials_with_provider',
            kwargs={'symbol': 'AAPL'}
        )

        # AdminActionLog에 params 저장 확인
        log = AdminActionLog.objects.get(task_id='test-task-with-params')
        assert log.params == {'symbol': 'AAPL'}

    @pytest.mark.django_db
    @patch('config.celery.app')
    def test_post_action_cooldown_check(self, mock_app, api_client, admin_user):
        """POST: 쿨다운 중 재호출 (429 + cooldown_remaining)"""
        mock_result = MagicMock()
        mock_result.id = 'test-task-1'
        mock_app.send_task.return_value = mock_result

        api_client.force_authenticate(user=admin_user)

        # 첫 번째 호출 (성공)
        response1 = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_eod_prices', 'params': {}},
            format='json'
        )
        assert response1.status_code == http_status.HTTP_200_OK

        # 두 번째 호출 (쿨다운)
        response2 = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_eod_prices', 'params': {}},
            format='json'
        )
        assert response2.status_code == http_status.HTTP_429_TOO_MANY_REQUESTS
        data = response2.json()
        assert '쿨다운 중입니다' in data['error']
        assert 'cooldown_remaining' in data
        assert data['cooldown_remaining'] > 0

    @pytest.mark.django_db
    @patch('config.celery.app')
    def test_post_action_dispatch_error_rollback_cooldown(self, mock_app, api_client, admin_user):
        """POST: send_task 실패 시 쿨다운 롤백 (500)"""
        # send_task 예외 발생
        mock_app.send_task.side_effect = Exception('Celery connection error')

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_eod_prices', 'params': {}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert '태스크 디스패치 실패' in data['error']

        # 쿨다운 롤백 확인 (두 번째 호출 시 쿨다운 없어야 함)
        mock_app.send_task.reset_mock()
        mock_app.send_task.side_effect = None
        mock_result = MagicMock()
        mock_result.id = 'test-task-2'
        mock_app.send_task.return_value = mock_result

        response2 = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_eod_prices', 'params': {}},
            format='json'
        )
        # 쿨다운이 롤백되었으므로 성공해야 함
        assert response2.status_code == http_status.HTTP_200_OK

    @pytest.mark.django_db
    def test_post_action_forbidden_for_normal_user(self, api_client, normal_user):
        """POST: 일반 사용자 접근 금지 (403)"""
        api_client.force_authenticate(user=normal_user)
        response = api_client.post(
            '/api/v1/serverless/admin/dashboard/actions/',
            {'action': 'sync_eod_prices', 'params': {}},
            format='json'
        )

        assert response.status_code == http_status.HTTP_403_FORBIDDEN


class TestAdminTaskStatusView:
    """AdminTaskStatusView 테스트 (GET)"""

    @pytest.fixture
    def api_client(self):
        """API 클라이언트"""
        return APIClient()

    @pytest.fixture
    @pytest.mark.django_db
    def admin_user(self):
        """관리자 사용자"""
        return User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

    # ========================================
    # GET /admin/dashboard/actions/status/<task_id>/ 테스트
    # ========================================

    @pytest.mark.django_db
    @patch('django_celery_results.models.TaskResult')
    def test_get_task_status_success_from_db(self, mock_task_result_model, api_client, admin_user):
        """GET: TaskResult DB에서 성공 상태 반환"""
        # Mock TaskResult 인스턴스
        mock_task = MagicMock()
        mock_task.task_id = 'test-task-123'
        mock_task.status = 'SUCCESS'
        mock_task.result = '{"synced": 50, "failed": 0}'
        mock_task.date_done = MagicMock()
        mock_task.date_done.isoformat.return_value = '2026-02-23T10:00:00'
        mock_task.traceback = None

        # Mock TaskResult.objects.get
        mock_task_result_model.objects.get.return_value = mock_task

        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/status/test-task-123/')

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['task_id'] == 'test-task-123'
        assert data['status'] == 'SUCCESS'
        assert data['result'] == '{"synced": 50, "failed": 0}'
        assert data['date_done'] == '2026-02-23T10:00:00'
        assert data['traceback'] is None

    @pytest.mark.django_db
    @patch('django_celery_results.models.TaskResult')
    def test_get_task_status_updates_admin_log(self, mock_task_result_model, api_client, admin_user):
        """GET: TaskResult 조회 시 AdminActionLog 업데이트"""
        # AdminActionLog 생성
        AdminActionLog.objects.create(
            action='sync_eod_prices',
            label='EOD 가격 동기화',
            user=admin_user,
            params={},
            task_id='test-task-456',
            status='dispatched'
        )

        # Mock TaskResult
        mock_task = MagicMock()
        mock_task.task_id = 'test-task-456'
        mock_task.status = 'SUCCESS'
        mock_task.result = 'Done'
        mock_task.date_done = MagicMock()
        mock_task.date_done.isoformat.return_value = '2026-02-23T11:00:00'
        mock_task.traceback = None

        mock_task_result_model.objects.get.return_value = mock_task

        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/status/test-task-456/')

        assert response.status_code == http_status.HTTP_200_OK

        # AdminActionLog 업데이트 확인
        log = AdminActionLog.objects.get(task_id='test-task-456')
        assert log.status == 'success'
        assert log.result_summary == 'Done'

    @pytest.mark.django_db
    @patch('django_celery_results.models.TaskResult')
    def test_get_task_status_failure(self, mock_task_result_model, api_client, admin_user):
        """GET: 실패 태스크 상태 (traceback 포함)"""
        # AdminActionLog 생성
        AdminActionLog.objects.create(
            action='sync_movers',
            label='Market Movers 동기화',
            user=admin_user,
            params={},
            task_id='test-task-fail',
            status='dispatched'
        )

        # Mock TaskResult (FAILURE)
        mock_task = MagicMock()
        mock_task.task_id = 'test-task-fail'
        mock_task.status = 'FAILURE'
        mock_task.result = None
        mock_task.date_done = MagicMock()
        mock_task.date_done.isoformat.return_value = '2026-02-23T12:00:00'
        mock_task.traceback = 'Traceback (most recent call last):\n  File ...'

        mock_task_result_model.objects.get.return_value = mock_task

        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/status/test-task-fail/')

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['status'] == 'FAILURE'
        assert data['traceback'] == 'Traceback (most recent call last):\n  File ...'

        # AdminActionLog 업데이트 확인
        log = AdminActionLog.objects.get(task_id='test-task-fail')
        assert log.status == 'failure'

    @pytest.mark.django_db
    @patch('celery.result.AsyncResult')
    @patch('django_celery_results.models.TaskResult')
    def test_get_task_status_fallback_to_async_result(
        self, mock_task_result_model, mock_async_result_class, api_client, admin_user
    ):
        """GET: TaskResult 없을 시 AsyncResult fallback (PENDING/STARTED)"""
        # TaskResult.objects.get → DoesNotExist
        mock_task_result_model.DoesNotExist = Exception
        mock_task_result_model.objects.get.side_effect = mock_task_result_model.DoesNotExist

        # Mock AsyncResult
        mock_async_result = MagicMock()
        mock_async_result.state = 'PENDING'
        mock_async_result_class.return_value = mock_async_result

        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/status/test-task-pending/')

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['task_id'] == 'test-task-pending'
        assert data['status'] == 'PENDING'
        assert data['result'] is None
        assert data['date_done'] is None
        assert data['traceback'] is None

        mock_async_result_class.assert_called_once_with('test-task-pending')

    @pytest.mark.django_db
    @patch('celery.result.AsyncResult')
    @patch('django_celery_results.models.TaskResult')
    def test_get_task_status_unknown_on_error(
        self, mock_task_result_model, mock_async_result_class, api_client, admin_user
    ):
        """GET: TaskResult/AsyncResult 모두 실패 시 UNKNOWN 반환"""
        # TaskResult.objects.get → DoesNotExist
        mock_task_result_model.DoesNotExist = Exception
        mock_task_result_model.objects.get.side_effect = mock_task_result_model.DoesNotExist

        # AsyncResult → Exception
        mock_async_result_class.side_effect = Exception('Celery not available')

        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/serverless/admin/dashboard/actions/status/test-task-unknown/')

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()
        assert data['task_id'] == 'test-task-unknown'
        assert data['status'] == 'UNKNOWN'
        assert data['result'] is None


class TestSuggestActionHelper:
    """_suggest_action() 헬퍼 테스트"""

    def test_suggest_action_stocks_price_missing(self):
        """stocks 카테고리: 가격 누락 → sync_eod_prices"""
        issue = {
            'category': 'stocks',
            'title': 'SP500 가격 누락 15개',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'sync_eod_prices'

    def test_suggest_action_market_pulse_movers_zero(self):
        """market_pulse: MarketMover 0건 → sync_movers"""
        issue = {
            'category': 'market_pulse',
            'title': 'MarketMover 0건',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'sync_movers'

    def test_suggest_action_market_pulse_movers_incomplete(self):
        """market_pulse: MarketMover 불완전 → sync_movers"""
        issue = {
            'category': 'market_pulse',
            'title': 'MarketMover 불완전 (25건)',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'sync_movers'

    def test_suggest_action_market_pulse_keyword_failure(self):
        """market_pulse: 키워드 생성 실패 → generate_keywords"""
        issue = {
            'category': 'market_pulse',
            'title': '키워드 생성 실패 8건',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'generate_keywords'

    def test_suggest_action_screener_breadth(self):
        """screener: MarketBreadth 미생성 → sync_breadth"""
        issue = {
            'category': 'screener',
            'title': 'MarketBreadth 미생성',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'sync_breadth'

    def test_suggest_action_screener_sector_performance(self):
        """screener: SectorPerformance 부족 → sync_heatmap"""
        issue = {
            'category': 'screener',
            'title': 'SectorPerformance 8/11',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'sync_heatmap'

    def test_suggest_action_chain_sight_etf_error(self):
        """chain_sight: ETF 수집 오류 → sync_etf_holdings"""
        issue = {
            'category': 'chain_sight',
            'title': 'ETF 수집 오류 3개',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'sync_etf_holdings'

    def test_suggest_action_news_keywords(self):
        """news: 뉴스 키워드 미생성 → extract_news_keywords"""
        issue = {
            'category': 'news',
            'title': '뉴스 키워드 미생성',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action == 'extract_news_keywords'

    def test_suggest_action_no_match(self):
        """매핑 없는 이슈 → None"""
        issue = {
            'category': 'system',
            'title': '반복 실패: some.task',
            'detail': '...',
        }
        action = _suggest_action(issue)
        assert action is None

    def test_suggest_action_partial_title_match(self):
        """부분 매칭 (키워드 포함) → 정상 동작"""
        issue = {
            'category': 'screener',
            'title': '경고: MarketBreadth 데이터 없음',
            'detail': '...',
        }
        action = _suggest_action(issue)
        # 'MarketBreadth' 포함하므로 sync_breadth
        assert action == 'sync_breadth'
