"""
거시경제 통합 서비스 — FRED + FMP 데이터를 마켓 펄스 대시보드용으로 통합.

소속: apps/market_pulse/services (app 레이어 서비스).
역할: FRED(매크로지표) + FMP(시장 지수·환율 등)에서 시계열을 가져와 macro DB
  (MarketIndex·MarketIndexPrice·EconomicIndicator·IndicatorValue·EconomicEvent)에 upsert.
의존: packages.shared.api_request.fred_client.FREDClient,
  packages.shared.api_request.providers.fmp.market_pulse_client.FMPClient, macro.models.
주의: FMP는 Starter Plan(300/m, 10k/d, `/stable/*` only). Legacy `/api/v3/*` 금지.
소비처: tasks/macro.py·management/commands/{backfill_v2_a1, sync_marketpulse_v2_*}.py.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.market_pulse.constants import calculate_fear_greed_index, get_insight_message
from packages.shared.api_request.fred_client import FREDClient
from packages.shared.api_request.providers.fmp.market_pulse_client import FMPClient

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

    # SWR(stale-while-revalidate) 캐시 키 — 전체 대시보드 전용.
    #   FULL  : fresh 캐시(TTL=realtime=60s). 워밍 beat는 ET 장중만 → KST 사용 시 상시 미스.
    #   STALE : 마지막 성공 payload 보존(24h). fresh 미스 시 즉시 응답용(28s 라이브 집계 회피).
    #   LOCK  : 백그라운드 갱신 enqueue dedup(cache.add 원자획득, 120s 자동만료).
    # (D-SUBPAGES-SWR, common-bugs 채번대기 — 장외 콜드 캐시 + ET-장중-한정 워밍.)
    FULL_CACHE_KEY = 'macro:market_pulse_full'
    STALE_CACHE_KEY = 'macro:market_pulse_full:stale'
    REFRESH_LOCK_KEY = 'macro:market_pulse_full:refreshing'
    STALE_TTL = 86400        # 24h
    REFRESH_LOCK_TTL = 120   # 워밍 태스크 왕복 여유(락 방치 방지 자동만료)

    def __init__(self):
        self.fred = FREDClient()
        self.fmp = FMPClient()

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
            result['last_updated'] = timezone.now().isoformat()

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
                'last_updated': timezone.now().isoformat(),
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
                'last_updated': timezone.now().isoformat(),
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
            # 주요 지수
            indices = self.fmp.get_market_indices()

            # 섹터 성과
            sectors = self.fmp.get_sector_performance()

            # 환율
            forex = self.fmp.get_forex_rates()

            # 원자재
            commodities = self.fmp.get_commodities()

            # 달러 인덱스
            dxy = self.fmp.get_dollar_index()

            # VIX (FRED에서 가져옴)
            vix = self.fred.get_vix()

            result = {
                'indices': {
                    'sp500': indices.get('SPY'),
                    'nasdaq': indices.get('QQQ'),
                    'dow': indices.get('DIA'),
                    'russell2000': indices.get('IWM'),
                },
                'global_indices': {},
                'sectors': sectors,
                'forex': forex,
                'commodities': commodities,
                'dxy': dxy,
                'vix': vix,
                'last_updated': timezone.now().isoformat(),
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
                'last_updated': timezone.now().isoformat(),
            }

            cache.set(cache_key, result, self.CACHE_TTL['daily'])
            return result

        except Exception as e:
            logger.error(f"Failed to get economic calendar: {e}")
            return {'error': str(e), 'events_by_date': {}}

    # =========================================================================
    # 6. Combined Dashboard (전체 데이터)
    # =========================================================================

    def _compute_market_pulse_dashboard(self) -> Dict[str, Any]:
        """5섹션 라이브 집계(FRED+FMP 외부 호출 ~14회). 콜드 경로에서만 실행."""
        return {
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
            'last_updated': timezone.now().isoformat(),
        }

    def _store_dashboard(self, result: Dict[str, Any]) -> None:
        """fresh(60s) + stale(24h) 동시 저장 — 성공한 계산 결과를 SWR 양 키에 반영."""
        cache.set(self.FULL_CACHE_KEY, result, self.CACHE_TTL['realtime'])
        cache.set(self.STALE_CACHE_KEY, result, self.STALE_TTL)

    def get_market_pulse_dashboard(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Market Pulse 전체 대시보드 데이터 (SWR 정책).

        모든 섹션의 데이터를 한 번에 반환. 응답 스키마는 불변(FREEZE) —
        스테일 여부 판단은 FE가 `last_updated` 나이로 수행한다.

        정책:
          - fresh 히트 → 즉시 반환(불변).
          - fresh 미스 + stale 존재 → 백그라운드 갱신 1회 enqueue(락 dedup) 후 stale 즉시 반환.
            요청 스레드에서 28s 라이브 집계를 타지 않는다(외부 호출 무증가).
          - stale도 없음(최초 콜드) → 라이브 계산 → fresh+stale 저장. 계산 실패 시 경합으로
            채워진 stale이 있으면 폴백(200), 없으면 재발생(뷰 500 경로 유지).

        Args:
            force_refresh: True면(워밍 태스크 전용) 캐시 무시하고 무조건 재계산 후
              fresh+stale 갱신 + 갱신 락 해제. SWR 미스 경로가 스스로를 다시
              enqueue하는 무한 루프를 차단한다.
        """
        if force_refresh:
            result = self._compute_market_pulse_dashboard()
            self._store_dashboard(result)
            cache.delete(self.REFRESH_LOCK_KEY)
            return result

        # 1) fresh 히트 → 즉시 반환(불변)
        cached = cache.get(self.FULL_CACHE_KEY)
        if cached:
            return cached

        # 2) fresh 미스 + stale 존재 → SWR: 백그라운드 갱신 후 stale 즉시 반환
        stale = cache.get(self.STALE_CACHE_KEY)
        if stale is not None:
            self._enqueue_refresh()
            return stale

        # 3) stale도 없음(최초 콜드) → 라이브 계산
        try:
            result = self._compute_market_pulse_dashboard()
        except Exception:
            # 계산 실패 — 그새 다른 워커가 stale을 채웠으면 폴백(200), 아니면 500 경로 유지
            stale = cache.get(self.STALE_CACHE_KEY)
            if stale is not None:
                return stale
            raise
        self._store_dashboard(result)
        return result

    def _enqueue_refresh(self) -> None:
        """락 획득 시에만 백그라운드 갱신 태스크 1회 enqueue(중복 폭주 방지)."""
        if not cache.add(self.REFRESH_LOCK_KEY, '1', self.REFRESH_LOCK_TTL):
            return  # 이미 다른 요청이 갱신을 걸어둠 — dedup
        try:
            from apps.market_pulse.tasks.macro import refresh_market_pulse_cache
            refresh_market_pulse_cache.delay()
        except Exception as e:
            # enqueue 실패 시 락 해제 → 다음 요청이 재시도 가능(락 방치 방지)
            logger.warning(f"Failed to enqueue market pulse refresh: {e}")
            cache.delete(self.REFRESH_LOCK_KEY)

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
        indicator.last_updated = timezone.now()
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
        시장 지수 데이터 동기화 (FMP API 사용)

        Returns:
            저장된 레코드 수
        """
        from ..models import MarketIndex, MarketIndexPrice

        try:
            indices_data = self.fmp.get_market_indices()
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
        글로벌 시장 데이터 동기화 (섹터, 환율, 원자재) - FMP API 사용

        Returns:
            카테고리별 저장된 레코드 수
        """
        results = {'sectors': 0, 'forex': 0, 'commodities': 0}

        try:
            # 섹터 데이터
            sectors = self.fmp.get_sector_performance()
            if sectors:
                results['sectors'] = len(sectors.get('sectors', {}))

            # 환율 데이터
            forex = self.fmp.get_forex_rates()
            if forex:
                results['forex'] = len(forex)

            # 원자재 데이터
            commodities = self.fmp.get_commodities()
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
        from ..models import EconomicEvent, EconomicIndicator, MarketIndex

        return {
            'has_indicators': EconomicIndicator.objects.exists(),
            'has_market_indices': MarketIndex.objects.exists(),
            'has_economic_events': EconomicEvent.objects.exists(),
            'has_recent_data': self._has_recent_data(),
        }

    def _has_recent_data(self) -> bool:
        """최근 데이터가 있는지 확인 (24시간 이내)"""
        from django.utils import timezone

        from ..models import IndicatorValue

        cutoff = timezone.now() - timedelta(hours=24)
        return IndicatorValue.objects.filter(created_at__gte=cutoff).exists()
