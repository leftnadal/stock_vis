"""
Enhanced Screener Service

FMP API가 직접 지원하지 않는 펀더멘탈 필터(PE, ROE, EPS Growth 등)를 위해
온디맨드로 Key Metrics API를 호출하여 2단계 필터링을 수행합니다.

Usage:
    service = EnhancedScreenerService()
    result = service.screen_enhanced(
        filters={'pe_ratio_max': 15, 'roe_min': 15, 'market_cap_min': 1_000_000_000},
        limit=100
    )
"""
import logging
from typing import Dict, List, Any, Optional, Set
from decimal import Decimal

from django.core.cache import cache

from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


class EnhancedScreenerService:
    """
    Enhanced 프리셋용 스크리너 서비스

    1차: FMP company-screener (market_cap, volume 등)
    2차: FMP key-metrics-ttm (PE, ROE, EPS Growth 등) - 온디맨드
    """

    # FMP company-screener API 직접 지원 필터 (파라미터 매핑)
    FMP_DIRECT_FILTERS = {
        'market_cap_min': 'marketCapMoreThan',
        'market_cap_max': 'marketCapLowerThan',
        'price_min': 'priceMoreThan',
        'price_max': 'priceLowerThan',
        'beta_min': 'betaMoreThan',
        'beta_max': 'betaLowerThan',
        'volume_min': 'volumeMoreThan',
        'volume_max': 'volumeLowerThan',
        'dividend_min': 'dividendMoreThan',
        'dividend_max': 'dividendLowerThan',
        'sector': 'sector',
        'exchange': 'exchange',
        'is_etf': 'isEtf',
        'is_actively_trading': 'isActivelyTrading',
    }

    # FMP 응답에 포함되어 클라이언트 필터링 가능 (API 파라미터는 없지만 응답에 필드 있음)
    CLIENT_FILTERABLE = {
        'change_percent_min',
        'change_percent_max',
    }

    # 추가 API 호출 필요 필터 (FMP key-metrics-ttm)
    ENHANCED_FILTERS = {
        'pe_ratio_min', 'pe_ratio_max',      # P/E Ratio
        'pb_ratio_min', 'pb_ratio_max',      # P/B Ratio
        'roe_min', 'roe_max',                # Return on Equity
        'roa_min', 'roa_max',                # Return on Assets
        'eps_growth_min', 'eps_growth_max',  # EPS Growth
        'revenue_growth_min', 'revenue_growth_max',  # Revenue Growth
        'debt_equity_max',                   # Debt to Equity
        'current_ratio_min',                 # Current Ratio
        'profit_margin_min',                 # Profit Margin
        'rsi_min', 'rsi_max',                # RSI (기술적 지표)
    }

    # Key Metrics API 응답 필드 매핑 (FMP /stable/key-metrics-ttm 기준)
    # Note: ROE는 decimal (1.5 = 150%), 필터 적용 시 *100 변환 필요
    METRICS_FIELD_MAP = {
        'pe_ratio': 'earningsYieldTTM',  # 1/PE, 역수 계산 필요
        'pb_ratio': 'grahamNumberTTM',   # 간접 지표
        'roe': 'returnOnEquityTTM',      # decimal (1.5 = 150%)
        'roa': 'returnOnAssetsTTM',      # decimal
        'eps_growth': 'netIncomePerShareTTM',  # 간접 계산 필요
        'revenue_growth': 'revenuePerShareTTM',  # 간접 계산 필요
        'debt_equity': 'netDebtToEBITDATTM',  # 부채 관련 지표
        'current_ratio': 'currentRatioTTM',
        'profit_margin': 'incomeQualityTTM',  # 간접 지표
    }

    # 캐시 TTL
    METRICS_CACHE_TTL = 3600  # 1시간

    def __init__(self):
        self.fmp_client = FMPClient()

    def screen_enhanced(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        sort_by: str = 'marketCap',
        sort_order: str = 'desc'
    ) -> Dict:
        """
        Enhanced 필터링 수행

        1. FMP 스크리너로 1차 필터링 (최대 500개)
        2. Enhanced 필터 있으면 key-metrics-ttm 배치 호출
        3. 펀더멘탈 필터 적용
        4. 클라이언트 필터 (change_percent 등)
        5. 정렬 및 결과 반환

        Args:
            filters: 필터 조건 딕셔너리
            limit: 최종 반환 개수
            sort_by: 정렬 기준
            sort_order: 정렬 방향

        Returns:
            {
                'results': [...],
                'count': 150,
                'is_enhanced': True,
                'filters_applied': {...}
            }
        """
        logger.info(f"Enhanced 스크리너 실행: {len(filters)}개 필터, limit={limit}")

        # 1. 필터 분리
        fmp_filters = self._extract_fmp_filters(filters)
        enhanced_filters = self._extract_enhanced_filters(filters)
        client_filters = self._extract_client_filters(filters)

        try:
            # 2. FMP 스크리너 호출 (1차 필터링)
            # Enhanced 필터가 있으면 더 많은 종목을 가져와서 필터링
            fetch_limit = 500 if enhanced_filters else min(limit * 2, 500)
            fmp_results = self._fetch_fmp_screener(fmp_filters, limit=fetch_limit)

            if not fmp_results:
                return {
                    'results': [],
                    'count': 0,
                    'is_enhanced': bool(enhanced_filters),
                    'filters_applied': {
                        'fmp': list(fmp_filters.keys()),
                        'enhanced': list(enhanced_filters.keys()),
                        'client': list(client_filters.keys()),
                    }
                }

            # 3. Enhanced 필터 있으면 추가 API 호출
            if enhanced_filters:
                # 최대 100개만 metrics 조회 (Rate Limit 고려)
                symbols = [r['symbol'] for r in fmp_results[:100]]
                metrics = self._fetch_key_metrics_batch(symbols)

                # 펀더멘탈 데이터 병합
                enriched = self._merge_metrics(fmp_results[:100], metrics)

                # Enhanced 필터 적용
                filtered = self._apply_enhanced_filters(enriched, enhanced_filters)
            else:
                filtered = fmp_results

            # 4. 클라이언트 필터 (change_percent 등)
            if client_filters:
                filtered = self._apply_client_filters(filtered, client_filters)

            # 5. 정렬
            filtered = self._sort_results(filtered, sort_by, sort_order)

            # 6. 결과 제한
            final_results = filtered[:limit]

            return {
                'results': final_results,
                'count': len(final_results),
                'total_before_filter': len(fmp_results),
                'is_enhanced': bool(enhanced_filters),
                'filters_applied': {
                    'fmp': list(fmp_filters.keys()),
                    'enhanced': list(enhanced_filters.keys()),
                    'client': list(client_filters.keys()),
                }
            }

        except FMPAPIError as e:
            logger.error(f"FMP API 오류: {e}")
            return {
                'results': [],
                'count': 0,
                'is_enhanced': bool(enhanced_filters),
                'error': str(e),
            }

    def _extract_fmp_filters(self, filters: Dict) -> Dict:
        """FMP API 직접 지원 필터 추출"""
        fmp_filters = {}
        for key, value in filters.items():
            if key in self.FMP_DIRECT_FILTERS and value is not None:
                fmp_param = self.FMP_DIRECT_FILTERS[key]
                fmp_filters[fmp_param] = value
        return fmp_filters

    def _extract_enhanced_filters(self, filters: Dict) -> Dict:
        """Enhanced (추가 API 필요) 필터 추출"""
        return {
            k: v for k, v in filters.items()
            if k in self.ENHANCED_FILTERS and v is not None
        }

    def _extract_client_filters(self, filters: Dict) -> Dict:
        """클라이언트 사이드 필터 추출"""
        return {
            k: v for k, v in filters.items()
            if k in self.CLIENT_FILTERABLE and v is not None
        }

    def _fetch_fmp_screener(self, fmp_params: Dict, limit: int) -> List[Dict]:
        """FMP company-screener API 호출"""
        try:
            # 캐시 키 생성
            cache_key = f'fmp:enhanced_screener:{hash(frozenset(fmp_params.items()))}:{limit}'
            cached = cache.get(cache_key)
            if cached:
                logger.debug("Enhanced 스크리너 캐시 HIT")
                return cached

            # FMP API 호출
            params = {'limit': limit, **fmp_params}
            response = self.fmp_client._make_request('/stable/company-screener', params)

            # 캐시 저장 (5분)
            cache.set(cache_key, response, 300)

            logger.info(f"FMP 스크리너 결과: {len(response)}개")
            return response

        except FMPAPIError:
            raise

    def _fetch_key_metrics_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        FMP key-metrics-ttm 배치 호출

        캐싱: Redis 1시간 TTL
        Rate Limit 대응: 캐시된 것 먼저 사용
        """
        result = {}
        uncached_symbols = []

        # 1. 캐시 확인
        for symbol in symbols:
            cache_key = f'fmp:metrics_ttm:{symbol}'
            cached = cache.get(cache_key)
            if cached:
                result[symbol] = cached
            else:
                uncached_symbols.append(symbol)

        logger.info(f"Metrics 캐시: {len(result)}개 HIT, {len(uncached_symbols)}개 MISS")

        # 2. 캐시 미스 종목 API 호출 (최대 20개씩, Rate Limit 고려)
        for symbol in uncached_symbols[:20]:
            try:
                data = self._fetch_single_key_metrics(symbol)
                if data:
                    result[symbol] = data
                    cache.set(f'fmp:metrics_ttm:{symbol}', data, self.METRICS_CACHE_TTL)
            except Exception as e:
                logger.warning(f"Metrics 조회 실패 ({symbol}): {e}")

        return result

    def _fetch_single_key_metrics(self, symbol: str) -> Optional[Dict]:
        """단일 종목 key-metrics-ttm 조회"""
        try:
            response = self.fmp_client._make_request(
                '/stable/key-metrics-ttm',
                params={'symbol': symbol.upper()}
            )

            if isinstance(response, list) and len(response) > 0:
                return response[0]
            return None

        except FMPAPIError as e:
            logger.warning(f"Key Metrics API 오류 ({symbol}): {e}")
            return None

    def _merge_metrics(
        self,
        stocks: List[Dict],
        metrics: Dict[str, Dict]
    ) -> List[Dict]:
        """
        종목 데이터에 펀더멘탈 metrics 병합

        FMP /stable/key-metrics-ttm API 응답 필드:
        - returnOnEquityTTM: decimal (1.5 = 150%)
        - returnOnAssetsTTM: decimal
        - earningsYieldTTM: 1/PE (역수 계산 필요)
        - priceToBookRatioTTM: P/B ratio
        - currentRatioTTM: 유동비율
        - debtToEquityTTM: 부채비율
        - netProfitMarginTTM: 순이익률 (decimal)
        """
        enriched = []
        for stock in stocks:
            symbol = stock.get('symbol')
            stock_copy = dict(stock)

            if symbol and symbol in metrics:
                m = metrics[symbol]

                # PE Ratio: earningsYieldTTM의 역수 (1/earningsYield)
                earnings_yield = m.get('earningsYieldTTM')
                if earnings_yield and earnings_yield > 0:
                    stock_copy['pe_ratio'] = round(1 / earnings_yield, 2)
                else:
                    stock_copy['pe_ratio'] = None

                # P/B Ratio
                stock_copy['pb_ratio'] = m.get('priceToBookRatioTTM')

                # ROE: decimal → percentage (1.5 → 150%)
                roe_decimal = m.get('returnOnEquityTTM')
                if roe_decimal is not None:
                    stock_copy['roe'] = round(roe_decimal * 100, 2)
                else:
                    stock_copy['roe'] = None

                # ROA: decimal → percentage
                roa_decimal = m.get('returnOnAssetsTTM')
                if roa_decimal is not None:
                    stock_copy['roa'] = round(roa_decimal * 100, 2)
                else:
                    stock_copy['roa'] = None

                # Debt to Equity
                stock_copy['debt_equity'] = m.get('debtToEquityTTM')

                # Current Ratio
                stock_copy['current_ratio'] = m.get('currentRatioTTM')

                # Profit Margin: decimal → percentage
                profit_margin_decimal = m.get('netProfitMarginTTM')
                if profit_margin_decimal is not None:
                    stock_copy['profit_margin'] = round(profit_margin_decimal * 100, 2)
                else:
                    stock_copy['profit_margin'] = None

                # EPS/Revenue Growth는 TTM API에서 직접 제공 안 됨 (간접 지표)
                stock_copy['eps_growth'] = m.get('netIncomePerShareTTM')
                stock_copy['revenue_growth'] = m.get('revenuePerShareTTM')

            enriched.append(stock_copy)

        return enriched

    def _apply_enhanced_filters(
        self,
        stocks: List[Dict],
        filters: Dict
    ) -> List[Dict]:
        """Enhanced 필터 적용 (PE, ROE 등)"""
        result = []

        for stock in stocks:
            if self._matches_enhanced_filters(stock, filters):
                result.append(stock)

        logger.info(f"Enhanced 필터 적용 후: {len(stocks)} → {len(result)}개")
        return result

    def _matches_enhanced_filters(self, stock: Dict, filters: Dict) -> bool:
        """단일 종목이 Enhanced 필터를 만족하는지 확인"""
        for filter_key, filter_value in filters.items():
            # 필터 키에서 필드명과 연산자 추출
            if filter_key.endswith('_min'):
                field = filter_key[:-4]
                operator = 'gte'
            elif filter_key.endswith('_max'):
                field = filter_key[:-4]
                operator = 'lte'
            else:
                field = filter_key
                operator = 'eq'

            # 종목의 해당 필드 값 가져오기
            stock_value = stock.get(field)

            # 데이터가 없으면 기본적으로 필터 통과 (데이터 없는 종목 제외하지 않음)
            # 단, Enhanced 필터의 경우 데이터 없으면 필터 미통과로 변경 가능
            if stock_value is None:
                # PE/ROE/EPS 등 핵심 필터는 데이터 없으면 제외
                if field in ('pe_ratio', 'roe', 'eps_growth', 'revenue_growth', 'debt_equity'):
                    return False
                continue

            try:
                stock_value = float(stock_value)
                filter_value = float(filter_value)
            except (ValueError, TypeError):
                continue

            if operator == 'gte' and stock_value < filter_value:
                return False
            elif operator == 'lte' and stock_value > filter_value:
                return False
            elif operator == 'eq' and stock_value != filter_value:
                return False

        return True

    def _apply_client_filters(
        self,
        stocks: List[Dict],
        filters: Dict
    ) -> List[Dict]:
        """클라이언트 사이드 필터 적용 (change_percent 등)"""
        result = []

        for stock in stocks:
            matches = True

            # change_percent 필터
            change_pct = stock.get('changesPercentage')
            if change_pct is not None:
                try:
                    change_pct = float(change_pct)

                    if 'change_percent_min' in filters:
                        if change_pct < float(filters['change_percent_min']):
                            matches = False

                    if 'change_percent_max' in filters:
                        if change_pct > float(filters['change_percent_max']):
                            matches = False
                except (ValueError, TypeError):
                    pass

            if matches:
                result.append(stock)

        return result

    def _sort_results(
        self,
        stocks: List[Dict],
        sort_by: str,
        sort_order: str
    ) -> List[Dict]:
        """결과 정렬"""
        reverse = sort_order.lower() == 'desc'

        # 정렬 필드 매핑
        field_map = {
            'pe': 'pe_ratio',
            'roe': 'roe',
            'marketCap': 'marketCap',
            'volume': 'volume',
            'change_percent': 'changesPercentage',
            'beta': 'beta',
        }
        sort_field = field_map.get(sort_by, sort_by)

        def get_sort_key(stock):
            value = stock.get(sort_field)
            if value is None:
                return float('-inf') if reverse else float('inf')
            try:
                return float(value)
            except (ValueError, TypeError):
                return value

        return sorted(stocks, key=get_sort_key, reverse=reverse)

    def has_enhanced_filters(self, filters: Dict) -> bool:
        """주어진 필터에 Enhanced 필터가 포함되어 있는지 확인"""
        return any(k in self.ENHANCED_FILTERS for k in filters.keys())

    def get_filter_type(self, filters: Dict) -> str:
        """필터 타입 반환 (instant 또는 enhanced)"""
        if self.has_enhanced_filters(filters):
            return 'enhanced'
        return 'instant'
