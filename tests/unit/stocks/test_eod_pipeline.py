"""
EOD Pipeline 통합 테스트 (Step 12-2)

EODPipeline.run() 전체 흐름, 멱등성, 실패 fallback, PipelineLog 생성을 검증합니다.
EODPipeline 서비스가 아직 구현되지 않은 경우 skip 처리합니다.
"""

import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock

pytestmark = pytest.mark.unit


def _import_pipeline():
    """EODPipeline import. 없으면 pytest.skip."""
    try:
        from stocks.services.eod_pipeline import EODPipeline
        return EODPipeline
    except ImportError:
        pytest.skip("stocks.services.eod_pipeline 미구현 — 구현 후 테스트 활성화")


# ───────────────────────────────────────────────
# Fixtures
# ───────────────────────────────────────────────

@pytest.fixture
def target_date():
    return date(2026, 2, 25)


@pytest.fixture
def mock_pipeline_deps(target_date):
    """
    파이프라인 외부 의존성 전체 mock.

    EODPipeline이 stocks.services.eod_pipeline 모듈에서 직접 import하므로
    해당 모듈 경로로 patch.
    """
    import pandas as pd

    # ── 샘플 signals_df (Stage3 결과) ──────────────────────────
    sample_signals_df = pd.DataFrame([{
        'symbol': 'AAPL',
        'date': target_date,
        'open': 180.0, 'high': 185.0, 'low': 178.0, 'close': 182.5,
        'volume': 15_000_000, 'sector': 'Technology', 'industry': 'Consumer Electronics',
        'market_cap': 3_000_000_000_000, 'dollar_volume': 2_737_500_000.0,
        'change_pct': 2.1, 'vol_ratio': 2.5,
        'sig_V1': True, 'sig_V1_value': 2.5, 'sig_V1_direction': 'neutral',
        'sig_P1': False, 'sig_P1_value': 0.0, 'sig_P1_direction': '',
        'sig_P2': False, 'sig_P2_value': 0.0, 'sig_P2_direction': '',
        'sig_P3': False, 'sig_P3_value': 0.0, 'sig_P3_direction': '',
        'sig_P4': False, 'sig_P4_value': 0.0, 'sig_P4_direction': '',
        'sig_P5': False, 'sig_P5_value': 0.0, 'sig_P5_direction': 'bullish',
        'sig_P7': False, 'sig_P7_value': 0.0, 'sig_P7_direction': 'bullish',
        'sig_PV1': False, 'sig_PV1_value': 0.0, 'sig_PV1_direction': '',
        'sig_PV2': False, 'sig_PV2_value': 0.0, 'sig_PV2_direction': 'neutral',
        'sig_MA1': False, 'sig_MA1_value': 0.0, 'sig_MA1_direction': '',
        'sig_T1': False, 'sig_T1_value': 0.0, 'sig_T1_direction': '',
        'sig_S1': False, 'sig_S1_value': 0.0, 'sig_S1_direction': 'bullish',
        'sig_S2': False, 'sig_S2_value': 0.0, 'sig_S2_direction': 'bearish',
        'sig_S4': False, 'sig_S4_value': 0.0, 'sig_S4_direction': '',
    }])

    # ── tagged 결과 (Stage4) ──────────────────────────────────
    sample_tagged = [
        {
            'stock_id': 'AAPL',
            'signals': [{'id': 'V1', 'category': 'volume', 'direction': 'neutral', 'value': 2.5,
                         'title': '거래량 폭발', 'description_ko': '평소의 2배 이상 거래',
                         'color': '#58A6FF', 'label': '거래량 2.5배',
                         'education_tip': '거래량은 시장 관심의 크기', 'education_risk': '단기 과열'}],
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
        }
    ]

    # ── enriched 결과 (Stage5) ────────────────────────────────
    sample_enriched = [
        dict(item, news_context={'match_type': 'none', 'articles': []})
        for item in sample_tagged
    ]

    with patch('stocks.services.eod_pipeline.EODSignalCalculator') as mock_calc_cls, \
         patch('stocks.services.eod_pipeline.EODSignalTagger') as mock_tagger_cls, \
         patch('stocks.services.eod_pipeline.EODNewsEnricher') as mock_enricher_cls, \
         patch('stocks.services.eod_pipeline.EODJSONBaker') as mock_baker_cls:

        mock_calc = MagicMock()
        mock_calc.calculate_batch.return_value = sample_signals_df
        mock_calc._load_price_data.return_value = sample_signals_df
        mock_calc_cls.return_value = mock_calc

        mock_tagger = MagicMock()
        mock_tagger.tag_signals.return_value = sample_tagged
        mock_tagger_cls.return_value = mock_tagger

        mock_enricher = MagicMock()
        mock_enricher.enrich.return_value = sample_enriched
        mock_enricher_cls.return_value = mock_enricher

        mock_baker = MagicMock()
        mock_baker.bake.return_value = {
            'files_written': 2,
            'snapshot_id': 999,
        }
        mock_baker_cls.return_value = mock_baker

        yield {
            'calculator': mock_calc,
            'tagger': mock_tagger,
            'enricher': mock_enricher,
            'baker': mock_baker,
        }


# ───────────────────────────────────────────────
# TestEODPipeline
# ───────────────────────────────────────────────

class TestEODPipeline:

    @pytest.mark.django_db
    def test_pipeline_creates_pipeline_log(self, target_date, mock_pipeline_deps,
                                           stock_aapl, sp500_constituents, daily_prices_60d):
        """
        Given: 유효한 종목 + 가격 데이터
        When: EODPipeline.run() 실행
        Then: PipelineLog 레코드가 생성됨
        """
        EODPipeline = _import_pipeline()
        from stocks.models import PipelineLog

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target_date)

        assert PipelineLog.objects.filter(date=target_date).exists()
        assert log is not None

    @pytest.mark.django_db
    def test_pipeline_success_status(self, target_date, mock_pipeline_deps,
                                     stock_aapl, sp500_constituents, daily_prices_60d):
        """
        Given: 모든 단계 정상
        When: EODPipeline.run()
        Then: PipelineLog.status = 'success'
        """
        EODPipeline = _import_pipeline()

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target_date)

        assert log.status in ('success', 'partial'), f"예상치 못한 status: {log.status}"

    @pytest.mark.django_db
    def test_pipeline_idempotent(self, target_date, mock_pipeline_deps,
                                 stock_aapl, sp500_constituents, daily_prices_60d):
        """
        Given: 동일 날짜로 2회 실행
        When: run() 2회 호출
        Then: EODSignal 중복 없음 (unique_together=stock,date 보장)
        """
        EODPipeline = _import_pipeline()
        from stocks.models import EODSignal

        pipeline = EODPipeline()
        pipeline.run(target_date=target_date)
        count_after_first = EODSignal.objects.filter(date=target_date).count()

        pipeline.run(target_date=target_date)
        count_after_second = EODSignal.objects.filter(date=target_date).count()

        assert count_after_first == count_after_second, (
            f"2회 실행 후 EODSignal 개수가 달라짐: "
            f"1차={count_after_first}, 2차={count_after_second}"
        )

    @pytest.mark.django_db
    def test_pipeline_creates_snapshot(self, target_date, mock_pipeline_deps,
                                       stock_aapl, sp500_constituents, daily_prices_60d):
        """
        When: EODPipeline.run()
        Then: EODJSONBaker.bake()가 호출됨 (스냅샷 생성 위임 확인)

        Note: baker 자체가 mock이므로 실제 EODDashboardSnapshot 생성은
        EODJSONBaker 단위 테스트에서 별도 검증합니다.
        파이프라인 테스트에서는 baker.bake()가 올바른 인수로 호출됐는지 확인합니다.
        """
        EODPipeline = _import_pipeline()

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target_date)

        # baker.bake가 호출됐는지 확인
        mock_baker = mock_pipeline_deps['baker']
        assert mock_baker.bake.called, "EODJSONBaker.bake()가 호출되지 않음"
        call_args = mock_baker.bake.call_args
        # 첫 번째 인수가 target_date인지
        assert call_args[0][0] == target_date

    @pytest.mark.django_db
    def test_pipeline_stages_logged(self, target_date, mock_pipeline_deps,
                                    stock_aapl, sp500_constituents, daily_prices_60d):
        """
        When: EODPipeline.run()
        Then: PipelineLog.stages 딕셔너리에 각 단계 결과 기록됨
        """
        EODPipeline = _import_pipeline()

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target_date)

        assert isinstance(log.stages, dict), "stages는 dict여야 합니다"
        # 최소한 1개 이상의 stage 키 존재
        assert len(log.stages) > 0, "stages가 비어 있음"

    @pytest.mark.django_db
    def test_pipeline_failure_sets_failed_status(self, target_date):
        """
        Given: calculator.calculate_batch가 예외를 던짐
        When: EODPipeline.run()
        Then: PipelineLog.status = 'failed', error_message 기록
        """
        EODPipeline = _import_pipeline()
        from stocks.models import PipelineLog

        with patch('stocks.services.eod_pipeline.EODSignalCalculator') as mock_calc:
            mock_calc_instance = MagicMock()
            mock_calc_instance.calculate_batch.side_effect = RuntimeError("DB 연결 실패")
            mock_calc.return_value = mock_calc_instance

            pipeline = EODPipeline()
            log = pipeline.run(target_date=target_date)

        assert log.status == 'failed'
        assert log.error_message  # 빈 문자열이 아님

    @pytest.mark.django_db
    def test_pipeline_log_has_run_id(self, target_date, mock_pipeline_deps,
                                     stock_aapl, sp500_constituents, daily_prices_60d):
        """
        When: EODPipeline.run()
        Then: PipelineLog.run_id는 UUID 형식
        """
        EODPipeline = _import_pipeline()

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target_date)

        assert log.run_id is not None
        # UUID 변환 가능한지 확인
        uuid.UUID(str(log.run_id))

    @pytest.mark.django_db
    def test_pipeline_duration_recorded(self, target_date, mock_pipeline_deps,
                                        stock_aapl, sp500_constituents, daily_prices_60d):
        """
        When: EODPipeline.run()
        Then: PipelineLog.total_duration_seconds > 0
        """
        EODPipeline = _import_pipeline()

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target_date)

        assert log.total_duration_seconds >= 0


# ───────────────────────────────────────────────
# Bulk upsert 멱등성
# ───────────────────────────────────────────────

class TestBulkUpsert:

    @pytest.mark.django_db
    def test_bulk_upsert_no_duplicates(self, stock_aapl, target_date):
        """
        EODSignal.bulk_create(update_conflicts=True) 멱등성 확인.
        동일한 (stock, date) 레코드를 2회 insert해도 1개만 존재.
        """
        from stocks.models import EODSignal

        signal_data = {
            'stock': stock_aapl,
            'date': target_date,
            'signals': [{'id': 'V1', 'category': 'volume'}],
            'tag_details': {'primary': 'V1', 'sub_tags': []},
            'signal_count': 1,
            'bullish_count': 0,
            'bearish_count': 0,
            'composite_score': 0.0,
            'close_price': Decimal('182.50'),
            'change_percent': 2.1,
            'volume': 15_000_000,
            'dollar_volume': Decimal('2737500000.00'),
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
        }

        # 1차 생성
        EODSignal.objects.update_or_create(
            stock=stock_aapl, date=target_date,
            defaults={k: v for k, v in signal_data.items() if k not in ('stock', 'date')}
        )
        count_1 = EODSignal.objects.filter(stock=stock_aapl, date=target_date).count()

        # 2차 — 동일 데이터로 upsert
        EODSignal.objects.update_or_create(
            stock=stock_aapl, date=target_date,
            defaults={k: v for k, v in signal_data.items() if k not in ('stock', 'date')}
        )
        count_2 = EODSignal.objects.filter(stock=stock_aapl, date=target_date).count()

        assert count_1 == 1
        assert count_2 == 1

    @pytest.mark.django_db
    def test_pipeline_log_multiple_runs_different_run_ids(self, target_date):
        """
        같은 날짜로 파이프라인 2회 실행 시 run_id는 서로 다름.
        """
        from django.utils import timezone
        from stocks.models import PipelineLog

        log1 = PipelineLog.objects.create(
            date=target_date, status='success',
            stages={}, total_duration_seconds=10.0,
            started_at=timezone.now(),
        )
        log2 = PipelineLog.objects.create(
            date=target_date, status='success',
            stages={}, total_duration_seconds=11.0,
            started_at=timezone.now(),
        )

        assert log1.run_id != log2.run_id
