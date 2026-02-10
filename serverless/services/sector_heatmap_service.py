"""
섹터 히트맵 서비스 (Lambda 전환 대상)

11개 섹터의 일일 성과를 계산하여 히트맵 시각화에 사용합니다.

데이터 소스: FMP API (sector performance, stock list by sector)
"""
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List

from django.core.cache import cache
from django.db import transaction

from serverless.models import SectorPerformance, SectorETFMapping
from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


class SectorHeatmapService:
    """
    섹터별 성과 히트맵 서비스

    11개 GICS 섹터의 일일 성과를 계산하고 저장합니다.

    Usage:
        service = SectorHeatmapService()
        heatmap = service.calculate_sector_performance()
        top_movers = service.get_top_movers_by_sector('Technology', limit=5)
    """

    # 11개 GICS 섹터 및 대표 ETF
    SECTORS = {
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financial Services': 'XLF',
        'Consumer Cyclical': 'XLY',
        'Industrials': 'XLI',
        'Energy': 'XLE',
        'Communication Services': 'XLC',
        'Real Estate': 'XLRE',
        'Utilities': 'XLU',
        'Basic Materials': 'XLB',
        'Consumer Defensive': 'XLP',
    }

    # 섹터 한글명
    SECTOR_NAMES_KO = {
        'Technology': '기술',
        'Healthcare': '헬스케어',
        'Financial Services': '금융',
        'Consumer Cyclical': '경기소비재',
        'Industrials': '산업재',
        'Energy': '에너지',
        'Communication Services': '통신',
        'Real Estate': '부동산',
        'Utilities': '유틸리티',
        'Basic Materials': '소재',
        'Consumer Defensive': '필수소비재',
    }

    # 캐시 TTL
    CACHE_TTL = 300  # 5분

    def __init__(self):
        self.fmp_client = FMPClient()

    def calculate_sector_performance(self, target_date: Optional[date] = None) -> List[Dict]:
        """
        일일 섹터별 성과 계산

        Args:
            target_date: 계산 대상 날짜 (기본값: 오늘)

        Returns:
            섹터별 성과 리스트

        Raises:
            FMPAPIError: FMP API 호출 실패 시
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"섹터 히트맵 계산 시작: {target_date}")

        results = []

        try:
            for sector_name, etf_symbol in self.SECTORS.items():
                try:
                    sector_data = self._calculate_single_sector(
                        target_date, sector_name, etf_symbol
                    )
                    if sector_data:
                        results.append(sector_data)
                except Exception as e:
                    logger.warning(f"섹터 계산 실패 {sector_name}: {e}")
                    continue

            # DB 저장
            with transaction.atomic():
                for sector_data in results:
                    SectorPerformance.objects.update_or_create(
                        date=target_date,
                        sector=sector_data['sector'],
                        defaults={
                            'return_pct': sector_data['return_pct'],
                            'market_cap': sector_data['market_cap'],
                            'stock_count': sector_data['stock_count'],
                            'etf_symbol': sector_data['etf_symbol'],
                            'etf_price': sector_data.get('etf_price'),
                            'etf_change_pct': sector_data.get('etf_change_pct'),
                            'top_gainers': sector_data.get('top_gainers', []),
                            'top_losers': sector_data.get('top_losers', []),
                        }
                    )

            logger.info(f"섹터 히트맵 저장 완료: {len(results)}개 섹터")

            # 캐시 무효화
            self._invalidate_cache(target_date)

            return results

        except FMPAPIError as e:
            logger.error(f"섹터 히트맵 계산 실패 (FMP API): {e}")
            raise
        except Exception as e:
            logger.exception(f"섹터 히트맵 계산 중 예기치 않은 오류: {e}")
            return []

    def get_sector_heatmap(self, target_date: Optional[date] = None) -> Dict:
        """
        섹터 히트맵 데이터 조회 (캐시 우선)

        Args:
            target_date: 조회 날짜 (기본값: 오늘)

        Returns:
            {
                'date': '2026-01-27',
                'sectors': [
                    {
                        'name': 'Technology',
                        'name_ko': '기술',
                        'return_pct': 2.5,
                        'market_cap': 15000000000000,
                        'stock_count': 450,
                        'color': '#22c55e',
                        'etf_symbol': 'XLK',
                        ...
                    }
                ]
            }
        """
        if target_date is None:
            target_date = date.today()

        cache_key = f'sector_heatmap:{target_date}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"섹터 히트맵 캐시 HIT: {target_date}")
            return cached

        sectors = SectorPerformance.objects.filter(date=target_date).order_by('-return_pct')

        if not sectors.exists():
            logger.warning(f"섹터 히트맵 데이터 없음: {target_date}")
            return {'date': target_date.isoformat(), 'sectors': []}

        result = {
            'date': target_date.isoformat(),
            'sectors': [self._serialize_sector(s) for s in sectors]
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def get_top_movers_by_sector(
        self,
        sector: str,
        limit: int = 5,
        target_date: Optional[date] = None
    ) -> Dict:
        """
        특정 섹터의 Top Movers 조회

        Args:
            sector: 섹터명 (예: 'Technology')
            limit: 반환할 종목 수 (기본값: 5)
            target_date: 조회 날짜 (기본값: 오늘)

        Returns:
            {
                'sector': 'Technology',
                'date': '2026-01-27',
                'top_gainers': [...],
                'top_losers': [...]
            }
        """
        if target_date is None:
            target_date = date.today()

        cache_key = f'sector_top_movers:{sector}:{target_date}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            sector_perf = SectorPerformance.objects.get(date=target_date, sector=sector)
            result = {
                'sector': sector,
                'sector_ko': self.SECTOR_NAMES_KO.get(sector, sector),
                'date': target_date.isoformat(),
                'return_pct': float(sector_perf.return_pct),
                'top_gainers': sector_perf.top_gainers[:limit],
                'top_losers': sector_perf.top_losers[:limit],
            }
            cache.set(cache_key, result, self.CACHE_TTL)
            return result
        except SectorPerformance.DoesNotExist:
            return {
                'sector': sector,
                'sector_ko': self.SECTOR_NAMES_KO.get(sector, sector),
                'date': target_date.isoformat(),
                'return_pct': 0,
                'top_gainers': [],
                'top_losers': [],
            }

    def get_sector_by_stock(self, symbol: str) -> Optional[str]:
        """
        종목의 섹터 조회

        Args:
            symbol: 종목 심볼

        Returns:
            섹터명 또는 None
        """
        cache_key = f'stock_sector:{symbol.upper()}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            profile = self.fmp_client.get_company_profile(symbol.upper())
            sector = profile.get('sector')
            if sector:
                cache.set(cache_key, sector, 86400)  # 24시간 캐시
            return sector
        except FMPAPIError:
            return None

    # ========================================
    # Private Methods
    # ========================================

    def _calculate_single_sector(
        self,
        target_date: date,
        sector_name: str,
        etf_symbol: str
    ) -> Optional[Dict]:
        """
        단일 섹터 성과 계산
        """
        try:
            # ETF 시세 조회
            etf_quote = self.fmp_client.get_quote(etf_symbol)

            etf_price = etf_quote.get('price')
            # FMP Quote API는 'changePercentage' (단수) 반환
            etf_change_pct = etf_quote.get('changePercentage') or etf_quote.get('changesPercentage', 0)

            # 섹터 성과는 ETF 수익률로 대표
            return_pct = Decimal(str(etf_change_pct or 0)).quantize(
                Decimal('0.001'), rounding=ROUND_HALF_UP
            )

            # 시가총액 (ETF AUM으로 추정하거나 고정값 사용)
            market_cap = self._estimate_sector_market_cap(sector_name)

            # 종목 수 (섹터별 대략적인 수)
            stock_count = self._estimate_sector_stock_count(sector_name)

            # Top Movers (gainers/losers에서 필터링)
            top_gainers, top_losers = self._get_sector_top_movers(sector_name)

            return {
                'sector': sector_name,
                'sector_ko': self.SECTOR_NAMES_KO.get(sector_name, sector_name),
                'return_pct': return_pct,
                'market_cap': market_cap,
                'stock_count': stock_count,
                'etf_symbol': etf_symbol,
                'etf_price': Decimal(str(etf_price)) if etf_price else None,
                'etf_change_pct': Decimal(str(etf_change_pct)) if etf_change_pct else None,
                'top_gainers': top_gainers,
                'top_losers': top_losers,
            }

        except FMPAPIError as e:
            logger.warning(f"섹터 ETF 조회 실패 {etf_symbol}: {e}")
            return None

    def _get_sector_top_movers(self, sector_name: str) -> tuple:
        """섹터 내 Top Gainers/Losers 조회"""
        try:
            gainers = self.fmp_client.get_market_gainers()
            losers = self.fmp_client.get_market_losers()

            # 섹터 필터링 (FMP API 응답에 sector 필드가 없으면 빈 리스트)
            top_gainers = []
            top_losers = []

            for stock in gainers[:10]:
                # sector 필드 확인 (없으면 profile 조회 비용이 크므로 스킵)
                if stock.get('sector') == sector_name:
                    top_gainers.append({
                        'symbol': stock.get('symbol'),
                        'name': stock.get('name'),
                        'change_pct': stock.get('changesPercentage'),
                    })

            for stock in losers[:10]:
                if stock.get('sector') == sector_name:
                    top_losers.append({
                        'symbol': stock.get('symbol'),
                        'name': stock.get('name'),
                        'change_pct': stock.get('changesPercentage'),
                    })

            return top_gainers[:3], top_losers[:3]

        except FMPAPIError:
            return [], []

    def _estimate_sector_market_cap(self, sector_name: str) -> int:
        """섹터 시가총액 추정 (고정값, 실제로는 API 필요)"""
        market_caps = {
            'Technology': 15_000_000_000_000,      # 15T
            'Healthcare': 8_000_000_000_000,       # 8T
            'Financial Services': 10_000_000_000_000,  # 10T
            'Consumer Cyclical': 6_000_000_000_000,    # 6T
            'Industrials': 5_000_000_000_000,      # 5T
            'Energy': 4_000_000_000_000,           # 4T
            'Communication Services': 4_500_000_000_000,  # 4.5T
            'Real Estate': 2_000_000_000_000,      # 2T
            'Utilities': 2_000_000_000_000,        # 2T
            'Basic Materials': 1_500_000_000_000,  # 1.5T
            'Consumer Defensive': 3_000_000_000_000,   # 3T
        }
        return market_caps.get(sector_name, 1_000_000_000_000)

    def _estimate_sector_stock_count(self, sector_name: str) -> int:
        """섹터 내 종목 수 추정 (고정값)"""
        stock_counts = {
            'Technology': 450,
            'Healthcare': 380,
            'Financial Services': 400,
            'Consumer Cyclical': 350,
            'Industrials': 320,
            'Energy': 120,
            'Communication Services': 80,
            'Real Estate': 200,
            'Utilities': 60,
            'Basic Materials': 100,
            'Consumer Defensive': 100,
        }
        return stock_counts.get(sector_name, 100)

    def _get_heatmap_color(self, return_pct: float) -> str:
        """수익률에 따른 히트맵 색상 반환"""
        if return_pct >= 3.0:
            return '#15803d'  # green-700
        elif return_pct >= 1.5:
            return '#22c55e'  # green-500
        elif return_pct >= 0.5:
            return '#86efac'  # green-300
        elif return_pct >= -0.5:
            return '#fef08a'  # yellow-200
        elif return_pct >= -1.5:
            return '#fca5a5'  # red-300
        elif return_pct >= -3.0:
            return '#ef4444'  # red-500
        else:
            return '#b91c1c'  # red-700

    def _serialize_sector(self, sector: SectorPerformance) -> Dict:
        """SectorPerformance 객체를 딕셔너리로 변환"""
        return_pct = float(sector.return_pct)
        return {
            'name': sector.sector,
            'name_ko': self.SECTOR_NAMES_KO.get(sector.sector, sector.sector),
            'return_pct': return_pct,
            'market_cap': sector.market_cap,
            'stock_count': sector.stock_count,
            'etf_symbol': sector.etf_symbol,
            'etf_price': float(sector.etf_price) if sector.etf_price else None,
            'etf_change_pct': float(sector.etf_change_pct) if sector.etf_change_pct else None,
            'color': self._get_heatmap_color(return_pct),
            'top_gainers': sector.top_gainers,
            'top_losers': sector.top_losers,
        }

    def _invalidate_cache(self, target_date: date):
        """관련 캐시 무효화"""
        cache.delete(f'sector_heatmap:{target_date}')
        for sector in self.SECTORS.keys():
            for limit in [3, 5, 10]:
                cache.delete(f'sector_top_movers:{sector}:{target_date}:{limit}')
