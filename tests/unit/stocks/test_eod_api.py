"""
EOD Dashboard API 엔드포인트 테스트 (Step 12-4)

GET /api/v1/stocks/eod/dashboard/
GET /api/v1/stocks/eod/signal/<signal_id>/
GET /api/v1/stocks/eod/pipeline/status/
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.unit


# ───────────────────────────────────────────────
# Fixtures
# ───────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def target_date():
    return date(2026, 2, 25)


@pytest.fixture
def dashboard_snapshot(db, target_date):
    """EODDashboardSnapshot DB 레코드"""
    from stocks.models import EODDashboardSnapshot

    json_data = {
        'date': str(target_date),
        'stocks': [
            {
                'stock_id': 'AAPL',
                'signals': [{'id': 'V1', 'category': 'volume', 'direction': 'neutral', 'value': 2.5}],
                'tag_details': {'primary': 'V1', 'sub_tags': []},
                'signal_count': 1,
                'bullish_count': 0,
                'bearish_count': 0,
                'composite_score': 0.0,
                'close': 182.5,
                'change_pct': 2.1,
                'volume': 15_000_000,
                'dollar_volume': 2_737_500_000.0,
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'market_cap': 3_000_000_000_000,
            },
            {
                'stock_id': 'NVDA',
                'signals': [
                    {'id': 'P2', 'category': 'momentum', 'direction': 'bullish', 'value': 6.1},
                    {'id': 'V1', 'category': 'volume', 'direction': 'neutral', 'value': 3.2},
                ],
                'tag_details': {'primary': 'V1', 'sub_tags': ['P2']},
                'signal_count': 2,
                'bullish_count': 1,
                'bearish_count': 0,
                'composite_score': 0.5,
                'close': 148.7,
                'change_pct': 6.1,
                'volume': 45_000_000,
                'dollar_volume': 6_691_500_000.0,
                'sector': 'Technology',
                'industry': 'Semiconductors',
                'market_cap': 2_000_000_000_000,
            },
        ],
        'summary': {
            'total_stocks': 2,
            'total_signals': 3,
            'signal_distribution': {'V1': 2, 'P2': 1},
        },
    }

    return EODDashboardSnapshot.objects.create(
        date=target_date,
        json_data=json_data,
        total_signals=3,
        total_stocks=2,
        signal_distribution={'V1': 2, 'P2': 1},
        generated_at=timezone.now(),
        pipeline_duration_seconds=45.0,
    )


@pytest.fixture
def eod_signal_v1(db, target_date):
    """V1 시그널을 가진 EODSignal 레코드 (AAPL)"""
    from stocks.models import Stock, EODSignal

    stock = Stock.objects.create(
        symbol='AAPL',
        stock_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        exchange='NASDAQ',
        market_capitalization=Decimal('3000000000000'),
    )

    return EODSignal.objects.create(
        stock=stock,
        date=target_date,
        signals=[{'id': 'V1', 'category': 'volume', 'direction': 'neutral', 'value': 2.5}],
        tag_details={'primary': 'V1', 'sub_tags': []},
        signal_count=1,
        bullish_count=0,
        bearish_count=0,
        composite_score=0.0,
        close_price=Decimal('182.50'),
        change_percent=2.1,
        volume=15_000_000,
        dollar_volume=Decimal('2737500000.00'),
        sector='Technology',
        industry='Consumer Electronics',
        market_cap=3_000_000_000_000,
        news_context={'match_type': 'none', 'articles': []},
    )


@pytest.fixture
def pipeline_logs(db, target_date):
    """최근 3일치 PipelineLog 레코드"""
    from stocks.models import PipelineLog

    logs = []
    for i in range(3):
        d = target_date - timedelta(days=i)
        logs.append(PipelineLog.objects.create(
            date=d,
            status='success',
            stages={
                'ingest': {'count': 500 - i * 2, 'degrade_mode': False},
                'calculate': {'duration_s': 12.0},
                'tag': {'count': 490 - i * 2},
                'persist': {'upserted': 490 - i * 2},
            },
            ingest_quality={
                'total_received': 500 - i * 2,
                'sector_null_pct': 1.2,
                'volume_zero_pct': 0.4,
                'degrade_mode': False,
                'warnings': [],
            },
            total_duration_seconds=43.0 + i,
            started_at=timezone.now(),
            completed_at=timezone.now(),
        ))
    return logs


# ───────────────────────────────────────────────
# TestEODDashboardAPI
# ───────────────────────────────────────────────

class TestEODDashboardAPI:

    @pytest.mark.django_db
    def test_dashboard_with_snapshot_returns_200(self, client, dashboard_snapshot, target_date):
        """
        Given: target_date의 EODDashboardSnapshot 존재
        When: GET /api/v1/stocks/eod/dashboard/?date=2026-02-25
        Then: 200 OK + json_data 반환
        """
        url = '/api/v1/stocks/eod/dashboard/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 200
        data = response.json()
        assert data['date'] == str(target_date)
        assert 'stocks' in data
        assert len(data['stocks']) == 2

    @pytest.mark.django_db
    def test_dashboard_no_snapshot_returns_404(self, client, target_date):
        """
        Given: 해당 날짜의 스냅샷 없음
        When: GET /api/v1/stocks/eod/dashboard/?date=2026-02-25
        Then: 404 Not Found
        """
        url = '/api/v1/stocks/eod/dashboard/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 404
        assert 'error' in response.json()

    @pytest.mark.django_db
    def test_dashboard_invalid_date_returns_400(self, client):
        """
        Given: 잘못된 날짜 형식
        When: GET /api/v1/stocks/eod/dashboard/?date=2026/02/25
        Then: 400 Bad Request
        """
        url = '/api/v1/stocks/eod/dashboard/'
        response = client.get(url, {'date': '2026/02/25'})

        assert response.status_code == 400
        assert 'error' in response.json()

    @pytest.mark.django_db
    def test_dashboard_returns_correct_json_structure(self, client, dashboard_snapshot, target_date):
        """
        응답 JSON 구조 검증 (stocks 배열 + summary 포함)
        """
        url = '/api/v1/stocks/eod/dashboard/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 200
        data = response.json()

        # 구조 검증
        assert 'summary' in data
        assert data['summary']['total_stocks'] == 2
        assert data['summary']['total_signals'] == 3

        # 개별 종목 구조
        aapl = next((s for s in data['stocks'] if s['stock_id'] == 'AAPL'), None)
        assert aapl is not None
        assert 'signals' in aapl
        assert 'composite_score' in aapl

    @pytest.mark.django_db
    def test_dashboard_no_date_param_uses_today(self, client):
        """
        Given: date 파라미터 없이 요청
        When: GET /api/v1/stocks/eod/dashboard/
        Then: 오늘 날짜 기준으로 조회 (스냅샷 없으면 404)
        """
        url = '/api/v1/stocks/eod/dashboard/'
        response = client.get(url)

        # 오늘 날짜 스냅샷이 없으므로 404, 또는 스냅샷 있으면 200
        assert response.status_code in (200, 404)


# ───────────────────────────────────────────────
# TestEODSignalDetailAPI
# ───────────────────────────────────────────────

class TestEODSignalDetailAPI:

    @pytest.mark.django_db
    def test_signal_detail_returns_200(self, client, eod_signal_v1, target_date):
        """
        Given: V1 시그널을 가진 EODSignal 존재
        When: GET /api/v1/stocks/eod/signal/V1/?date=2026-02-25
        Then: 200 OK + 해당 종목 포함
        """
        url = '/api/v1/stocks/eod/signal/V1/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 200
        data = response.json()
        assert data['signal_id'] == 'V1'
        assert data['count'] >= 1
        assert any(s['symbol'] == 'AAPL' for s in data['stocks'])

    @pytest.mark.django_db
    def test_signal_detail_empty_returns_200_with_zero_count(self, client, target_date):
        """
        Given: 해당 날짜에 MA1 시그널 없음
        When: GET /api/v1/stocks/eod/signal/MA1/?date=2026-02-25
        Then: 200 OK, count=0
        """
        url = '/api/v1/stocks/eod/signal/MA1/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert data['stocks'] == []

    @pytest.mark.django_db
    def test_signal_detail_response_structure(self, client, eod_signal_v1, target_date):
        """
        응답 필드 구조 검증.
        """
        url = '/api/v1/stocks/eod/signal/V1/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 200
        data = response.json()

        assert 'signal_id' in data
        assert 'date' in data
        assert 'count' in data
        assert 'stocks' in data

        if data['stocks']:
            stock = data['stocks'][0]
            required_fields = [
                'symbol', 'signals', 'tag_details',
                'close_price', 'change_percent', 'volume',
                'composite_score', 'signal_count',
            ]
            for field in required_fields:
                assert field in stock, f"필드 누락: {field}"

    @pytest.mark.django_db
    def test_signal_detail_invalid_date_returns_400(self, client):
        """
        잘못된 날짜 형식 → 400
        """
        url = '/api/v1/stocks/eod/signal/V1/'
        response = client.get(url, {'date': 'invalid-date'})

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_signal_detail_no_date_uses_today(self, client):
        """
        date 파라미터 없으면 오늘 날짜로 조회.
        """
        url = '/api/v1/stocks/eod/signal/V1/'
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert 'date' in data

    @pytest.mark.django_db
    def test_signal_detail_returns_at_most_50_stocks(self, client, target_date):
        """
        EODSignal 60개 생성 → API 응답은 최대 50개만 반환.
        """
        from stocks.models import Stock, EODSignal

        stocks_created = []
        for i in range(60):
            sym = f'SYM{i:03d}'
            s = Stock.objects.create(
                symbol=sym,
                stock_name=f'Stock {i}',
                sector='Technology',
            )
            stocks_created.append(s)
            EODSignal.objects.create(
                stock=s,
                date=target_date,
                signals=[{'id': 'T1', 'category': 'technical', 'direction': 'bullish', 'value': 25.0}],
                tag_details={'primary': 'T1', 'sub_tags': []},
                signal_count=1,
                bullish_count=1,
                bearish_count=0,
                composite_score=float(i) / 60,
                close_price=Decimal('100.00'),
                change_percent=1.0,
                volume=1_000_000,
                dollar_volume=Decimal('100000000.00'),
                sector='Technology',
            )

        url = '/api/v1/stocks/eod/signal/T1/'
        response = client.get(url, {'date': str(target_date)})

        assert response.status_code == 200
        data = response.json()
        assert data['count'] <= 50


# ───────────────────────────────────────────────
# TestEODPipelineStatusAPI
# ───────────────────────────────────────────────

class TestEODPipelineStatusAPI:

    @pytest.mark.django_db
    def test_pipeline_status_returns_200(self, client, pipeline_logs):
        """
        Given: PipelineLog 레코드 존재
        When: GET /api/v1/stocks/eod/pipeline/status/
        Then: 200 OK + logs 배열 반환
        """
        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert 'logs' in data
        assert len(data['logs']) > 0

    @pytest.mark.django_db
    def test_pipeline_status_no_logs_returns_empty(self, client):
        """
        Given: PipelineLog 레코드 없음
        When: GET /api/v1/stocks/eod/pipeline/status/
        Then: 200 OK, logs=[]
        """
        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['logs'] == []

    @pytest.mark.django_db
    def test_pipeline_status_response_structure(self, client, pipeline_logs):
        """
        응답의 각 로그 항목 구조 검증.
        """
        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data['logs']) > 0

        log_entry = data['logs'][0]
        required_fields = [
            'date', 'run_id', 'status',
            'stages', 'ingest_quality',
            'total_duration_seconds', 'error_message',
        ]
        for field in required_fields:
            assert field in log_entry, f"필드 누락: {field}"

    @pytest.mark.django_db
    def test_pipeline_status_ordered_by_date_desc(self, client, pipeline_logs, target_date):
        """
        응답 로그가 날짜 내림차순으로 정렬됨.
        """
        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        assert response.status_code == 200
        dates = [entry['date'] for entry in response.json()['logs']]

        # 날짜가 내림차순인지 확인
        assert dates == sorted(dates, reverse=True), f"날짜 정렬 오류: {dates}"

    @pytest.mark.django_db
    def test_pipeline_status_returns_at_most_7_logs(self, client, target_date):
        """
        10개의 로그가 있어도 최대 7개만 반환.
        """
        from stocks.models import PipelineLog

        for i in range(10):
            d = target_date - timedelta(days=i)
            PipelineLog.objects.create(
                date=d,
                status='success',
                stages={},
                total_duration_seconds=10.0,
                started_at=timezone.now(),
            )

        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.json()['logs']) <= 7

    @pytest.mark.django_db
    def test_pipeline_status_log_run_id_is_string(self, client, pipeline_logs):
        """
        run_id가 문자열로 직렬화됨 (UUID → str).
        """
        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        data = response.json()
        for log_entry in data['logs']:
            assert isinstance(log_entry['run_id'], str)
            # UUID 형식인지 검증
            import uuid
            uuid.UUID(log_entry['run_id'])

    @pytest.mark.django_db
    def test_pipeline_status_failed_log_shows_error_message(self, client, target_date):
        """
        status=failed인 로그의 error_message가 응답에 포함됨.
        """
        from stocks.models import PipelineLog

        PipelineLog.objects.create(
            date=target_date,
            status='failed',
            stages={},
            error_message='DB 연결 실패: connection refused',
            total_duration_seconds=2.0,
            started_at=timezone.now(),
        )

        url = '/api/v1/stocks/eod/pipeline/status/'
        response = client.get(url)

        assert response.status_code == 200
        logs = response.json()['logs']
        failed = next((l for l in logs if l['status'] == 'failed'), None)
        assert failed is not None
        assert 'DB 연결 실패' in failed['error_message']


# ───────────────────────────────────────────────
# TestEODDashboardSnapshotModel (모델 직접 검증)
# ───────────────────────────────────────────────

class TestEODDashboardSnapshotModel:

    @pytest.mark.django_db
    def test_snapshot_unique_per_date(self, target_date, dashboard_snapshot):
        """
        동일 날짜에 스냅샷 2개 생성 시 IntegrityError 발생.
        """
        from django.db import IntegrityError
        from stocks.models import EODDashboardSnapshot

        with pytest.raises(IntegrityError):
            EODDashboardSnapshot.objects.create(
                date=target_date,  # 이미 존재
                json_data={'date': str(target_date), 'stocks': []},
                total_signals=0,
                total_stocks=0,
                signal_distribution={},
                generated_at=timezone.now(),
                pipeline_duration_seconds=1.0,
            )

    @pytest.mark.django_db
    def test_snapshot_str_representation(self, dashboard_snapshot, target_date):
        """
        __str__ 반환값 검증.
        """
        s = str(dashboard_snapshot)
        assert str(target_date) in s


# ───────────────────────────────────────────────
# TestEODSignalModel (모델 직접 검증)
# ───────────────────────────────────────────────

class TestEODSignalModel:

    @pytest.mark.django_db
    def test_eod_signal_unique_per_stock_date(self, eod_signal_v1, target_date):
        """
        (stock, date) unique_together 제약 검증.
        """
        from django.db import IntegrityError
        from stocks.models import EODSignal

        with pytest.raises(IntegrityError):
            EODSignal.objects.create(
                stock=eod_signal_v1.stock,
                date=target_date,   # 동일 (stock, date)
                signals=[],
                tag_details={},
                close_price=Decimal('100.00'),
                change_percent=0.0,
                volume=0,
                dollar_volume=Decimal('0'),
            )

    @pytest.mark.django_db
    def test_eod_signal_str_representation(self, eod_signal_v1):
        """
        __str__ 반환값 검증.
        """
        s = str(eod_signal_v1)
        assert 'AAPL' in s
        assert '2026-02-25' in s
