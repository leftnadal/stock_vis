"""
Market Movers 키워드 생성 컨텍스트 빌더

Overview + 뉴스를 결합하여 풍부한 컨텍스트를 구성합니다.
토큰 최적화를 통해 배치 처리 시 4000 토큰 이내로 유지합니다.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class KeywordContextBuilder:
    """
    Market Movers 키워드 생성을 위한 컨텍스트 빌더

    Features:
    - Overview 데이터 통합 (description, market_cap, pe_ratio 등)
    - 뉴스 데이터 통합 (최대 3개, 제목만)
    - 토큰 최적화 (description 200자 제한)
    - Fallback 전략 (데이터 없을 시)
    """

    # Overview description 최대 길이
    MAX_DESCRIPTION_LENGTH = 200

    # 뉴스 최대 개수
    MAX_NEWS_COUNT = 3

    # 토큰 추정치
    TOKENS_PER_CHAR_KO = 0.4  # 한국어 1자 ≈ 0.4 토큰
    TOKENS_PER_CHAR_EN = 0.25  # 영어 1자 ≈ 0.25 토큰

    def __init__(self):
        pass

    def build_stock_context(
        self,
        symbol: str,
        company_name: str,
        mover_type: str,
        price_data: Dict[str, Any],
        indicators: Dict[str, Any],
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        overview: Optional[Dict[str, Any]] = None,
        news: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        단일 종목 컨텍스트 구성

        Args:
            symbol: 종목 심볼
            company_name: 회사명
            mover_type: 'gainers', 'losers', 'actives'
            price_data: {'price', 'change_percent', 'volume', 'open', 'high', 'low'}
            indicators: {'rvol', 'trend_strength', 'sector_alpha', 'etf_sync_rate', 'volatility_pct'}
            sector: 섹터명
            industry: 산업명
            overview: Overview 데이터 (선택)
            news: 뉴스 리스트 (선택)

        Returns:
            {
                'basic': {...},
                'overview': {...},
                'news': [...],
                'indicators': {...},
                'has_overview': bool,
                'has_news': bool,
                'estimated_tokens': int
            }
        """
        context = {
            'basic': {
                'symbol': symbol,
                'company_name': company_name,
                'mover_type': mover_type,
                'sector': sector,
                'industry': industry,
                'price_data': price_data,
            },
            'overview': self._process_overview(overview) if overview else None,
            'news': self._process_news(news) if news else None,
            'indicators': indicators,
            'has_overview': bool(overview),
            'has_news': bool(news and len(news) > 0),
        }

        # 토큰 추정
        context['estimated_tokens'] = self._estimate_tokens(context)

        return context

    def _process_overview(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        """
        Overview 데이터 처리 (토큰 최적화)

        Args:
            overview: 원본 Overview 데이터

        Returns:
            처리된 Overview 데이터
        """
        processed = {}

        # Description (200자 제한)
        description = overview.get('description', '')
        if description:
            if len(description) > self.MAX_DESCRIPTION_LENGTH:
                description = description[:self.MAX_DESCRIPTION_LENGTH] + '...'
            processed['description'] = description

        # 핵심 재무 지표만 선택
        key_metrics = [
            'market_cap',
            'pe_ratio',
            '52_week_high',
            '52_week_low',
            'dividend_yield',
            'beta',
            'revenue_ttm',
            'profit_margin',
        ]

        for metric in key_metrics:
            if metric in overview and overview[metric] is not None:
                processed[metric] = overview[metric]

        return processed if processed else None

    def _process_news(self, news: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        뉴스 데이터 처리 (최대 3개, 제목만)

        Args:
            news: 원본 뉴스 리스트

        Returns:
            처리된 뉴스 리스트
        """
        processed = []

        for item in news[:self.MAX_NEWS_COUNT]:
            # 제목, 출처, sentiment만 포함
            processed.append({
                'title': item.get('title', ''),
                'source': item.get('source', ''),
                'sentiment': item.get('sentiment', 'neutral'),
                'published_at': item.get('published_at', ''),
            })

        return processed if processed else None

    def _estimate_tokens(self, context: Dict[str, Any]) -> int:
        """
        컨텍스트 토큰 추정

        Args:
            context: 컨텍스트 딕셔너리

        Returns:
            추정 토큰 수
        """
        total_chars = 0

        # Basic
        basic = context.get('basic', {})
        total_chars += len(str(basic.get('company_name', '')))
        total_chars += len(str(basic.get('sector', '')))
        total_chars += len(str(basic.get('industry', '')))
        total_chars += 100  # price_data 대략

        # Overview
        if context.get('overview'):
            overview = context['overview']
            total_chars += len(overview.get('description', ''))
            total_chars += 150  # 기타 지표들

        # News
        if context.get('news'):
            for item in context['news']:
                total_chars += len(item.get('title', ''))
                total_chars += len(item.get('source', ''))

        # Indicators
        total_chars += 200  # 5개 지표

        # 토큰 변환 (영어 + 한국어 혼합)
        estimated_tokens = int(total_chars * 0.3)  # 중간값

        return estimated_tokens

    def build_batch_contexts(
        self,
        stocks: List[Dict[str, Any]],
        max_tokens: int = 4000
    ) -> List[Dict[str, Any]]:
        """
        배치 처리용 컨텍스트 구성 (토큰 제한)

        Args:
            stocks: 종목 리스트 (각 dict는 build_stock_context 파라미터 포함)
            max_tokens: 최대 토큰 제한

        Returns:
            토큰 제한 내 종목 리스트
        """
        batch_contexts = []
        total_tokens = 0

        for stock in stocks:
            context = self.build_stock_context(**stock)

            # 토큰 제한 체크
            if total_tokens + context['estimated_tokens'] > max_tokens:
                logger.warning(
                    f"Token limit reached: {total_tokens} + {context['estimated_tokens']} > {max_tokens}. "
                    f"Stopping at {len(batch_contexts)} stocks."
                )
                break

            batch_contexts.append(context)
            total_tokens += context['estimated_tokens']

        logger.info(
            f"Batch contexts built: {len(batch_contexts)} stocks, "
            f"estimated {total_tokens} tokens"
        )

        return batch_contexts

    def get_fallback_keywords(self, mover_type: str) -> List[str]:
        """
        Fallback 키워드 (데이터 없을 시)

        Args:
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            기본 키워드 리스트
        """
        fallback_map = {
            'gainers': ["급등", "거래량 증가", "상승 모멘텀"],
            'losers': ["급락", "매도 압력", "하락 조정"],
            'actives': ["거래량 급증", "변동성 확대", "투자자 관심"],
        }

        return fallback_map.get(mover_type, ["변동성"])


class ContextEnricher:
    """
    컨텍스트 보강 헬퍼

    Overview/뉴스 데이터를 외부 소스에서 가져오는 로직
    """

    @staticmethod
    def fetch_overview(symbol: str) -> Optional[Dict[str, Any]]:
        """
        종목 Overview 조회 (stocks 앱 연동)

        Args:
            symbol: 종목 심볼

        Returns:
            Overview 데이터 또는 None
        """
        try:
            from stocks.models import Stock

            stock = Stock.objects.filter(symbol=symbol.upper()).first()
            if not stock:
                return None

            return {
                'description': stock.description or '',
                'market_cap': str(stock.market_cap) if stock.market_cap else None,
                'pe_ratio': float(stock.pe_ratio) if stock.pe_ratio else None,
                '52_week_high': float(stock.week_52_high) if stock.week_52_high else None,
                '52_week_low': float(stock.week_52_low) if stock.week_52_low else None,
                'dividend_yield': float(stock.dividend_yield) if stock.dividend_yield else None,
                'beta': float(stock.beta) if stock.beta else None,
            }

        except Exception as e:
            logger.warning(f"Failed to fetch overview for {symbol}: {e}")
            return None

    @staticmethod
    def fetch_news(symbol: str, days: int = 7, limit: int = 3) -> Optional[List[Dict[str, Any]]]:
        """
        종목 뉴스 조회 (news 앱 연동)

        Args:
            symbol: 종목 심볼
            days: 최근 N일 뉴스
            limit: 최대 뉴스 개수

        Returns:
            뉴스 리스트 또는 None
        """
        try:
            from news.models import NewsArticle
            from django.utils import timezone

            cutoff_date = timezone.now() - timedelta(days=days)

            articles = NewsArticle.objects.filter(
                symbols__icontains=symbol.upper(),
                published_at__gte=cutoff_date
            ).order_by('-published_at')[:limit]

            if not articles:
                return None

            news_list = []
            for article in articles:
                news_list.append({
                    'title': article.title,
                    'source': article.source,
                    'published_at': article.published_at.isoformat(),
                    'sentiment': article.sentiment or 'neutral',
                })

            return news_list if news_list else None

        except Exception as e:
            logger.warning(f"Failed to fetch news for {symbol}: {e}")
            return None

    @classmethod
    def enrich_stock_data(
        cls,
        symbol: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        종목 데이터 보강 (Overview + 뉴스 추가)

        Args:
            symbol: 종목 심볼
            **kwargs: build_stock_context에 전달할 기본 파라미터

        Returns:
            보강된 종목 데이터
        """
        enriched = dict(kwargs)
        enriched['symbol'] = symbol

        # Overview 추가
        if 'overview' not in enriched:
            enriched['overview'] = cls.fetch_overview(symbol)

        # 뉴스 추가
        if 'news' not in enriched:
            enriched['news'] = cls.fetch_news(symbol)

        return enriched
