"""PR-A1 backfill_v2_a1 management command 테스트.

T12~T18 커버 (PR-A1 위임 프롬프트 §5.2).
- T12: --dry-run
- T13: --check-pending
- T14: idempotency
- T15: --series-id 단일 실행
- T17: --from/--to 범위
- T18: --limit
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command


@pytest.fixture
def seed_indicators(db):
    """11 신규 EconomicIndicator 시드 (migration 0003이 적재된 상태 가정)."""
    from macro.models.indicators import EconomicIndicator
    series = (
        'NFCI', 'NFCICREDIT', 'NFCILEVERAGE', 'NFCIRISK',
        'BAMLH0A0HYM2', 'BAMLH0A3HYC',
        'T10Y3M', 'VIX3M', 'MOVE',
        'DGS10', 'DGS2',
    )
    for code in series:
        EconomicIndicator.objects.update_or_create(
            code=code,
            defaults={'name': code, 'data_source': 'fred'},
        )


@pytest.fixture
def seed_market_indices(db):
    """11 GICS sector ETFs 시드 (migration 0004 적재 상태 가정)."""
    from macro.models.indicators import MarketIndex
    mapping = {
        'XLF': 'FINANCIALS', 'XLK': 'TECH', 'XLV': 'HEALTHCARE',
        'XLY': 'CONSUMER_DISC', 'XLP': 'CONSUMER_STAPLES',
        'XLE': 'ENERGY', 'XLI': 'INDUSTRIALS', 'XLB': 'MATERIALS',
        'XLU': 'UTILITIES', 'XLRE': 'REAL_ESTATE', 'XLC': 'COMMUNICATION',
    }
    for symbol, gics in mapping.items():
        MarketIndex.objects.update_or_create(
            symbol=symbol,
            defaults={'name': symbol, 'sector_group': gics, 'category': 'sector'},
        )


@pytest.mark.django_db
class TestDryRun:
    """T12: --dry-run은 DB 변경 없이 대상 출력."""

    def test_t12_dry_run_lists_targets(self, seed_indicators, seed_market_indices):
        from macro.models.indicators import IndicatorValue, MarketIndexPrice

        before_obs = IndicatorValue.objects.count()
        before_bars = MarketIndexPrice.objects.count()

        out = StringIO()
        call_command('backfill_v2_a1', '--dry-run', stdout=out)
        output = out.getvalue()

        assert '[DRY-RUN]' in output
        assert 'Economic (11)' in output
        assert 'Market (11)' in output
        # DB 미변경
        assert IndicatorValue.objects.count() == before_obs
        assert MarketIndexPrice.objects.count() == before_bars


@pytest.mark.django_db
class TestCheckPending:
    """T13: --check-pending — 데이터 0인 series/symbol 출력."""

    def test_t13_all_pending_initially(self, seed_indicators, seed_market_indices):
        out = StringIO()
        call_command('backfill_v2_a1', '--check-pending', stdout=out)
        output = out.getvalue()

        assert '[CHECK] Pending economic (11):' in output
        assert '[CHECK] Pending market (11):' in output
        assert "'NFCI'" in output
        assert "'XLF'" in output

    def test_t13_partial_seeded_pending_excluded(self, seed_indicators, seed_market_indices):
        from macro.models.indicators import EconomicIndicator, IndicatorValue
        nfci = EconomicIndicator.objects.get(code='NFCI')
        IndicatorValue.objects.create(indicator=nfci, date=date(2026, 4, 1), value=Decimal('-0.5'))

        out = StringIO()
        call_command('backfill_v2_a1', '--check-pending', stdout=out)
        output = out.getvalue()

        # NFCI는 더 이상 pending이 아님
        assert "'NFCI'" not in output.split('Pending economic')[1].split(']')[0]


@pytest.mark.django_db
class TestIdempotency:
    """T14: 동일 fetch 결과 두 번 적용 시 두 번째에서 inserted=0."""

    def test_t14_idempotent_economic(self, seed_indicators, seed_market_indices):
        fake_obs = [{'date': date(2026, 4, 1), 'value': '-0.5'}]

        with patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_fred', return_value=fake_obs), \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_indicator', return_value=fake_obs), \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_ohlc', return_value=[]):
            out1 = StringIO()
            call_command('backfill_v2_a1', '--series-id', 'NFCI', stdout=out1)
            out2 = StringIO()
            call_command('backfill_v2_a1', '--series-id', 'NFCI', stdout=out2)

        assert 'NFCI: fetched 1, inserted 1' in out1.getvalue()
        # 2회차: fetched>0(가져옴) 이나 inserted 0(이미 존재) — 침묵 동치 해소.
        assert 'NFCI: fetched 1, inserted 0' in out2.getvalue()


@pytest.mark.django_db
class TestFredDeepBackfill:
    """FRED 심층 백필 회귀 — limit·sort_order override로 전 창 확보 + fetched/inserted 구분."""

    def test_fetch_fred_passes_full_limit_and_asc(self, seed_indicators, seed_market_indices):
        """_fetch_fred가 get_series_observations에 limit=100000·sort_order='asc' 전달.

        (기본 limit=100·desc면 심층 창에서 최신 100건[대개 기존]만 와 0 삽입 = 원 장애.)
        """
        fake_client = MagicMock()
        fake_client.get_series_observations.return_value = [
            {'date': '2023-07-10', 'value': '0.10'},
            {'date': '2023-07-11', 'value': '0.20'},
        ]
        with patch('packages.shared.api_request.fred_client.FREDClient', return_value=fake_client), \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_ohlc', return_value=[]):
            call_command(
                'backfill_v2_a1', '--series-id', 'NFCI', '--econ-only',
                '--from', '2023-07-10', '--to', '2026-07-09',
            )
        fake_client.get_series_observations.assert_called_once()
        kwargs = fake_client.get_series_observations.call_args.kwargs
        assert kwargs.get('limit') == 100000
        assert kwargs.get('sort_order') == 'asc'

    def test_log_distinguishes_fetched_from_inserted(self, seed_indicators, seed_market_indices):
        """fetched>0·inserted=0(이미 존재)이 'fetched N, inserted 0'로 노출 — 침묵 해소."""
        fake_obs = [{'date': date(2026, 4, 1), 'value': '-0.5'}]
        with patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_fred', return_value=fake_obs), \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_indicator', return_value=fake_obs), \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_ohlc', return_value=[]):
            call_command('backfill_v2_a1', '--series-id', 'NFCI', '--econ-only')  # 1회차 삽입
            out = StringIO()
            call_command('backfill_v2_a1', '--series-id', 'NFCI', '--econ-only', stdout=out)  # 2회차 기존
        v = out.getvalue()
        assert 'NFCI: fetched 1, inserted 0' in v  # 가져왔으나 이미 존재(못 가져옴 아님)


@pytest.mark.django_db
class TestSingleTarget:
    """T15: --series-id 단일 실행은 다른 series fetch 안 함."""

    def test_t15_series_id_only(self, seed_indicators, seed_market_indices):
        with patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_fred', return_value=[]) as m_fred, \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_indicator', return_value=[]) as m_yi, \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_ohlc', return_value=[]) as m_ohlc:
            call_command('backfill_v2_a1', '--series-id', 'NFCI')

        # NFCI 한 series만 fetch (FRED 또는 Yahoo 한 곳)
        total_fetch_calls = m_fred.call_count + m_yi.call_count
        assert total_fetch_calls == 1
        # Market은 호출 안 됨 (NEW_MARKET_SYMBOLS 11개 디폴트라 호출되지 않으려면 추가 가드 필요)
        # 본 명령은 series-id만 줘도 market 디폴트 11개를 진행하므로 m_ohlc은 11회 호출
        # → 의도: --series-id는 series 단일 + market은 디폴트.
        # PR-A1 사양 동일.
        assert m_ohlc.call_count == 11


@pytest.mark.django_db
class TestDateRange:
    """T17: --from/--to 인자가 fetch 메서드에 전달."""

    def test_t17_date_range_passed(self, seed_indicators, seed_market_indices):
        with patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_fred', return_value=[]) as m_fred, \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_indicator', return_value=[]), \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_ohlc', return_value=[]):
            call_command(
                'backfill_v2_a1',
                '--series-id', 'NFCI',
                '--from', '2025-01-01',
                '--to', '2025-12-31',
            )

        m_fred.assert_called_once()
        args = m_fred.call_args
        assert args.args[1] == date(2025, 1, 1)
        assert args.args[2] == date(2025, 12, 31)


@pytest.mark.django_db
class TestLimit:
    """T18: --limit 대상 수 제한."""

    def test_t18_limit_3(self, seed_indicators, seed_market_indices):
        with patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_fred', return_value=[]) as m_fred, \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_indicator', return_value=[]) as m_yi, \
             patch('apps.market_pulse.management.commands.backfill_v2_a1.Command._fetch_yahoo_ohlc', return_value=[]) as m_ohlc:
            call_command('backfill_v2_a1', '--limit', '3')

        # economic 3개 + market 3개 fetch
        assert (m_fred.call_count + m_yi.call_count) == 3
        assert m_ohlc.call_count == 3
