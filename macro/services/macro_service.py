"""
거시경제 통합 서비스

FRED + FMP 데이터를 통합하여 Market Pulse 대시보드용 데이터 제공
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction

from .fred_client import FREDClient
from .fmp_client import FMPClient
from .yfinance_client import YFinanceClient
from ..constants import get_insight_message, calculate_fear_greed_index

logger = logging.getLogger(__name__)


class MacroEconomicService:
    """거시경제 데이터 통합 서비스"""

    # 캐시 TTL (초)
    CACHE_TTL = {
        'realtime': 60,          # VIX, 지수 등
        'daily': 3600,           # 금리, 환율
        'monthly': 86400,        # CPI, 고용
        'quarterly': 86400 * 7,  # GDP
    }

    def __init__(self):
        self.fred = FREDClient()
        self.fmp = FMPClient()
        self.yfinance = YFinanceClient()  # FMP 대체용

    # =========================================================================
    # 1. Market Sentiment (공포/탐욕 지수)
    # =========================================================================

    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Fear & Greed Index 계산 및 반환

        VIX + 수익률 곡선 스프레드 기반 계산

        Returns:
            공포/탐욕 지수 데이터
        """
        cache_key = 'macro:fear_greed_index'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            # VIX 조회
            vix_data = self.fred.get_vix()
            vix_value = vix_data['value'] if vix_data else 20  # 기본값

            # 수익률 곡선 스프레드
            spread_data = self.fred.get_yield_spread()
            spread_value = spread_data['spread'] if spread_data['spread'] else 1.0

            # Fear & Greed Index 계산
            result = calculate_fear_greed_index(vix_value, spread_value)

            # 추가 메타데이터
            result['vix'] = vix_data
            result['yield_spread'] = spread_data
            result['last_updated'] = datetime.now().isoformat()

            # 캐시 저장
            cache.set(cache_key, result, self.CACHE_TTL['realtime'])

            return result

        except Exception as e:
            logger.error(f"Failed to calculate Fear & Greed Index: {e}")
            return {
                'value': 50,
                'rule_key': 'neutral',
                'label': '중립',
                'message': '데이터를 가져오는 중 오류가 발생했습니다.',
                'error': str(e),
            }

    # =========================================================================
    # 2. Interest Rates & Yield Curve
    # =========================================================================

    def get_interest_rates_dashboard(self) -> Dict[str, Any]:
        """
        금리 대시보드 데이터

        Returns:
            금리, 수익률 곡선, 변화 추이 데이터
        """
        cache_key = 'macro:interest_rates_dashboard'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            # FRED에서 금리 데이터
            rates = self.fred.get_interest_rates()

            # 수익률 곡선 상태
            yield_spread = self.fred.get_yield_spread()
            curve_insight = get_insight_message('yield_curve', yield_spread['spread'] or 0)

            # 수익률 곡선 데이터 (차트용)
            yield_curve_data = []
            maturities = [
                ('3M', 'DGS3MO'),
                ('6M', 'DGS6MO'),
                ('1Y', 'DGS1'),
                ('2Y', 'DGS2'),
                ('5Y', 'DGS5'),
                ('10Y', 'DGS10'),
                ('30Y', 'DGS30'),
            ]

            for label, series_id in maturities:
                if series_id in rates:
                    yield_curve_data.append({
                        'maturity': label,
                        'rate': rates[series_id]['value'],
                    })

            result = {
                'fed_funds_rate': rates.get('FEDFUNDS', {}).get('value'),
                'treasury_2y': rates.get('DGS2', {}).get('value'),
                'treasury_10y': rates.get('DGS10', {}).get('value'),
                'yield_spread': yield_spread,
                'yield_curve_status': curve_insight,
                'yield_curve_data': yield_curve_data,
                'last_updated': datetime.now().isoformat(),
            }

            cache.set(cache_key, result, self.CACHE_TTL['daily'])
            return result

        except Exception as e:
            logger.error(f"Failed to get interest rates dashboard: {e}")
            return {'error': str(e)}

    # =========================================================================
    # 3. Inflation & Employment
    # =========================================================================

    def get_inflation_dashboard(self) -> Dict[str, Any]:
        """
        인플레이션 대시보드 데이터

        Returns:
            CPI, PCE, 고용 데이터
        """
        cache_key = 'macro:inflation_dashboard'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            # 인플레이션 지표
            inflation = self.fred.get_inflation_data()

            # 고용 지표
            employment = self.fred.get_employment_data()

            # GDP 성장률
            gdp = self.fred.get_gdp_growth()

            result = {
                'inflation': {
                    'cpi_yoy': inflation.get('CPIAUCSL', {}).get('yoy_change'),
                    'core_cpi_yoy': inflation.get('CPILFESL', {}).get('yoy_change'),
                    'pce_yoy': inflation.get('PCEPI', {}).get('yoy_change'),
                    'fed_target': 2.0,  # 연준 목표
                },
                'employment': {
                    'unemployment_rate': employment.get('unemployment_rate', {}).get('value'),
                    'nfp_change': employment.get('nonfarm_payrolls', {}).get('change'),
                    'initial_claims': employment.get('initial_claims', {}).get('value'),
                },
                'gdp': gdp,
                'last_updated': datetime.now().isoformat(),
            }

            cache.set(cache_key, result, self.CACHE_TTL['monthly'])
            return result

        except Exception as e:
            logger.error(f"Failed to get inflation dashboard: {e}")
            return {'error': str(e)}

    # =========================================================================
    # 4. Global Markets
    # =========================================================================

    def get_global_markets_dashboard(self) -> Dict[str, Any]:
        """
        글로벌 시장 대시보드 데이터

        Returns:
            지수, 섹터, 환율, 원자재 데이터
        """
        cache_key = 'macro:global_markets_dashboard'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            # yfinance 사용 (FMP API 403 에러 대응)
            # 주요 지수
            indices = self.yfinance.get_market_indices()

            # 섹터 성과
            sectors = self.yfinance.get_sector_performance()

            # 환율
            forex = self.yfinance.get_forex_rates()

            # 원자재
            commodities = self.yfinance.get_commodities()

            # 달러 인덱스
            dxy = self.yfinance.get_dollar_index()

            # VIX (FRED에서 가져옴)
            vix = self.fred.get_vix()

            result = {
                'indices': {
                    'sp500': indices.get('^GSPC'),
                    'nasdaq': indices.get('^IXIC'),
                    'dow': indices.get('^DJI'),
                    'russell2000': indices.get('^RUT'),
                },
                'global_indices': {
                    'ftse': indices.get('^FTSE'),
                    'dax': indices.get('^GDAXI'),
                    'nikkei': indices.get('^N225'),
                    'hangseng': indices.get('^HSI'),
                },
                'sectors': sectors,
                'forex': forex,
                'commodities': commodities,
                'dxy': dxy,
                'vix': vix,
                'last_updated': datetime.now().isoformat(),
            }

            cache.set(cache_key, result, self.CACHE_TTL['realtime'])
            return result

        except Exception as e:
            logger.error(f"Failed to get global markets dashboard: {e}")
            return {'error': str(e)}

    # =========================================================================
    # 5. Economic Calendar
    # =========================================================================

    def get_economic_calendar(
        self,
        days_ahead: int = 7,
        importance_filter: str = None
    ) -> Dict[str, Any]:
        """
        경제 캘린더 데이터

        Args:
            days_ahead: 향후 며칠간의 이벤트를 가져올지
            importance_filter: 중요도 필터 ('critical', 'high', 'medium')

        Returns:
            경제 이벤트 리스트
        """
        cache_key = f'macro:economic_calendar:{days_ahead}:{importance_filter}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            from_date = date.today()
            to_date = from_date + timedelta(days=days_ahead)

            events = self.fmp.get_economic_calendar(from_date, to_date)

            # 중요도 필터링
            if importance_filter:
                impact_map = {
                    'critical': 'High',
                    'high': 'High',
                    'medium': 'Medium',
                }
                filter_impact = impact_map.get(importance_filter)
                if filter_impact:
                    events = [e for e in events if e.get('impact') == filter_impact]

            # 날짜별 그룹핑
            grouped = {}
            for event in events:
                event_date = event.get('date', '')[:10]
                if event_date not in grouped:
                    grouped[event_date] = []
                grouped[event_date].append({
                    'time': event.get('date', '')[11:16],
                    'event': event.get('event'),
                    'country': event.get('country'),
                    'impact': event.get('impact'),
                    'actual': event.get('actual'),
                    'previous': event.get('previous'),
                    'estimate': event.get('estimate'),
                })

            result = {
                'events_by_date': grouped,
                'total_count': len(events),
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'last_updated': datetime.now().isoformat(),
            }

            cache.set(cache_key, result, self.CACHE_TTL['daily'])
            return result

        except Exception as e:
            logger.error(f"Failed to get economic calendar: {e}")
            return {'error': str(e), 'events_by_date': {}}

    # =========================================================================
    # 6. Combined Dashboard (전체 데이터)
    # =========================================================================

    def get_market_pulse_dashboard(self) -> Dict[str, Any]:
        """
        Market Pulse 전체 대시보드 데이터

        모든 섹션의 데이터를 한 번에 반환

        Returns:
            전체 대시보드 데이터
        """
        cache_key = 'macro:market_pulse_full'
        cached = cache.get(cache_key)
        if cached:
            return cached

        result = {
            # Section 1: 시장 심리
            'fear_greed': self.get_fear_greed_index(),

            # Section 2: 금리 & 수익률 곡선
            'interest_rates': self.get_interest_rates_dashboard(),

            # Section 3: 인플레이션 & 고용
            'economy': self.get_inflation_dashboard(),

            # Section 4: 글로벌 시장
            'global_markets': self.get_global_markets_dashboard(),

            # Section 5: 경제 캘린더
            'calendar': self.get_economic_calendar(days_ahead=7, importance_filter='high'),

            # 메타데이터
            'last_updated': datetime.now().isoformat(),
        }

        # 전체 대시보드 캐시는 가장 짧은 TTL 사용
        cache.set(cache_key, result, self.CACHE_TTL['realtime'])

        return result

    # =========================================================================
    # 데이터 동기화 (Celery 태스크용)
    # =========================================================================

    def sync_indicator_values(self, indicator_code: str) -> int:
        """
        지표 값을 DB에 동기화

        Args:
            indicator_code: FRED 시리즈 코드

        Returns:
            저장된 레코드 수
        """
        from ..models import EconomicIndicator, IndicatorValue

        try:
            indicator = EconomicIndicator.objects.get(code=indicator_code)
        except EconomicIndicator.DoesNotExist:
            logger.error(f"Indicator not found: {indicator_code}")
            return 0

        observations = self.fred.get_series_observations(
            indicator_code,
            limit=100,
            sort_order='desc'
        )

        saved_count = 0
        with transaction.atomic():
            for obs in observations:
                date_str = obs.get('date')
                value_str = obs.get('value')

                if not date_str or not value_str or value_str == '.':
                    continue

                try:
                    obs_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    value = Decimal(value_str)

                    _, created = IndicatorValue.objects.update_or_create(
                        indicator=indicator,
                        date=obs_date,
                        defaults={'value': value}
                    )

                    if created:
                        saved_count += 1

                except (ValueError, Exception) as e:
                    logger.warning(f"Failed to save {indicator_code} @ {date_str}: {e}")
                    continue

        # 지표 최종 업데이트 시간 갱신
        indicator.last_updated = datetime.now()
        indicator.save(update_fields=['last_updated'])

        logger.info(f"Synced {saved_count} new values for {indicator_code}")
        return saved_count

    def sync_all_indicators(self) -> Dict[str, int]:
        """
        모든 주요 경제 지표 동기화

        Returns:
            지표별 저장된 레코드 수
        """
        from ..models import EconomicIndicator

        # 주요 지표 목록
        indicators = [
            'FEDFUNDS',   # 기준금리
            'DGS2',       # 2년물 국채
            'DGS10',      # 10년물 국채
            'T10Y2Y',     # 장단기 금리차
            'VIXCLS',     # VIX
            'UNRATE',     # 실업률
            'CPIAUCSL',   # CPI
            'PCEPI',      # PCE
        ]

        results = {}
        for code in indicators:
            try:
                # 지표가 없으면 생성
                EconomicIndicator.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': code,
                        'category': 'interest_rate' if 'DGS' in code or 'FEDFUNDS' in code else 'other',
                        'data_source': 'fred',
                        'update_frequency': 'daily',
                    }
                )
                saved = self.sync_indicator_values(code)
                results[code] = saved
            except Exception as e:
                logger.error(f"Failed to sync {code}: {e}")
                results[code] = 0

        return results

    def sync_market_indices(self) -> int:
        """
        시장 지수 데이터 동기화 (yfinance 사용)

        Returns:
            저장된 레코드 수
        """
        from ..models import MarketIndex, MarketIndexPrice

        try:
            # yfinance 사용 (FMP API 403 에러 대응)
            indices_data = self.yfinance.get_market_indices()
            saved_count = 0
            today = date.today()

            with transaction.atomic():
                for symbol, data in indices_data.items():
                    if not data or not data.get('price'):
                        continue

                    # MarketIndex 생성/조회
                    index, _ = MarketIndex.objects.get_or_create(
                        symbol=symbol,
                        defaults={
                            'name': data.get('name', symbol),
                            'category': 'us_equity' if symbol.startswith('^G') or symbol.startswith('^D') else 'global',
                        }
                    )

                    # 가격 저장
                    _, created = MarketIndexPrice.objects.update_or_create(
                        index=index,
                        date=today,
                        defaults={
                            'close': Decimal(str(data.get('price', 0))),
                            'change': Decimal(str(data.get('change', 0))) if data.get('change') else None,
                            'change_percent': Decimal(str(data.get('change_percent', 0))) if data.get('change_percent') else None,
                        }
                    )

                    if created:
                        saved_count += 1

            logger.info(f"Synced {saved_count} market index prices")
            return saved_count

        except Exception as e:
            logger.error(f"Failed to sync market indices: {e}")
            return 0

    def sync_global_markets(self) -> Dict[str, int]:
        """
        글로벌 시장 데이터 동기화 (섹터, 환율, 원자재) - yfinance 사용

        Returns:
            카테고리별 저장된 레코드 수
        """
        results = {'sectors': 0, 'forex': 0, 'commodities': 0}

        try:
            # yfinance 사용 (FMP API 403 에러 대응)
            # 섹터 데이터
            sectors = self.yfinance.get_sector_performance()
            if sectors:
                results['sectors'] = len(sectors.get('sectors', {}))

            # 환율 데이터
            forex = self.yfinance.get_forex_rates()
            if forex:
                results['forex'] = len(forex)

            # 원자재 데이터
            commodities = self.yfinance.get_commodities()
            if commodities:
                results['commodities'] = len(commodities)

            logger.info(f"Synced global markets: {results}")
            return results

        except Exception as e:
            logger.error(f"Failed to sync global markets: {e}")
            return results

    def sync_economic_calendar(self) -> int:
        """
        경제 캘린더 동기화 (FMP API 사용 - 현재 비활성화)

        Returns:
            저장된 이벤트 수
        """
        # FMP API 403 에러로 인해 경제 캘린더 동기화 비활성화
        # 추후 대체 API 또는 수동 데이터 입력으로 대체 예정
        logger.info("Economic calendar sync skipped (FMP API unavailable)")
        return 0

    def check_data_availability(self) -> Dict[str, bool]:
        """
        데이터 가용성 확인

        Returns:
            카테고리별 데이터 존재 여부
        """
        from ..models import EconomicIndicator, MarketIndex, EconomicEvent

        return {
            'has_indicators': EconomicIndicator.objects.exists(),
            'has_market_indices': MarketIndex.objects.exists(),
            'has_economic_events': EconomicEvent.objects.exists(),
            'has_recent_data': self._has_recent_data(),
        }

    def _has_recent_data(self) -> bool:
        """최근 데이터가 있는지 확인 (24시간 이내)"""
        from ..models import IndicatorValue
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(hours=24)
        return IndicatorValue.objects.filter(created_at__gte=cutoff).exists()
