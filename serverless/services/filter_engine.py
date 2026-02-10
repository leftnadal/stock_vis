"""
동적 필터 엔진 (Lambda 전환 대상)

50개 이상의 필터를 동적으로 적용하고 FMP API와 클라이언트 사이드 필터링을 조합합니다.
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Any

from django.core.cache import cache

from serverless.models import ScreenerFilter
from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


class FilterEngine:
    """
    동적 필터 적용 엔진

    FMP API 지원 필터는 서버 사이드에서 적용하고,
    미지원 필터는 클라이언트 사이드에서 필터링합니다.

    Usage:
        engine = FilterEngine()
        results = engine.apply_filters({
            'pe_ratio': {'max': 20},
            'roe': {'min': 15},
            'sector': ['Technology', 'Healthcare']
        })
    """

    # FMP API 직접 지원 필터 파라미터 매핑
    FMP_PARAM_MAP = {
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
        'country': 'country',
    }

    # 클라이언트 사이드 필터 (FMP API 미지원)
    CLIENT_SIDE_FILTERS = {
        'pe_ratio_min', 'pe_ratio_max',
        'pb_ratio_min', 'pb_ratio_max',
        'peg_ratio_min', 'peg_ratio_max',
        'roe_min', 'roe_max',
        'roa_min', 'roa_max',
        'debt_equity_min', 'debt_equity_max',
        'current_ratio_min', 'current_ratio_max',
        'eps_growth_min', 'eps_growth_max',
        'revenue_growth_min', 'revenue_growth_max',
        'profit_margin_min', 'profit_margin_max',
        'rsi_min', 'rsi_max',
        'ma_cross',
        'change_percent_min', 'change_percent_max',
    }

    def __init__(self):
        self.fmp_client = FMPClient()

    def apply_filters(
        self,
        filters_dict: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        sort_by: str = 'marketCap',
        sort_order: str = 'desc'
    ) -> Dict:
        """
        필터 적용

        Args:
            filters_dict: 필터 조건 딕셔너리
                예: {
                    'market_cap_min': 1000000000,
                    'pe_ratio_max': 20,
                    'sector': ['Technology', 'Healthcare']
                }
            limit: 결과 개수
            offset: 페이지 오프셋
            sort_by: 정렬 기준
            sort_order: 정렬 방향 ('asc' or 'desc')

        Returns:
            {
                'results': [...],
                'count': 234,
                'total_pages': 5,
                'current_page': 1,
                'filters_applied': {...}
            }
        """
        logger.info(f"필터 적용: {len(filters_dict)}개 조건, limit={limit}")

        # 필터 분리: FMP API용 vs 클라이언트 사이드
        fmp_params, client_filters = self._split_filters(filters_dict)

        try:
            # FMP API 호출
            all_stocks = self._fetch_from_fmp(fmp_params, limit=1000)

            # 클라이언트 사이드 필터링
            if client_filters:
                filtered_stocks = self._apply_client_filters(all_stocks, client_filters)
            else:
                filtered_stocks = all_stocks

            # 정렬
            filtered_stocks = self._sort_results(filtered_stocks, sort_by, sort_order)

            # 페이지네이션
            total_count = len(filtered_stocks)
            total_pages = (total_count + limit - 1) // limit
            current_page = (offset // limit) + 1

            paginated = filtered_stocks[offset:offset + limit]

            return {
                'results': paginated,
                'count': total_count,
                'total_pages': total_pages,
                'current_page': current_page,
                'page_size': limit,
                'filters_applied': {
                    'fmp_filters': list(fmp_params.keys()),
                    'client_filters': list(client_filters.keys()),
                },
            }

        except FMPAPIError as e:
            logger.error(f"FMP API 오류: {e}")
            return {
                'results': [],
                'count': 0,
                'error': str(e),
            }

    def validate_filters(self, filters_dict: Dict[str, Any]) -> Dict:
        """
        필터 유효성 검증

        Args:
            filters_dict: 검증할 필터 딕셔너리

        Returns:
            {
                'valid': True/False,
                'errors': [...],
                'warnings': [...]
            }
        """
        errors = []
        warnings = []

        for filter_key, filter_value in filters_dict.items():
            # 알려진 필터인지 확인
            if not self._is_known_filter(filter_key):
                warnings.append(f"알 수 없는 필터: {filter_key}")
                continue

            # 값 타입 검증
            if not self._validate_filter_value(filter_key, filter_value):
                errors.append(f"잘못된 값: {filter_key}={filter_value}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }

    def get_available_filters(self) -> List[Dict]:
        """
        사용 가능한 필터 목록 반환

        Returns:
            카테고리별 필터 리스트
        """
        cache_key = 'screener_available_filters'
        cached = cache.get(cache_key)
        if cached:
            return cached

        filters = ScreenerFilter.objects.filter(is_active=True).order_by(
            'category', 'display_order'
        )

        result = {}
        for f in filters:
            if f.category not in result:
                result[f.category] = []
            result[f.category].append({
                'id': f.filter_id,
                'label': f.label,
                'label_ko': f.label_ko,
                'operator_type': f.operator_type,
                'unit': f.unit,
                'min_value': float(f.min_value) if f.min_value else None,
                'max_value': float(f.max_value) if f.max_value else None,
                'default_min': float(f.default_min) if f.default_min else None,
                'default_max': float(f.default_max) if f.default_max else None,
                'options': f.options,
                'is_premium': f.is_premium,
                'is_popular': f.is_popular,
                'tooltip_key': f.tooltip_key,
            })

        cache.set(cache_key, result, 3600)  # 1시간 캐시
        return result

    # ========================================
    # Private Methods
    # ========================================

    def _split_filters(self, filters_dict: Dict) -> tuple:
        """FMP API 필터와 클라이언트 사이드 필터 분리"""
        fmp_params = {}
        client_filters = {}

        for key, value in filters_dict.items():
            if key in self.FMP_PARAM_MAP:
                fmp_param = self.FMP_PARAM_MAP[key]
                fmp_params[fmp_param] = value
            elif key in self.CLIENT_SIDE_FILTERS:
                client_filters[key] = value
            else:
                # 알 수 없는 필터는 클라이언트 사이드로
                client_filters[key] = value

        return fmp_params, client_filters

    def _fetch_from_fmp(self, fmp_params: Dict, limit: int = 1000) -> List[Dict]:
        """FMP API에서 종목 조회"""
        cache_key = f'fmp_screener:{hash(frozenset(fmp_params.items()))}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug("FMP 스크리너 캐시 HIT")
            return cached

        # FMP API 호출 (기존 stocks 앱의 서비스 활용 가능)
        try:
            # FMP /stable/company-screener 엔드포인트 직접 호출
            params = {'limit': limit, **fmp_params}
            endpoint = '/stable/company-screener'

            response = self.fmp_client._make_request(endpoint, params)

            # 캐시 저장 (5분)
            cache.set(cache_key, response, 300)

            return response

        except FMPAPIError:
            raise

    def _apply_client_filters(
        self,
        stocks: List[Dict],
        filters: Dict
    ) -> List[Dict]:
        """클라이언트 사이드 필터 적용"""
        result = []

        for stock in stocks:
            if self._matches_all_filters(stock, filters):
                result.append(stock)

        return result

    def _matches_all_filters(self, stock: Dict, filters: Dict) -> bool:
        """단일 종목이 모든 필터 조건을 만족하는지 확인"""
        for filter_key, filter_value in filters.items():
            if not self._matches_filter(stock, filter_key, filter_value):
                return False
        return True

    def _matches_filter(self, stock: Dict, filter_key: str, filter_value: Any) -> bool:
        """단일 필터 조건 매칭"""
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

        # 필드명 매핑 (snake_case → API 필드명)
        field_map = {
            'pe_ratio': 'pe',
            'pb_ratio': 'priceToBook',
            'peg_ratio': 'peg',
            'roe': 'roe',
            'roa': 'roa',
            'debt_equity': 'debtToEquity',
            'current_ratio': 'currentRatio',
            'eps_growth': 'epsGrowth',
            'revenue_growth': 'revenueGrowth',
            'profit_margin': 'grossProfitMargin',
            'rsi': 'rsi',
            'change_percent': 'changesPercentage',
        }

        actual_field = field_map.get(field, field)
        stock_value = stock.get(actual_field)

        if stock_value is None:
            return True  # 데이터 없으면 통과 (필터 제외)

        try:
            stock_value = float(stock_value)
            filter_value = float(filter_value)
        except (ValueError, TypeError):
            return True

        if operator == 'gte':
            return stock_value >= filter_value
        elif operator == 'lte':
            return stock_value <= filter_value
        elif operator == 'eq':
            return stock_value == filter_value

        return True

    def _sort_results(
        self,
        stocks: List[Dict],
        sort_by: str,
        sort_order: str
    ) -> List[Dict]:
        """결과 정렬"""
        reverse = sort_order.lower() == 'desc'

        def get_sort_key(stock):
            value = stock.get(sort_by)
            if value is None:
                return float('-inf') if reverse else float('inf')
            try:
                return float(value)
            except (ValueError, TypeError):
                return value

        return sorted(stocks, key=get_sort_key, reverse=reverse)

    def _is_known_filter(self, filter_key: str) -> bool:
        """알려진 필터인지 확인"""
        return (
            filter_key in self.FMP_PARAM_MAP or
            filter_key in self.CLIENT_SIDE_FILTERS or
            filter_key.replace('_min', '').replace('_max', '') in {
                'market_cap', 'price', 'volume', 'beta', 'dividend',
                'pe_ratio', 'pb_ratio', 'roe', 'roa', 'change_percent',
            }
        )

    def _validate_filter_value(self, filter_key: str, value: Any) -> bool:
        """필터 값 유효성 검증"""
        if value is None:
            return True

        # 숫자 필터
        if filter_key.endswith(('_min', '_max')):
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        # 리스트 필터 (sector, exchange)
        if filter_key in ('sector', 'exchange'):
            if isinstance(value, list):
                return all(isinstance(v, str) for v in value)
            return isinstance(value, str)

        # Boolean 필터
        if filter_key in ('is_etf', 'is_actively_trading'):
            return isinstance(value, bool)

        return True
