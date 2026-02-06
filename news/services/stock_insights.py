"""
뉴스 기반 종목 인사이트 서비스

팩트 중심의 종목 정보를 제공합니다.
- 뉴스 언급 현황
- 감성 분포 (긍정/부정/중립)
- 키워드별 뉴스 헤드라인
- 시장 데이터 (선택적)

"추천", "점수" 등 주관적 표현을 배제하고 사실 기반 정보만 제공합니다.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.core.cache import cache
from django.db.models import Avg, Count, Q
from django.utils import timezone

from ..models import DailyNewsKeyword, NewsArticle, NewsEntity

logger = logging.getLogger(__name__)


class NewsBasedStockInsights:
    """
    뉴스 기반 종목 인사이트 서비스

    팩트 중심 접근:
    1. 뉴스 언급 횟수 및 분포
    2. 감성 분포 (positive/negative/neutral 건수)
    3. 키워드별 뉴스 헤드라인
    4. 시장 데이터 (가격 위치, 기술적 지표)
    """

    # 캐시 TTL
    CACHE_TTL_SECONDS = 3600  # 1시간

    # 감성 임계값
    SENTIMENT_POSITIVE_THRESHOLD = 0.2
    SENTIMENT_NEGATIVE_THRESHOLD = -0.2

    def __init__(self):
        pass

    def get_insights(
        self,
        target_date: Optional[date] = None,
        limit: int = 10,
        min_mentions: int = 2,
        include_market_data: bool = True
    ) -> Dict:
        """
        종목 인사이트 목록 반환 (팩트 중심)

        Args:
            target_date: 대상 날짜 (기본: 오늘)
            limit: 최대 종목 수
            min_mentions: 최소 멘션 수 필터
            include_market_data: 시장 데이터 포함 여부

        Returns:
            {
                "date": "2026-02-06",
                "insights": [
                    {
                        "symbol": "NVDA",
                        "company_name": "NVIDIA Corp",
                        "keyword_mentions": [
                            {
                                "keyword": "AI 반도체 수요",
                                "sentiment": "positive",
                                "news_headline": "NVIDIA's AI chip revenue...",
                                "news_source": "Marketaux",
                                "published_at": "2026-02-06T10:30:00Z"
                            }
                        ],
                        "sentiment_distribution": {
                            "positive": 3,
                            "negative": 1,
                            "neutral": 1,
                            "total": 5
                        },
                        "market_data": {...},  # 선택적
                        "total_news_count": 5
                    }
                ],
                "total_keywords": 10,
                "computation_time_ms": 50
            }
        """
        import time
        start_time = time.time()

        if target_date is None:
            target_date = timezone.now().date()

        # 캐시 확인
        cache_key = f"news:insights:{target_date}:{limit}:{include_market_data}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return cached

        # 당일 키워드 조회
        keyword_obj = DailyNewsKeyword.objects.filter(
            date=target_date,
            status='completed'
        ).first()

        keywords = keyword_obj.keywords if keyword_obj else []

        # 종목별 데이터 수집
        symbol_data = self._collect_symbol_data(target_date, keywords, min_mentions)

        # 뉴스 언급 횟수 기준 정렬
        sorted_symbols = sorted(
            symbol_data.items(),
            key=lambda x: x[1]['total_news_count'],
            reverse=True
        )

        # 상위 N개 선택 및 인사이트 구성
        insights = []
        for symbol, data in sorted_symbols[:limit]:
            insight = {
                'symbol': symbol,
                'company_name': data.get('company_name'),
                'keyword_mentions': data.get('keyword_mentions', []),
                'sentiment_distribution': data.get('sentiment_distribution', {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'total': 0
                }),
                'total_news_count': data.get('total_news_count', 0),
            }

            # 시장 데이터 추가 (선택적)
            if include_market_data:
                market_data = self._get_market_data(symbol)
                if market_data:
                    insight['market_data'] = market_data

            insights.append(insight)

        computation_time_ms = int((time.time() - start_time) * 1000)

        result = {
            'date': str(target_date),
            'insights': insights,
            'total_keywords': len(keywords),
            'computation_time_ms': computation_time_ms,
        }

        # 캐시 저장
        cache.set(cache_key, result, self.CACHE_TTL_SECONDS)

        return result

    def _collect_symbol_data(
        self,
        target_date: date,
        keywords: List[Dict],
        min_mentions: int
    ) -> Dict[str, Dict]:
        """종목별 데이터 수집"""
        symbol_data = defaultdict(lambda: {
            'company_name': None,
            'keyword_mentions': [],
            'sentiment_distribution': {
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'total': 0
            },
            'total_news_count': 0,
            'news_articles': [],
        })

        # 1. 키워드에서 종목-키워드 매핑 수집
        keyword_symbol_map = self._build_keyword_symbol_map(keywords)

        # 2. 해당 날짜 뉴스 멘션 조회
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        # NewsEntity 조회 (뉴스 정보 포함)
        news_entities = NewsEntity.objects.filter(
            news__published_at__gte=start_datetime,
            news__published_at__lte=end_datetime
        ).select_related('news').order_by('-news__published_at')

        # 종목별 뉴스 그룹화
        for entity in news_entities:
            symbol = entity.symbol.upper()
            news = entity.news

            # 회사명 설정
            if not symbol_data[symbol]['company_name']:
                symbol_data[symbol]['company_name'] = entity.entity_name

            # 감성 분류
            sentiment = self._classify_sentiment(entity.sentiment_score)
            symbol_data[symbol]['sentiment_distribution'][sentiment] += 1
            symbol_data[symbol]['sentiment_distribution']['total'] += 1
            symbol_data[symbol]['total_news_count'] += 1

            # 뉴스 기사 정보 저장
            symbol_data[symbol]['news_articles'].append({
                'headline': news.title,
                'source': news.source,
                'published_at': news.published_at.isoformat(),
                'sentiment': sentiment,
                'sentiment_score': float(entity.sentiment_score) if entity.sentiment_score else None,
            })

        # 3. 키워드 멘션 정보 추가
        for symbol, data in symbol_data.items():
            # 해당 종목과 연관된 키워드 찾기
            related_keywords = keyword_symbol_map.get(symbol, [])

            for kw_info in related_keywords:
                # 해당 키워드와 관련된 뉴스 찾기
                matching_news = self._find_matching_news(
                    data['news_articles'],
                    kw_info['text']
                )

                for news_item in matching_news[:2]:  # 키워드당 최대 2개 뉴스
                    symbol_data[symbol]['keyword_mentions'].append({
                        'keyword': kw_info['text'],
                        'sentiment': kw_info['sentiment'],
                        'news_headline': news_item['headline'],
                        'news_source': news_item['source'],
                        'published_at': news_item['published_at'],
                    })

        # 4. 최소 멘션 필터 적용 및 news_articles 필드 제거
        filtered_data = {}
        for symbol, data in symbol_data.items():
            if data['total_news_count'] >= min_mentions:
                # 내부용 news_articles 필드 제거
                del data['news_articles']
                filtered_data[symbol] = data

        return filtered_data

    def _build_keyword_symbol_map(self, keywords: List[Dict]) -> Dict[str, List[Dict]]:
        """키워드-종목 매핑 구축"""
        symbol_keywords = defaultdict(list)

        for keyword in keywords:
            keyword_text = keyword.get('text', '')
            sentiment = keyword.get('sentiment', 'neutral')
            related_symbols = keyword.get('related_symbols', [])
            importance = keyword.get('importance', 0.5)

            for symbol in related_symbols:
                symbol = symbol.upper()
                symbol_keywords[symbol].append({
                    'text': keyword_text,
                    'sentiment': sentiment,
                    'importance': importance,
                })

        return dict(symbol_keywords)

    def _classify_sentiment(self, sentiment_score: Optional[Decimal]) -> str:
        """감성 점수를 카테고리로 분류"""
        if sentiment_score is None:
            return 'neutral'

        score = float(sentiment_score)
        if score >= self.SENTIMENT_POSITIVE_THRESHOLD:
            return 'positive'
        elif score <= self.SENTIMENT_NEGATIVE_THRESHOLD:
            return 'negative'
        else:
            return 'neutral'

    def _find_matching_news(
        self,
        news_articles: List[Dict],
        keyword_text: str
    ) -> List[Dict]:
        """키워드와 매칭되는 뉴스 찾기"""
        # 키워드 텍스트를 단어로 분리
        keyword_words = set(keyword_text.lower().split())

        matching = []
        for article in news_articles:
            headline_lower = article['headline'].lower()
            # 키워드 단어 중 하나라도 포함되면 매칭
            if any(word in headline_lower for word in keyword_words):
                matching.append(article)

        # 매칭되는 뉴스가 없으면 최신 뉴스 반환
        if not matching and news_articles:
            matching = news_articles[:1]

        return matching

    def _get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        종목 시장 데이터 조회

        Stock 모델에서 가격 위치, 이동평균, 밸류에이션 정보를 조회합니다.
        """
        try:
            from stocks.models import Stock

            stock = Stock.objects.filter(symbol=symbol.upper()).first()
            if not stock:
                return None

            current_price = float(stock.real_time_price or stock.previous_close or 0)

            # 가격 위치 계산
            price_position = {}

            if current_price > 0:
                price_position['current_price'] = current_price

                # 52주 고가/저가 대비
                if stock.week_52_high:
                    high = float(stock.week_52_high)
                    price_position['week_52_high'] = high
                    price_position['distance_from_52w_high'] = round(
                        ((current_price - high) / high) * 100, 2
                    )

                if stock.week_52_low:
                    low = float(stock.week_52_low)
                    price_position['week_52_low'] = low
                    price_position['distance_from_52w_low'] = round(
                        ((current_price - low) / low) * 100, 2
                    )

                # 이동평균 대비
                if stock.day_50_moving_average:
                    ma50 = float(stock.day_50_moving_average)
                    price_position['ma_50'] = ma50
                    price_position['vs_ma_50'] = round(
                        ((current_price - ma50) / ma50) * 100, 2
                    )

                if stock.day_200_moving_average:
                    ma200 = float(stock.day_200_moving_average)
                    price_position['ma_200'] = ma200
                    price_position['vs_ma_200'] = round(
                        ((current_price - ma200) / ma200) * 100, 2
                    )

            # 밸류에이션
            valuation = {}
            if stock.pe_ratio:
                valuation['pe_ratio'] = float(stock.pe_ratio)
            if stock.return_on_equity_ttm:
                valuation['roe'] = float(stock.return_on_equity_ttm)
            if stock.beta:
                valuation['beta'] = float(stock.beta)
            if stock.analyst_target_price and current_price > 0:
                target = float(stock.analyst_target_price)
                valuation['analyst_target'] = target
                valuation['analyst_upside'] = round(
                    ((target - current_price) / current_price) * 100, 2
                )

            # 애널리스트 레이팅
            analyst_ratings = None
            if stock.analyst_rating_buy or stock.analyst_rating_hold or stock.analyst_rating_sell:
                analyst_ratings = {
                    'buy': stock.analyst_rating_buy or 0,
                    'hold': stock.analyst_rating_hold or 0,
                    'sell': stock.analyst_rating_sell or 0,
                }

            return {
                'price_position': price_position if price_position else None,
                'valuation': valuation if valuation else None,
                'analyst_ratings': analyst_ratings,
            }

        except Exception as e:
            logger.warning(f"Failed to get market data for {symbol}: {e}")
            return None

    def get_insight_for_symbol(
        self,
        symbol: str,
        target_date: Optional[date] = None,
        include_market_data: bool = True
    ) -> Optional[Dict]:
        """
        단일 종목 인사이트 조회

        Args:
            symbol: 종목 심볼
            target_date: 대상 날짜
            include_market_data: 시장 데이터 포함 여부

        Returns:
            단일 종목 인사이트 또는 None
        """
        if target_date is None:
            target_date = timezone.now().date()

        # 캐시 확인
        cache_key = f"news:insight:{symbol}:{target_date}:{include_market_data}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # 해당 종목 뉴스 조회
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        news_entities = NewsEntity.objects.filter(
            symbol=symbol.upper(),
            news__published_at__gte=start_datetime,
            news__published_at__lte=end_datetime
        ).select_related('news').order_by('-news__published_at')

        if not news_entities.exists():
            return None

        # 감성 분포 계산
        sentiment_dist = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
        news_articles = []
        company_name = None

        for entity in news_entities:
            if not company_name:
                company_name = entity.entity_name

            sentiment = self._classify_sentiment(entity.sentiment_score)
            sentiment_dist[sentiment] += 1
            sentiment_dist['total'] += 1

            news_articles.append({
                'headline': entity.news.title,
                'source': entity.news.source,
                'published_at': entity.news.published_at.isoformat(),
                'sentiment': sentiment,
            })

        # 키워드 멘션 조회
        keyword_mentions = []
        keyword_obj = DailyNewsKeyword.objects.filter(
            date=target_date,
            status='completed'
        ).first()

        if keyword_obj and keyword_obj.keywords:
            for kw in keyword_obj.keywords:
                if symbol.upper() in [s.upper() for s in kw.get('related_symbols', [])]:
                    # 매칭 뉴스 찾기
                    matching = self._find_matching_news(news_articles, kw.get('text', ''))
                    if matching:
                        keyword_mentions.append({
                            'keyword': kw.get('text'),
                            'sentiment': kw.get('sentiment', 'neutral'),
                            'news_headline': matching[0]['headline'],
                            'news_source': matching[0]['source'],
                            'published_at': matching[0]['published_at'],
                        })

        result = {
            'symbol': symbol.upper(),
            'company_name': company_name,
            'keyword_mentions': keyword_mentions,
            'sentiment_distribution': sentiment_dist,
            'total_news_count': sentiment_dist['total'],
        }

        if include_market_data:
            market_data = self._get_market_data(symbol)
            if market_data:
                result['market_data'] = market_data

        # 캐시 저장 (30분)
        cache.set(cache_key, result, 1800)

        return result
