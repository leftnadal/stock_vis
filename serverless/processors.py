"""
Market Movers 비즈니스 로직 레이어
"""
import logging
from typing import Dict, List, Optional
from django.utils import timezone

from serverless.models import MarketMover, StockKeyword
from serverless.services.keyword_service import KeywordGenerationService


logger = logging.getLogger(__name__)


class MarketMoversProcessor:
    """
    Market Movers 데이터 조합 및 변환 로직

    역할:
    - MarketMover + StockKeyword 조인
    - 응답 형식 구조화
    - 5개 지표 디스플레이 포맷팅
    """

    def __init__(self):
        self.keyword_service = KeywordGenerationService()

    def get_movers_with_keywords(
        self,
        date,
        mover_type: str
    ) -> List[Dict]:
        """
        Market Movers + 키워드 조회

        Args:
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            [
                {
                    'symbol': 'NVDA',
                    'company_name': 'NVIDIA Corporation',
                    'rank': 1,
                    'price': 525.32,
                    'change_percent': 8.45,
                    'volume': 52400000,
                    'sector': 'Technology',
                    'industry': 'Semiconductors',
                    'indicators': {...},
                    'keywords': [...]  # ⭐ 추가
                },
                ...
            ]
        """
        # 1. MarketMover 조회
        movers = MarketMover.objects.filter(
            date=date,
            mover_type=mover_type
        ).order_by('rank')

        # 2. 키워드 일괄 조회 (N+1 방지)
        symbols = [m.symbol for m in movers]
        keywords_map = self._get_keywords_map(symbols, date)

        # 3. 조합
        result = []
        for mover in movers:
            result.append({
                'symbol': mover.symbol,
                'company_name': mover.company_name,
                'rank': mover.rank,
                'price': float(mover.price),
                'change_percent': float(mover.change_percent),
                'volume': mover.volume,
                'sector': mover.sector,
                'industry': mover.industry,
                'ohlc': {
                    'open': float(mover.open_price) if mover.open_price else None,
                    'high': float(mover.high) if mover.high else None,
                    'low': float(mover.low) if mover.low else None,
                },
                'indicators': {
                    'rvol': mover.rvol_display,
                    'trend': mover.trend_display,
                    'sector_alpha': self._format_percentage(mover.sector_alpha),
                    'etf_sync': str(mover.etf_sync_rate) if mover.etf_sync_rate else None,
                    'volatility': f"P{mover.volatility_pct}" if mover.volatility_pct else None,
                },
                'keywords': keywords_map.get(mover.symbol, []),  # ⭐ 키워드 추가
            })

        return result

    def _get_keywords_map(
        self,
        symbols: List[str],
        date
    ) -> Dict[str, List[str]]:
        """
        키워드 일괄 조회 (N+1 방지)

        Args:
            symbols: 심볼 리스트
            date: 날짜

        Returns:
            {'NVDA': [...], 'TSLA': [...]}
        """
        keywords_qs = StockKeyword.objects.filter(
            symbol__in=symbols,
            date=date,
            status='completed'
        ).values('symbol', 'keywords')

        return {
            kw['symbol']: kw['keywords']
            for kw in keywords_qs
        }

    def _format_percentage(self, value) -> Optional[str]:
        """
        Decimal을 % 포맷으로 변환

        Args:
            value: Decimal 값

        Returns:
            "+2.3%" 형식 문자열 또는 None
        """
        if value is None:
            return None
        try:
            return f"{value:+.1f}%"
        except (ValueError, TypeError):
            return None
