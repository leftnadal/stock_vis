"""
FRED API Client

Federal Reserve Economic Data API
- 무료: 분당 120회, 일일 무제한
- 경제 지표: GDP, CPI, 실업률, 금리 등
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class FREDClient:
    """FRED API 클라이언트"""

    BASE_URL = "https://api.stlouisfed.org/fred"

    # 주요 FRED 시리즈 코드
    SERIES_CODES = {
        # 금리
        'FEDFUNDS': 'Federal Funds Effective Rate',
        'DGS2': '2-Year Treasury Constant Maturity',
        'DGS10': '10-Year Treasury Constant Maturity',
        'DGS30': '30-Year Treasury Constant Maturity',
        'T10Y2Y': '10-Year Treasury Minus 2-Year Treasury',

        # 인플레이션
        'CPIAUCSL': 'Consumer Price Index for All Urban Consumers',
        'CPILFESL': 'Core CPI (Less Food and Energy)',
        'PCEPI': 'Personal Consumption Expenditures Price Index',
        'PCEPILFE': 'Core PCE',

        # 고용
        'UNRATE': 'Unemployment Rate',
        'PAYEMS': 'All Employees, Total Nonfarm',
        'ICSA': 'Initial Claims',
        'CIVPART': 'Labor Force Participation Rate',

        # 성장
        'GDP': 'Gross Domestic Product',
        'GDPC1': 'Real GDP',

        # 변동성 및 신용
        'VIXCLS': 'CBOE Volatility Index (VIX)',
        'BAMLH0A0HYM2': 'High Yield Bond Spread',

        # 통화
        'M2SL': 'M2 Money Stock',
        'DTWEXBGS': 'Trade Weighted U.S. Dollar Index',
    }

    def __init__(self, api_key: str = None, request_delay: float = 0.5):
        """
        Args:
            api_key: FRED API 키 (없으면 settings에서 로드)
            request_delay: 요청 간 대기 시간 (초)
        """
        self.api_key = api_key or getattr(settings, 'FRED_API_KEY', None)
        self.request_delay = request_delay
        self.last_request_time = 0

        if not self.api_key:
            logger.warning("FRED API Key not found. Set FRED_API_KEY in settings.")

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        FRED API 요청

        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터

        Returns:
            API 응답 데이터
        """
        # API 키 추가
        params['api_key'] = self.api_key
        params['file_type'] = 'json'

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"FRED API Request: {endpoint}")

        try:
            response = requests.get(url, params=params, timeout=30)
            self.last_request_time = time.time()

            if response.status_code != 200:
                logger.error(f"FRED API Error {response.status_code}: {response.text}")
                response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"FRED API Request failed: {e}")
            raise

    def get_series_info(self, series_id: str) -> Dict[str, Any]:
        """
        시리즈 메타데이터 조회

        Args:
            series_id: FRED 시리즈 ID (예: 'GDP', 'UNRATE')

        Returns:
            시리즈 정보
        """
        data = self._make_request('series', {'series_id': series_id})
        if 'seriess' in data and len(data['seriess']) > 0:
            return data['seriess'][0]
        return {}

    def get_series_observations(
        self,
        series_id: str,
        observation_start: str = None,
        observation_end: str = None,
        limit: int = 100,
        sort_order: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        시리즈 데이터 조회

        Args:
            series_id: FRED 시리즈 ID
            observation_start: 시작일 (YYYY-MM-DD)
            observation_end: 종료일 (YYYY-MM-DD)
            limit: 반환할 데이터 수
            sort_order: 정렬 순서 (asc/desc)

        Returns:
            관측값 리스트
        """
        params = {
            'series_id': series_id,
            'limit': str(limit),
            'sort_order': sort_order,
        }

        if observation_start:
            params['observation_start'] = observation_start
        if observation_end:
            params['observation_end'] = observation_end

        data = self._make_request('series/observations', params)
        return data.get('observations', [])

    def get_latest_value(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        최신 값 조회

        Args:
            series_id: FRED 시리즈 ID

        Returns:
            최신 관측값 또는 None
        """
        observations = self.get_series_observations(
            series_id,
            limit=1,
            sort_order='desc'
        )
        if observations:
            obs = observations[0]
            return {
                'date': obs.get('date'),
                'value': self._parse_value(obs.get('value')),
                'series_id': series_id,
            }
        return None

    def get_yield_spread(self) -> Dict[str, Any]:
        """
        수익률 곡선 스프레드 (10Y - 2Y) 조회

        Returns:
            스프레드 데이터
        """
        # T10Y2Y 시리즈 사용 (FRED에서 계산해 제공)
        spread_data = self.get_latest_value('T10Y2Y')

        if spread_data:
            spread_value = float(spread_data['value']) if spread_data['value'] else 0

            # 상태 판단
            if spread_value < 0:
                status = 'inverted'
            elif spread_value < 0.5:
                status = 'flattening'
            elif spread_value < 2.5:
                status = 'normal'
            else:
                status = 'steep'

            return {
                'spread': spread_value,
                'status': status,
                'date': spread_data['date'],
            }

        return {'spread': None, 'status': 'unknown', 'date': None}

    def get_interest_rates(self) -> Dict[str, Any]:
        """
        주요 금리 조회

        Returns:
            금리 데이터
        """
        rates = {}
        rate_series = ['FEDFUNDS', 'DGS2', 'DGS10', 'DGS30']

        for series_id in rate_series:
            try:
                data = self.get_latest_value(series_id)
                if data and data['value'] is not None:
                    rates[series_id] = {
                        'value': float(data['value']),
                        'date': data['date'],
                        'name': self.SERIES_CODES.get(series_id, series_id),
                    }
            except Exception as e:
                logger.error(f"Failed to fetch {series_id}: {e}")

        return rates

    def get_inflation_data(self) -> Dict[str, Any]:
        """
        인플레이션 지표 조회

        Returns:
            CPI, Core CPI, PCE 데이터
        """
        inflation = {}
        inflation_series = ['CPIAUCSL', 'CPILFESL', 'PCEPI']

        for series_id in inflation_series:
            try:
                # 최근 13개월 데이터로 YoY 계산
                observations = self.get_series_observations(
                    series_id,
                    limit=13,
                    sort_order='desc'
                )

                if len(observations) >= 13:
                    latest = self._parse_value(observations[0]['value'])
                    year_ago = self._parse_value(observations[12]['value'])

                    if latest and year_ago and year_ago > 0:
                        yoy_change = ((latest - year_ago) / year_ago) * 100
                        inflation[series_id] = {
                            'current': latest,
                            'year_ago': year_ago,
                            'yoy_change': round(yoy_change, 2),
                            'date': observations[0]['date'],
                            'name': self.SERIES_CODES.get(series_id, series_id),
                        }

            except Exception as e:
                logger.error(f"Failed to fetch {series_id}: {e}")

        return inflation

    def get_employment_data(self) -> Dict[str, Any]:
        """
        고용 지표 조회

        Returns:
            실업률, NFP 등 고용 데이터
        """
        employment = {}

        # 실업률
        try:
            unrate = self.get_latest_value('UNRATE')
            if unrate and unrate['value']:
                employment['unemployment_rate'] = {
                    'value': float(unrate['value']),
                    'date': unrate['date'],
                }
        except Exception as e:
            logger.error(f"Failed to fetch UNRATE: {e}")

        # NFP (전월 대비 변화)
        try:
            observations = self.get_series_observations('PAYEMS', limit=2)
            if len(observations) >= 2:
                current = self._parse_value(observations[0]['value'])
                previous = self._parse_value(observations[1]['value'])

                if current and previous:
                    change = current - previous
                    employment['nonfarm_payrolls'] = {
                        'current': current,
                        'change': change,  # 천 명 단위
                        'date': observations[0]['date'],
                    }
        except Exception as e:
            logger.error(f"Failed to fetch PAYEMS: {e}")

        # 초기실업수당청구
        try:
            icsa = self.get_latest_value('ICSA')
            if icsa and icsa['value']:
                employment['initial_claims'] = {
                    'value': float(icsa['value']),
                    'date': icsa['date'],
                }
        except Exception as e:
            logger.error(f"Failed to fetch ICSA: {e}")

        return employment

    def get_vix(self) -> Optional[Dict[str, Any]]:
        """
        VIX 지수 조회

        Returns:
            VIX 데이터
        """
        try:
            vix = self.get_latest_value('VIXCLS')
            if vix and vix['value']:
                value = float(vix['value'])

                # VIX 레벨 판단
                if value >= 30:
                    level = 'extreme_high'
                elif value >= 20:
                    level = 'high'
                elif value >= 12:
                    level = 'normal'
                else:
                    level = 'low'

                return {
                    'value': value,
                    'level': level,
                    'date': vix['date'],
                }
        except Exception as e:
            logger.error(f"Failed to fetch VIX: {e}")

        return None

    def get_gdp_growth(self) -> Optional[Dict[str, Any]]:
        """
        GDP 성장률 조회

        Returns:
            GDP 데이터
        """
        try:
            # 실질 GDP (분기별, 연율화)
            observations = self.get_series_observations('GDPC1', limit=5)

            if len(observations) >= 2:
                latest = self._parse_value(observations[0]['value'])
                previous = self._parse_value(observations[1]['value'])

                if latest and previous and previous > 0:
                    # 분기 성장률 연율화
                    qoq_growth = ((latest / previous) - 1) * 100
                    annualized = ((1 + qoq_growth / 100) ** 4 - 1) * 100

                    return {
                        'real_gdp': latest,
                        'qoq_growth': round(qoq_growth, 2),
                        'annualized_growth': round(annualized, 2),
                        'date': observations[0]['date'],
                    }
        except Exception as e:
            logger.error(f"Failed to fetch GDP: {e}")

        return None

    def _parse_value(self, value: str) -> Optional[float]:
        """FRED 값 파싱 (빈 값, '.' 처리)"""
        if value is None or value == '.' or value == '':
            return None
        try:
            return float(value)
        except ValueError:
            return None
