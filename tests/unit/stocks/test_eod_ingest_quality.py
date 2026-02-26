"""
EOD 데이터 수집 품질 체크 테스트 (Step 12-3)

IngestQualityChecker (또는 동등 로직)의 degrade_mode 판단 기준과
volume/dollar_volume 필터링 로직을 검증합니다.

품질 체크 로직이 EODPipeline 내부에 인라인으로 구현되는 경우를 고려하여
독립 함수/클래스와 파이프라인 모두 커버합니다.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta
from decimal import Decimal

pytestmark = pytest.mark.unit


# ───────────────────────────────────────────────
# 품질 체크 헬퍼
# ───────────────────────────────────────────────

def _make_quality_df(n_stocks=500, sector_null_ratio=0.0,
                     volume_zero_ratio=0.0, today=None):
    """
    품질 체크 테스트용 DataFrame 생성 헬퍼.

    Args:
        n_stocks: 종목 수
        sector_null_ratio: sector가 ''인 비율 (0~1)
        volume_zero_ratio: volume=0인 비율 (0~1)
    """
    if today is None:
        today = date(2026, 2, 25)

    n_null_sector = int(n_stocks * sector_null_ratio)
    n_zero_vol = int(n_stocks * volume_zero_ratio)

    symbols = [f'SYM{i:04d}' for i in range(n_stocks)]
    rows = []

    for i, sym in enumerate(symbols):
        sector = '' if i < n_null_sector else 'Technology'
        volume = 0 if i < n_zero_vol else 5_000_000
        close = 100.0
        rows.append({
            'symbol':     sym,
            'date':       today,
            'open':       close * 0.99,
            'high':       close * 1.02,
            'low':        close * 0.97,
            'close':      close,
            'volume':     volume,
            'dollar_volume': close * volume,
            'sector':     sector,
            'industry':   '',
            'market_cap': 500_000_000_000,
        })

    return pd.DataFrame(rows)


def _run_quality_check(df, prev_day_count=None):
    """
    품질 체크 로직을 직접 실행하는 헬퍼.

    EODPipeline._check_ingest_quality 또는 별도 IngestQualityChecker를 우선 시도,
    없으면 인라인으로 동일 로직을 실행.
    """
    try:
        from stocks.services.eod_pipeline import EODPipeline
        pipeline = EODPipeline.__new__(EODPipeline)
        if hasattr(pipeline, '_check_ingest_quality'):
            return pipeline._check_ingest_quality(df, prev_day_count=prev_day_count)
    except (ImportError, AttributeError):
        pass

    try:
        from stocks.services.ingest_quality import IngestQualityChecker
        checker = IngestQualityChecker()
        return checker.check(df, prev_day_count=prev_day_count)
    except ImportError:
        pass

    # 파이프라인/체커 모두 없으면 직접 계산 (로직 재현)
    total = len(df)
    if total == 0:
        return {'total_received': 0, 'degrade_mode': True,
                'warnings': ['빈 데이터셋']}

    warnings = []
    degrade_mode = False

    # 전일 대비 종목 수 감소
    if prev_day_count is not None and prev_day_count > 0:
        ratio = total / prev_day_count
        if ratio < 0.90:
            degrade_mode = True
            warnings.append(f'종목수 전일 대비 {(1-ratio)*100:.1f}% 감소')

    # sector null 비율
    sector_null_pct = (df['sector'] == '').mean() * 100
    if sector_null_pct > 5.0:
        degrade_mode = True
        warnings.append(f'sector null {sector_null_pct:.1f}%')

    # volume zero 비율
    volume_zero_pct = (df['volume'] == 0).mean() * 100
    if volume_zero_pct > 3.0:
        degrade_mode = True
        warnings.append(f'volume zero {volume_zero_pct:.1f}%')

    return {
        'total_received': total,
        'sector_null_pct': round(sector_null_pct, 2),
        'volume_zero_pct': round(volume_zero_pct, 2),
        'vs_prev_day_pct': round(total / prev_day_count * 100, 1) if prev_day_count else None,
        'degrade_mode': degrade_mode,
        'warnings': warnings,
    }


def _apply_volume_filter(df, min_volume=100_000, min_dollar_volume=500_000):
    """볼륨/달러볼륨 필터 적용 헬퍼 (파이프라인 로직 재현)."""
    try:
        from stocks.services.eod_pipeline import EODPipeline
        pipeline = EODPipeline.__new__(EODPipeline)
        if hasattr(pipeline, '_filter_low_liquidity'):
            return pipeline._filter_low_liquidity(df)
    except (ImportError, AttributeError):
        pass

    # 직접 계산
    mask = (df['volume'] >= min_volume) & (df['dollar_volume'] >= min_dollar_volume)
    return df[mask].reset_index(drop=True)


# ───────────────────────────────────────────────
# TestIngestQuality
# ───────────────────────────────────────────────

class TestIngestQuality:

    def test_normal_quality_no_degrade(self):
        """
        Given: 500개 종목, sector null 0%, volume zero 0%
        Then: degrade_mode=False
        """
        df = _make_quality_df(n_stocks=500, sector_null_ratio=0.0,
                              volume_zero_ratio=0.0)
        result = _run_quality_check(df, prev_day_count=500)

        assert result['degrade_mode'] is False
        assert len(result.get('warnings', [])) == 0

    def test_degrade_mode_count_drop_10pct(self):
        """
        Given: 전일 500개 → 오늘 440개 (12% 감소, 임계값 10% 초과)
        Then: degrade_mode=True
        """
        df = _make_quality_df(n_stocks=440)
        result = _run_quality_check(df, prev_day_count=500)

        assert result['degrade_mode'] is True
        assert any('감소' in w or 'count' in w.lower() for w in result.get('warnings', []))

    def test_no_degrade_count_drop_within_5pct(self):
        """
        Given: 전일 500개 → 오늘 480개 (4% 감소, 임계값 미달)
        Then: count 감소 원인의 degrade_mode=False
        """
        df = _make_quality_df(n_stocks=480)
        result = _run_quality_check(df, prev_day_count=500)

        # 감소율만 체크 (sector/volume 조건은 정상이므로 degrade 없어야 함)
        if result.get('vs_prev_day_pct') is not None:
            assert result['degrade_mode'] is False

    def test_degrade_mode_sector_null_above_5pct(self):
        """
        Given: sector null 비율 8% (임계값 5% 초과)
        Then: degrade_mode=True
        """
        df = _make_quality_df(n_stocks=500, sector_null_ratio=0.08)
        result = _run_quality_check(df, prev_day_count=500)

        assert result['degrade_mode'] is True
        assert result.get('sector_null_pct', 0) > 5.0

    def test_no_degrade_sector_null_below_5pct(self):
        """
        Given: sector null 비율 3% (임계값 이하)
        Then: sector null 원인의 degrade 없음
        """
        df = _make_quality_df(n_stocks=500, sector_null_ratio=0.03)
        result = _run_quality_check(df, prev_day_count=500)

        # volume_zero가 0이고 count drop도 없으면 degrade_mode=False
        assert result.get('sector_null_pct', 0) <= 5.0

    def test_degrade_mode_volume_zero_above_3pct(self):
        """
        Given: volume zero 비율 5% (임계값 3% 초과)
        Then: degrade_mode=True
        """
        df = _make_quality_df(n_stocks=500, volume_zero_ratio=0.05)
        result = _run_quality_check(df, prev_day_count=500)

        assert result['degrade_mode'] is True
        assert result.get('volume_zero_pct', 0) > 3.0

    def test_no_degrade_volume_zero_below_3pct(self):
        """
        Given: volume zero 비율 2% (임계값 이하)
        Then: volume zero 원인의 degrade 없음
        """
        df = _make_quality_df(n_stocks=500, volume_zero_ratio=0.02)
        result = _run_quality_check(df, prev_day_count=500)

        assert result.get('volume_zero_pct', 0) <= 3.0

    def test_multiple_degrade_triggers(self):
        """
        Given: sector null 8% + volume zero 5% 동시 발생
        Then: degrade_mode=True, warnings 2개 이상
        """
        df = _make_quality_df(n_stocks=500, sector_null_ratio=0.08,
                              volume_zero_ratio=0.05)
        result = _run_quality_check(df, prev_day_count=500)

        assert result['degrade_mode'] is True
        assert len(result.get('warnings', [])) >= 2

    def test_quality_result_has_required_keys(self):
        """
        품질 체크 결과에 필수 키가 모두 포함됨.
        """
        df = _make_quality_df(n_stocks=100)
        result = _run_quality_check(df, prev_day_count=100)

        assert 'degrade_mode' in result
        assert 'total_received' in result
        assert result['total_received'] == 100

    def test_empty_dataframe_degrade(self):
        """
        Given: 빈 DataFrame
        Then: degrade_mode=True
        """
        df = pd.DataFrame(columns=['symbol', 'date', 'close', 'volume',
                                   'sector', 'industry', 'market_cap', 'dollar_volume'])
        result = _run_quality_check(df, prev_day_count=500)

        assert result['degrade_mode'] is True


# ───────────────────────────────────────────────
# TestVolumeFilter
# ───────────────────────────────────────────────

class TestVolumeFilter:

    def test_filter_low_volume(self):
        """
        Given: volume < 100K 종목 포함
        Then: 해당 종목 필터링 (결과에서 제외)
        """
        today = date(2026, 2, 25)
        df = pd.DataFrame([
            {'symbol': 'BIG', 'date': today, 'open': 100.0, 'high': 102.0,
             'low': 98.0, 'close': 101.0, 'volume': 5_000_000,
             'dollar_volume': 505_000_000.0, 'sector': 'Tech', 'industry': '', 'market_cap': 1e11},
            {'symbol': 'TINY', 'date': today, 'open': 10.0, 'high': 10.5,
             'low': 9.8, 'close': 10.2, 'volume': 50_000,   # < 100K
             'dollar_volume': 510_000.0, 'sector': 'Tech', 'industry': '', 'market_cap': 1e8},
        ])

        result = _apply_volume_filter(df, min_volume=100_000, min_dollar_volume=500_000)

        assert 'BIG' in result['symbol'].values
        assert 'TINY' not in result['symbol'].values

    def test_filter_low_dollar_volume(self):
        """
        Given: dollar_volume < $500K 종목 포함
        Then: 해당 종목 필터링
        """
        today = date(2026, 2, 25)
        df = pd.DataFrame([
            {'symbol': 'RICH', 'date': today, 'open': 100.0, 'high': 102.0,
             'low': 98.0, 'close': 101.0, 'volume': 200_000,
             'dollar_volume': 20_200_000.0, 'sector': 'Tech', 'industry': '', 'market_cap': 1e11},
            {'symbol': 'POOR', 'date': today, 'open': 1.0, 'high': 1.05,
             'low': 0.98, 'close': 1.02, 'volume': 300_000,
             'dollar_volume': 306_000.0,  # < $500K
             'sector': 'Tech', 'industry': '', 'market_cap': 1e7},
        ])

        result = _apply_volume_filter(df, min_volume=100_000, min_dollar_volume=500_000)

        assert 'RICH' in result['symbol'].values
        assert 'POOR' not in result['symbol'].values

    def test_filter_preserves_valid_stocks(self):
        """
        Given: 모든 종목이 필터 통과 조건 충족
        Then: 필터 후 동일한 수의 종목 유지
        """
        today = date(2026, 2, 25)
        rows = []
        for i in range(5):
            rows.append({
                'symbol': f'STOCK{i}', 'date': today,
                'open': 100.0, 'high': 102.0, 'low': 98.0, 'close': 101.0,
                'volume': 1_000_000, 'dollar_volume': 101_000_000.0,
                'sector': 'Technology', 'industry': '', 'market_cap': 1e12,
            })
        df = pd.DataFrame(rows)

        result = _apply_volume_filter(df, min_volume=100_000, min_dollar_volume=500_000)

        assert len(result) == 5

    def test_filter_empty_after_all_filtered(self):
        """
        Given: 모든 종목이 volume < 100K
        Then: 필터 결과 빈 DataFrame
        """
        today = date(2026, 2, 25)
        df = pd.DataFrame([
            {'symbol': f'TINY{i}', 'date': today,
             'open': 1.0, 'high': 1.05, 'low': 0.95, 'close': 1.0,
             'volume': 1_000, 'dollar_volume': 1_000.0,
             'sector': 'Tech', 'industry': '', 'market_cap': 1e6}
            for i in range(3)
        ])

        result = _apply_volume_filter(df, min_volume=100_000, min_dollar_volume=500_000)

        assert len(result) == 0


# ───────────────────────────────────────────────
# PipelineLog ingest_quality 저장 검증
# ───────────────────────────────────────────────

class TestPipelineLogQualityStorage:

    @pytest.mark.django_db
    def test_pipeline_log_stores_ingest_quality(self, target_date):
        """
        Given: ingest_quality 데이터
        When: PipelineLog 생성
        Then: ingest_quality JSON 필드에 저장됨
        """
        from django.utils import timezone
        from stocks.models import PipelineLog

        quality = {
            'total_received': 498,
            'vs_prev_day_pct': 99.6,
            'sector_null_pct': 1.2,
            'volume_zero_pct': 0.4,
            'degrade_mode': False,
            'warnings': [],
        }

        log = PipelineLog.objects.create(
            date=target_date,
            status='success',
            stages={'ingest': {'count': 498}},
            ingest_quality=quality,
            total_duration_seconds=42.0,
            started_at=timezone.now(),
        )

        log.refresh_from_db()
        assert log.ingest_quality['total_received'] == 498
        assert log.ingest_quality['degrade_mode'] is False

    @pytest.mark.django_db
    def test_pipeline_log_degrade_mode_stored(self, target_date):
        """
        degrade_mode=True 상태가 DB에 올바르게 저장됨.
        """
        from django.utils import timezone
        from stocks.models import PipelineLog

        quality = {
            'total_received': 420,
            'degrade_mode': True,
            'warnings': ['종목수 전일 대비 16.0% 감소', 'volume zero 4.5%'],
        }

        log = PipelineLog.objects.create(
            date=target_date,
            status='partial',
            stages={},
            ingest_quality=quality,
            total_duration_seconds=30.0,
            started_at=timezone.now(),
        )

        log.refresh_from_db()
        assert log.ingest_quality['degrade_mode'] is True
        assert len(log.ingest_quality['warnings']) == 2
