"""
뉴스 통합 서비스

Finnhub + Marketaux Provider를 통합하여 뉴스 수집 및 저장
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from django.db import transaction
from django.conf import settings

from ..models import NewsArticle, NewsEntity, EntityHighlight
from ..providers import FinnhubNewsProvider, MarketauxNewsProvider, RawNewsArticle
from .deduplicator import NewsDeduplicator

logger = logging.getLogger(__name__)


class NewsAggregatorService:
    """뉴스 통합 서비스"""

    def __init__(self):
        """Provider 초기화"""
        # Finnhub Provider
        self.finnhub = FinnhubNewsProvider(
            api_key=settings.FINNHUB_API_KEY,
            request_delay=1.0  # 60 calls/min
        )

        # Marketaux Provider
        self.marketaux = MarketauxNewsProvider(
            api_key=settings.MARKETAUX_API_KEY,
            request_delay=900.0  # 100 calls/day (15분 간격)
        )

        # Deduplicator
        self.deduplicator = NewsDeduplicator(title_similarity_threshold=0.85)

    def fetch_and_save_company_news(
        self,
        symbol: str,
        days: int = 7,
        use_marketaux: bool = True
    ) -> Dict[str, Any]:
        """
        종목별 뉴스 수집 및 저장

        Args:
            symbol: 주식 심볼
            days: 수집 기간 (일)
            use_marketaux: Marketaux 사용 여부 (rate limit 고려)

        Returns:
            Dict[str, Any]: 결과 통계
        """
        symbol = symbol.upper()
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        logger.info(f"Fetching news for {symbol} from {from_date} to {to_date}")

        # Provider별 뉴스 수집
        all_articles = []

        # Finnhub (항상 사용)
        try:
            finnhub_articles = self.finnhub.fetch_company_news(symbol, from_date, to_date)
            all_articles.extend(finnhub_articles)
            logger.info(f"Finnhub: {len(finnhub_articles)} articles")
        except Exception as e:
            logger.error(f"Finnhub fetch failed: {e}")

        # Marketaux (선택적)
        if use_marketaux:
            try:
                marketaux_articles = self.marketaux.fetch_company_news(symbol, from_date, to_date)
                all_articles.extend(marketaux_articles)
                logger.info(f"Marketaux: {len(marketaux_articles)} articles")
            except Exception as e:
                logger.error(f"Marketaux fetch failed: {e}")

        # 중복 제거
        unique_articles = self.deduplicator.deduplicate(all_articles)

        # 데이터베이스 저장
        saved_count, updated_count, skipped_count = self._save_articles(unique_articles)

        result = {
            'symbol': symbol,
            'total_fetched': len(all_articles),
            'unique_articles': len(unique_articles),
            'saved': saved_count,
            'updated': updated_count,
            'skipped': skipped_count
        }

        logger.info(f"News aggregation result: {result}")
        return result

    def fetch_and_save_market_news(
        self,
        category: str = 'general',
        use_marketaux: bool = False
    ) -> Dict[str, Any]:
        """
        일반 시장 뉴스 수집 및 저장

        Args:
            category: 뉴스 카테고리 (general, forex, crypto, merger)
            use_marketaux: Marketaux 사용 여부 (rate limit 고려)

        Returns:
            Dict[str, Any]: 결과 통계
        """
        logger.info(f"Fetching market news for category '{category}'")

        all_articles = []

        # Finnhub (항상 사용)
        try:
            finnhub_articles = self.finnhub.fetch_market_news(category, limit=50)
            all_articles.extend(finnhub_articles)
            logger.info(f"Finnhub: {len(finnhub_articles)} articles")
        except Exception as e:
            logger.error(f"Finnhub fetch failed: {e}")

        # Marketaux (선택적)
        if use_marketaux:
            try:
                marketaux_articles = self.marketaux.fetch_market_news(category, limit=3)
                all_articles.extend(marketaux_articles)
                logger.info(f"Marketaux: {len(marketaux_articles)} articles")
            except Exception as e:
                logger.error(f"Marketaux fetch failed: {e}")

        # 중복 제거
        unique_articles = self.deduplicator.deduplicate(all_articles)

        # 데이터베이스 저장
        saved_count, updated_count, skipped_count = self._save_articles(unique_articles)

        result = {
            'category': category,
            'total_fetched': len(all_articles),
            'unique_articles': len(unique_articles),
            'saved': saved_count,
            'updated': updated_count,
            'skipped': skipped_count
        }

        logger.info(f"Market news aggregation result: {result}")
        return result

    @transaction.atomic
    def _save_articles(self, articles: List[RawNewsArticle]) -> tuple:
        """
        뉴스 리스트를 데이터베이스에 저장

        Args:
            articles: 뉴스 리스트

        Returns:
            tuple: (saved_count, updated_count, skipped_count)
        """
        saved_count = 0
        updated_count = 0
        skipped_count = 0

        for raw_article in articles:
            try:
                # NewsArticle 저장/업데이트
                article, created = self._save_article(raw_article)

                if created:
                    saved_count += 1
                    # 새 뉴스인 경우에만 Entity 저장 (기존 뉴스에는 entity 추가하지 않음)
                    self._save_entities(article, raw_article.entities)
                elif article:
                    updated_count += 1
                else:
                    skipped_count += 1
                    continue

            except Exception as e:
                logger.error(f"Failed to save article: {e}, url: {raw_article.url}")
                skipped_count += 1
                continue

        return saved_count, updated_count, skipped_count

    def _save_article(self, raw_article: RawNewsArticle) -> tuple:
        """
        NewsArticle 저장/업데이트

        Args:
            raw_article: 원본 뉴스 데이터

        Returns:
            tuple: (article, created)
        """
        # URL로 중복 체크
        try:
            article = NewsArticle.objects.get(url=raw_article.url)
            created = False

            # 기존 데이터 업데이트 (감성 점수 등)
            updated = False
            if raw_article.sentiment_score and not article.sentiment_score:
                article.sentiment_score = raw_article.sentiment_score
                article.sentiment_source = raw_article.sentiment_source
                updated = True

            if raw_article.provider_id:
                if raw_article.provider_name == 'finnhub' and not article.finnhub_id:
                    article.finnhub_id = int(raw_article.provider_id)
                    updated = True
                elif raw_article.provider_name == 'marketaux' and not article.marketaux_uuid:
                    article.marketaux_uuid = raw_article.provider_id
                    updated = True

            if updated:
                article.save()

            return article, created

        except NewsArticle.DoesNotExist:
            # 새 뉴스 생성
            article = NewsArticle.objects.create(
                url=raw_article.url,
                title=raw_article.title,
                summary=raw_article.summary,
                image_url=raw_article.image_url or '',
                source=raw_article.source,
                published_at=raw_article.published_at,
                language=raw_article.language,
                category=raw_article.category,
                finnhub_id=int(raw_article.provider_id) if raw_article.provider_name == 'finnhub' and raw_article.provider_id else None,
                marketaux_uuid=raw_article.provider_id if raw_article.provider_name == 'marketaux' else '',
                sentiment_score=raw_article.sentiment_score,
                sentiment_source=raw_article.sentiment_source,
                is_press_release=raw_article.is_press_release
            )
            return article, True

    def _save_entities(
        self,
        article: NewsArticle,
        entities_data: List[Dict[str, Any]]
    ):
        """
        NewsEntity 저장 (M:N 관계)

        Args:
            article: NewsArticle 인스턴스
            entities_data: 엔티티 데이터 리스트
        """
        for entity_data in entities_data:
            try:
                # NewsEntity 생성/업데이트
                # None 값을 빈 문자열로 변환 (DB NOT NULL 제약조건)
                entity, created = NewsEntity.objects.update_or_create(
                    news=article,
                    symbol=entity_data.get('symbol', '').upper(),
                    defaults={
                        'entity_name': entity_data.get('entity_name') or '',
                        'entity_type': entity_data.get('entity_type') or 'equity',
                        'exchange': entity_data.get('exchange') or '',
                        'country': entity_data.get('country') or '',
                        'industry': entity_data.get('industry') or '',
                        'match_score': entity_data.get('match_score') or Decimal('1.00000'),
                        'sentiment_score': entity_data.get('sentiment_score'),
                        'source': entity_data.get('source') or 'finnhub'
                    }
                )

                # EntityHighlight 저장 (Marketaux 전용)
                if 'highlights' in entity_data:
                    for highlight_data in entity_data['highlights']:
                        EntityHighlight.objects.update_or_create(
                            news_entity=entity,
                            highlight_text=highlight_data.get('text', ''),
                            defaults={
                                'sentiment': highlight_data.get('sentiment', Decimal('0.000')),
                                'location': highlight_data.get('location', 'main_text')
                            }
                        )

            except Exception as e:
                logger.error(f"Failed to save entity: {e}, entity_data: {entity_data}")
                continue
