"""
뉴스 기반 주식 추천 서비스 (Phase 3)

일일 뉴스 키워드와 종목 멘션을 기반으로 투자 추천 종목을 선별합니다.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.core.cache import cache
from django.db.models import Avg, Count, F
from django.utils import timezone

from ..models import DailyNewsKeyword, NewsArticle, NewsEntity

logger = logging.getLogger(__name__)


class NewsBasedStockRecommender:
    """
    뉴스 기반 주식 추천 서비스

    알고리즘:
    1. 당일 키워드의 related_symbols 수집
    2. 뉴스 멘션 빈도 계산
    3. 감정 점수 기반 가중치 계산
    4. 섹터별 분산 (선택적)
    5. 점수 기반 상위 N개 추천
    """

    # 가중치 설정
    WEIGHT_MENTION_COUNT = 0.3  # 멘션 빈도
    WEIGHT_SENTIMENT = 0.4  # 감정 점수
    WEIGHT_KEYWORD_IMPORTANCE = 0.3  # 키워드 중요도

    # 캐시 TTL
    CACHE_TTL_SECONDS = 3600  # 1시간

    def __init__(self):
        pass

    def get_recommendations(
        self,
        target_date: Optional[date] = None,
        limit: int = 10,
        min_mentions: int = 2,
        sector_diversity: bool = True
    ) -> Dict:
        """
        주식 추천 목록 반환

        Args:
            target_date: 대상 날짜 (기본: 오늘)
            limit: 최대 추천 수
            min_mentions: 최소 멘션 수 필터
            sector_diversity: 섹터 다양성 적용 여부

        Returns:
            {
                "date": "2026-02-06",
                "recommendations": [
                    {
                        "symbol": "NVDA",
                        "company_name": "NVIDIA Corp",
                        "score": 0.95,
                        "reasons": ["AI 반도체 수요", "실적 호조"],
                        "avg_sentiment": 0.45,
                        "mention_count": 15
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
        cache_key = f"news:recommendations:{target_date}:{limit}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return cached

        # 당일 키워드 조회
        keyword_obj = DailyNewsKeyword.objects.filter(
            date=target_date,
            status='completed'
        ).first()

        if not keyword_obj or not keyword_obj.keywords:
            # 키워드가 없으면 멘션 기반으로 추천
            return self._fallback_recommendations(target_date, limit)

        # 키워드에서 종목 점수 계산
        symbol_scores = self._calculate_scores_from_keywords(
            keyword_obj.keywords,
            target_date
        )

        # 뉴스 멘션 데이터 추가
        symbol_scores = self._enhance_with_mentions(
            symbol_scores,
            target_date,
            min_mentions
        )

        # 점수 순 정렬
        sorted_symbols = sorted(
            symbol_scores.items(),
            key=lambda x: x[1]['total_score'],
            reverse=True
        )

        # 섹터 다양성 적용 (선택적)
        if sector_diversity:
            sorted_symbols = self._apply_sector_diversity(sorted_symbols, limit * 2)

        # 상위 N개 선택
        recommendations = []
        for symbol, data in sorted_symbols[:limit]:
            recommendations.append({
                'symbol': symbol,
                'company_name': data.get('company_name'),
                'score': round(data['total_score'], 3),
                'reasons': data.get('reasons', []),
                'avg_sentiment': round(data.get('avg_sentiment', 0), 3),
                'mention_count': data.get('mention_count', 0),
                'price_change': data.get('price_change'),
            })

        computation_time_ms = int((time.time() - start_time) * 1000)

        result = {
            'date': str(target_date),
            'recommendations': recommendations,
            'total_keywords': len(keyword_obj.keywords),
            'computation_time_ms': computation_time_ms,
        }

        # 캐시 저장
        cache.set(cache_key, result, self.CACHE_TTL_SECONDS)

        return result

    def _calculate_scores_from_keywords(
        self,
        keywords: List[Dict],
        target_date: date
    ) -> Dict[str, Dict]:
        """키워드에서 종목 점수 계산"""
        symbol_scores = defaultdict(lambda: {
            'total_score': 0,
            'keyword_score': 0,
            'reasons': [],
            'company_name': None,
            'avg_sentiment': 0,
            'mention_count': 0,
        })

        for keyword in keywords:
            keyword_text = keyword.get('text', '')
            sentiment = keyword.get('sentiment', 'neutral')
            importance = keyword.get('importance', 0.5)
            related_symbols = keyword.get('related_symbols', [])

            # 감정 점수 변환
            sentiment_score = {
                'positive': 1.0,
                'neutral': 0.0,
                'negative': -0.5,  # 부정 뉴스는 낮은 점수
            }.get(sentiment, 0)

            for symbol in related_symbols:
                symbol = symbol.upper()

                # 키워드 기반 점수
                kw_score = importance * self.WEIGHT_KEYWORD_IMPORTANCE
                sent_score = (sentiment_score + 1) / 2 * self.WEIGHT_SENTIMENT

                symbol_scores[symbol]['keyword_score'] += kw_score + sent_score
                symbol_scores[symbol]['reasons'].append(keyword_text)

        return dict(symbol_scores)

    def _enhance_with_mentions(
        self,
        symbol_scores: Dict[str, Dict],
        target_date: date,
        min_mentions: int
    ) -> Dict[str, Dict]:
        """뉴스 멘션 데이터로 점수 보강"""
        # 해당 날짜 뉴스 멘션 집계
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        mention_stats = NewsEntity.objects.filter(
            news__published_at__gte=start_datetime,
            news__published_at__lte=end_datetime
        ).values('symbol', 'entity_name').annotate(
            mention_count=Count('id'),
            avg_sentiment=Avg('sentiment_score')
        )

        # 최대 멘션 수 (정규화용)
        max_mentions = max(
            (m['mention_count'] for m in mention_stats),
            default=1
        )

        # 멘션 데이터가 있는 종목 처리
        mentioned_symbols = set()
        for stat in mention_stats:
            symbol = stat['symbol'].upper()
            mentioned_symbols.add(symbol)
            mention_count = stat['mention_count']
            avg_sentiment = stat['avg_sentiment'] or 0

            # 최소 멘션 필터
            if mention_count < min_mentions:
                continue

            if symbol not in symbol_scores:
                symbol_scores[symbol] = {
                    'total_score': 0,
                    'keyword_score': 0,
                    'reasons': [],
                    'company_name': stat['entity_name'],
                    'avg_sentiment': 0,
                    'mention_count': 0,
                }

            # 멘션 점수 계산 (정규화)
            mention_score = (mention_count / max_mentions) * self.WEIGHT_MENTION_COUNT

            symbol_scores[symbol]['mention_count'] = mention_count
            symbol_scores[symbol]['avg_sentiment'] = float(avg_sentiment)
            symbol_scores[symbol]['company_name'] = stat['entity_name']

            # 총점 계산
            sentiment_boost = (float(avg_sentiment) + 1) / 2 * 0.2  # 감정 보너스
            symbol_scores[symbol]['total_score'] = (
                symbol_scores[symbol]['keyword_score'] +
                mention_score +
                sentiment_boost
            )

        # 키워드에만 있는 종목도 total_score 계산 (멘션 데이터 없어도 추천)
        for symbol, data in symbol_scores.items():
            if symbol not in mentioned_symbols and data['keyword_score'] > 0:
                # 키워드 점수 기반으로 total_score 계산
                # 기본 감정 점수 (중립 가정)
                neutral_sentiment_boost = 0.5 * 0.2
                data['total_score'] = data['keyword_score'] + neutral_sentiment_boost
                data['mention_count'] = 1  # 키워드에서 언급됨

        return symbol_scores

    def _apply_sector_diversity(
        self,
        sorted_symbols: List,
        max_items: int
    ) -> List:
        """섹터 다양성 적용 (같은 섹터 종목 제한)"""
        # TODO: 섹터 정보가 필요한 경우 FMP API 연동
        # 현재는 단순히 반환
        return sorted_symbols[:max_items]

    def _fallback_recommendations(
        self,
        target_date: date,
        limit: int
    ) -> Dict:
        """키워드가 없을 때 멘션 기반 추천"""
        import time
        start_time = time.time()

        # 해당 날짜 뉴스 멘션 상위 종목
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        mention_stats = NewsEntity.objects.filter(
            news__published_at__gte=start_datetime,
            news__published_at__lte=end_datetime
        ).values('symbol', 'entity_name').annotate(
            mention_count=Count('id'),
            avg_sentiment=Avg('sentiment_score')
        ).order_by('-mention_count')[:limit]

        recommendations = []
        for stat in mention_stats:
            avg_sentiment = float(stat['avg_sentiment']) if stat['avg_sentiment'] else 0
            score = (stat['mention_count'] / 10) * 0.5 + (avg_sentiment + 1) / 2 * 0.5

            recommendations.append({
                'symbol': stat['symbol'],
                'company_name': stat['entity_name'],
                'score': round(min(score, 1.0), 3),
                'reasons': ['뉴스 멘션 상위'],
                'avg_sentiment': round(avg_sentiment, 3),
                'mention_count': stat['mention_count'],
                'price_change': None,
            })

        computation_time_ms = int((time.time() - start_time) * 1000)

        return {
            'date': str(target_date),
            'recommendations': recommendations,
            'total_keywords': 0,
            'computation_time_ms': computation_time_ms,
            'fallback': True,
        }
