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
        min_mentions: int = 1,
        include_market_data: bool = True,
        sector: Optional[str] = None,
    ) -> Dict:
        """
        종목 인사이트 목록 반환 (팩트 중심)

        Args:
            target_date: 대상 날짜 (기본: 오늘)
            limit: 최대 종목 수
            min_mentions: 최소 멘션 수 필터
            include_market_data: 시장 데이터 포함 여부
            sector: 섹터 필터 (None이면 전체, 대소문자 무관)

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

        # 섹터 정규화 (.title() — "TECHNOLOGY" → "Technology")
        normalized_sector = sector.strip().title() if sector else None

        # 캐시 확인
        cache_key = f"news:insights:{target_date}:{limit}:{include_market_data}:{normalized_sector or 'all'}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return cached

        # 당일 키워드 조회 (없으면 최근 완료 키워드 fallback)
        keyword_obj = DailyNewsKeyword.objects.filter(
            date=target_date,
            status='completed'
        ).first()

        if not keyword_obj:
            keyword_obj = DailyNewsKeyword.objects.filter(
                date__lt=target_date,
                status='completed',
            ).order_by('-date').first()

        keywords = keyword_obj.keywords if keyword_obj else []

        # 종목별 데이터 수집
        symbol_data = self._collect_symbol_data(target_date, keywords, min_mentions)

        # 섹터 정보 일괄 조회 (N+1 방지)
        from stocks.models import Stock
        all_symbols = list(symbol_data.keys())
        sector_map: Dict[str, Optional[str]] = {}
        if all_symbols:
            stock_rows = Stock.objects.filter(
                symbol__in=all_symbols
            ).values('symbol', 'sector')
            for row in stock_rows:
                raw_sector = row['sector']
                sector_map[row['symbol']] = raw_sector.strip().title() if raw_sector else None

        # available_sectors 계산 (sector 필터 없을 때만)
        available_sectors = None
        if not normalized_sector:
            sector_counts: Dict[str, int] = {}
            for symbol in all_symbols:
                sym_sector = sector_map.get(symbol)
                if sym_sector:
                    sector_counts[sym_sector] = sector_counts.get(sym_sector, 0) + 1
            available_sectors = sorted(
                [{'sector': s, 'count': c} for s, c in sector_counts.items()],
                key=lambda x: x['count'],
                reverse=True,
            )

        # 섹터 필터 적용 (sector 파라미터가 있을 때만)
        if normalized_sector:
            symbol_data = {
                sym: data
                for sym, data in symbol_data.items()
                if (sector_map.get(sym) or '') == normalized_sector
            }

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
                'sector': sector_map.get(symbol),
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

        # 9. 영문 키워드 → 한국어 변환 (Gemini 배치)
        self._translate_keywords_to_korean(insights)

        computation_time_ms = int((time.time() - start_time) * 1000)

        result = {
            'date': str(target_date),
            'period_days': 7,
            'period_start': str(target_date - timedelta(days=6)),
            'period_end': str(target_date),
            'sector_filter': normalized_sector,
            'insights': insights,
            'total_keywords': len(keywords),
            'computation_time_ms': computation_time_ms,
        }

        if available_sectors is not None:
            result['available_sectors'] = available_sectors

        # 캐시 저장
        cache.set(cache_key, result, self.CACHE_TTL_SECONDS)

        return result

    def _collect_symbol_data(
        self,
        target_date: date,
        keywords: List[Dict],
        min_mentions: int
    ) -> Dict[str, Dict]:
        """종목별 데이터 수집 (7일 범위 + 키워드 fallback)"""
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

        # 2. 최근 7일 뉴스 멘션 조회 (오늘만 보면 데이터 부족)
        end_datetime = datetime.combine(target_date, datetime.max.time())
        start_datetime = datetime.combine(target_date - timedelta(days=6), datetime.min.time())

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
                'article_url': news.url,
            })

        # 3. Fallback: 엔티티가 부족하면 키워드 related_symbols로 보충
        if len(symbol_data) < min_mentions + 2:
            self._supplement_from_keywords(
                symbol_data, keywords, start_datetime, end_datetime
            )

        # 4. 키워드 멘션 정보 추가
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
                        'sentiment': news_item.get('sentiment', kw_info['sentiment']),
                        'news_headline': news_item['headline'],
                        'news_source': news_item['source'],
                        'published_at': news_item['published_at'],
                        'article_url': news_item.get('article_url', ''),
                    })

        # 5. 반대 sentiment 보충 — 양쪽 관점 보장
        for symbol, data in symbol_data.items():
            if data['keyword_mentions'] and data['news_articles']:
                existing_sentiments = {m['sentiment'] for m in data['keyword_mentions']}
                existing_headlines = {m['news_headline'] for m in data['keyword_mentions']}
                dist = data['sentiment_distribution']

                # 긍정만 있는데 부정 뉴스가 존재하면 보충
                # 부정만 있는데 긍정 뉴스가 존재하면 보충
                missing = []
                if 'negative' not in existing_sentiments and dist.get('negative', 0) > 0:
                    missing.append('negative')
                if 'positive' not in existing_sentiments and dist.get('positive', 0) > 0:
                    missing.append('positive')

                for target_sentiment in missing:
                    for article in data['news_articles']:
                        if (article['sentiment'] == target_sentiment
                                and article['headline'] not in existing_headlines):
                            # 헤드라인에서 요약 키워드 생성 (20자 + …)
                            headline = article['headline']
                            short_kw = headline[:20].rstrip() + '…' if len(headline) > 20 else headline
                            data['keyword_mentions'].append({
                                'keyword': short_kw,
                                'sentiment': target_sentiment,
                                'news_headline': headline,
                                'news_source': article['source'],
                                'published_at': article['published_at'],
                                'article_url': article.get('article_url', ''),
                            })
                            existing_headlines.add(headline)
                            break  # 반대 sentiment당 1개만 보충

        # 6. 키워드 매핑이 없는 종목: 최신 뉴스 헤드라인으로 보충
        for symbol, data in symbol_data.items():
            if not data['keyword_mentions'] and data['news_articles']:
                seen_headlines = set()
                for article in data['news_articles'][:3]:
                    if article['headline'] in seen_headlines:
                        continue
                    seen_headlines.add(article['headline'])
                    headline = article['headline']
                    short_kw = headline[:20].rstrip() + '…' if len(headline) > 20 else headline
                    data['keyword_mentions'].append({
                        'keyword': short_kw,
                        'sentiment': article['sentiment'],
                        'news_headline': headline,
                        'news_source': article['source'],
                        'published_at': article['published_at'],
                        'article_url': article.get('article_url', ''),
                    })

        # 7. sentiment 인터리브 정렬 — 첫 3개에 양쪽 관점 포함
        for symbol, data in symbol_data.items():
            mentions = data['keyword_mentions']
            if len(mentions) > 1:
                by_sentiment = {'positive': [], 'negative': [], 'neutral': []}
                for m in mentions:
                    by_sentiment.get(m['sentiment'], by_sentiment['neutral']).append(m)

                # 라운드로빈: positive → negative → neutral 순으로 인터리브
                reordered = []
                buckets = [by_sentiment['positive'], by_sentiment['negative'], by_sentiment['neutral']]
                max_len = max(len(b) for b in buckets)
                for i in range(max_len):
                    for bucket in buckets:
                        if i < len(bucket):
                            reordered.append(bucket[i])
                data['keyword_mentions'] = reordered

        # 8. 최소 멘션 필터 적용 및 news_articles 필드 제거
        filtered_data = {}
        for symbol, data in symbol_data.items():
            if data['total_news_count'] >= min_mentions:
                # 내부용 news_articles 필드 제거
                del data['news_articles']
                filtered_data[symbol] = data

        return filtered_data

    def _supplement_from_keywords(
        self,
        symbol_data: Dict,
        keywords: List[Dict],
        start_datetime: datetime,
        end_datetime: datetime,
    ):
        """
        NewsEntity가 부족할 때 키워드 related_symbols로 보충.
        키워드에서 종목을 추출하고 NewsArticle에서 직접 검색.
        """
        # 키워드에서 종목 추출
        keyword_symbols = set()
        symbol_keyword_info = defaultdict(list)
        for kw in keywords:
            for sym in kw.get('related_symbols', []):
                sym_upper = sym.upper()
                keyword_symbols.add(sym_upper)
                symbol_keyword_info[sym_upper].append({
                    'text': kw.get('text', ''),
                    'sentiment': kw.get('sentiment', 'neutral'),
                })

        # 이미 symbol_data에 있는 종목 제외
        new_symbols = keyword_symbols - set(symbol_data.keys())
        if not new_symbols:
            return

        # 해당 종목명이 제목에 포함된 뉴스 검색
        for symbol in list(new_symbols)[:20]:  # 최대 20개
            articles = NewsArticle.objects.filter(
                published_at__gte=start_datetime,
                published_at__lte=end_datetime,
            ).filter(
                Q(title__icontains=symbol) |
                Q(rule_tickers__contains=[symbol])
            ).order_by('-published_at')[:5]

            if not articles:
                continue

            # 회사명 조회
            company_name = None
            try:
                from stocks.models import Stock
                stock = Stock.objects.filter(symbol=symbol).first()
                if stock:
                    company_name = stock.stock_name or symbol
            except Exception:
                pass

            for article in articles:
                sentiment = self._classify_sentiment(article.sentiment_score)
                symbol_data[symbol]['sentiment_distribution'][sentiment] += 1
                symbol_data[symbol]['sentiment_distribution']['total'] += 1
                symbol_data[symbol]['total_news_count'] += 1
                symbol_data[symbol]['news_articles'].append({
                    'headline': article.title,
                    'source': article.source,
                    'published_at': article.published_at.isoformat(),
                    'sentiment': sentiment,
                    'sentiment_score': float(article.sentiment_score) if article.sentiment_score else None,
                })

            if company_name:
                symbol_data[symbol]['company_name'] = company_name

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

    def _translate_keywords_to_korean(self, insights: List[Dict]):
        """영문 키워드를 Gemini로 한국어 변환 (배치, in-place 수정)"""
        import re

        # 한국어가 아닌 키워드 수집
        headlines_to_translate = []
        mention_refs = []  # (insight_idx, mention_idx)
        for i, insight in enumerate(insights):
            for j, mention in enumerate(insight.get('keyword_mentions', [])):
                kw = mention['keyword']
                if not re.search(r'[가-힣]', kw):
                    headlines_to_translate.append(mention['news_headline'])
                    mention_refs.append((i, j))

        if not headlines_to_translate:
            return

        # 중복 제거하며 순서 유지
        unique_headlines = list(dict.fromkeys(headlines_to_translate))[:20]

        try:
            from django.conf import settings as django_settings
            from google import genai
            from google.genai import types
            import json

            api_key = getattr(django_settings, 'GOOGLE_AI_API_KEY', None) or getattr(django_settings, 'GEMINI_API_KEY', None)
            if not api_key:
                return

            client = genai.Client(api_key=api_key)

            numbered = "\n".join(f"{idx + 1}. {h}" for idx, h in enumerate(unique_headlines))

            prompt = f"""다음 영문 뉴스 헤드라인을 각각 20자 이내의 한국어 키워드로 요약하세요.
투자자 관점에서 핵심 내용만 간결하게 "주어 + 동사" 구조로 작성하세요.
예: "Tesla Q1 deliveries beat" → "테슬라 1분기 인도량 상회"

{numbered}

정확히 {len(unique_headlines)}개의 한국어 키워드를 JSON 배열로만 응답하세요."""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=500,
                    temperature=0.2,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )

            json_match = re.search(r'\[[\s\S]*\]', response.text)
            if not json_match:
                return

            summaries = json.loads(json_match.group())
            translation_map = {
                h: str(s)[:20] for h, s in zip(unique_headlines, summaries)
                if isinstance(s, str)
            }

            # 인사이트에 적용
            for i, j in mention_refs:
                headline = insights[i]['keyword_mentions'][j]['news_headline']
                korean_kw = translation_map.get(headline)
                if korean_kw:
                    insights[i]['keyword_mentions'][j]['keyword'] = korean_kw

        except Exception as e:
            logger.warning(f"Korean keyword translation failed: {e}")

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
                'article_url': entity.news.url,
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
                            'article_url': matching[0].get('article_url', ''),
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
