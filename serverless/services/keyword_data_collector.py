"""
Market Movers 키워드 생성용 추가 데이터 수집 서비스

외부 API로부터 Overview, News, Indicators를 수집하여
LLM 키워드 생성을 위한 풍부한 컨텍스트를 제공합니다.

병렬 처리 및 Redis 캐싱 전략:
- ThreadPoolExecutor (max_workers=5)
- Alpha Vantage Rate Limit: 5 calls/분 (12초 간격)
- Redis 캐싱: msgpack 압축, TTL 1시간
- 타임아웃: 10초/호출, 5분/전체

KB 참고: Alpha Vantage Rate Limiting, ThreadPoolExecutor 병렬 처리
"""

import logging
import time
import msgpack
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.core.cache import cache
from django.conf import settings

from api_request.alphavantage_client import AlphaVantageClient
from api_request.rate_limiter import get_rate_limiter, RateLimitExceeded

# News Providers (선택적)
try:
    from news.providers.marketaux import MarketauxNewsProvider
except ImportError:
    MarketauxNewsProvider = None

try:
    from news.providers.finnhub import FinnhubNewsProvider
except ImportError:
    FinnhubNewsProvider = None


logger = logging.getLogger(__name__)


class KeywordDataCollector:
    """
    키워드 생성용 추가 데이터 수집기

    수집 데이터:
    1. Overview (Alpha Vantage): 기업 개요, market_cap, PE ratio, 52주 high/low
    2. News (MarketAux/Finnhub): 최근 3개 뉴스 + 감성 분석 (선택)
    3. Indicators: 기존 5개 지표 (MarketMover 모델에서 이미 수집됨)

    병렬 처리:
    - ThreadPoolExecutor (max_workers=5)
    - Alpha Vantage Rate Limit: 5 calls/분 (12초 간격)
    - 종목당 평균 수집 시간: 12초 (Rate Limiting)
    - 20개 종목 전체: ~4분 (12초 × 20 = 240초)

    Redis 캐싱:
    - Cache Key: keyword_context:{date}:{symbol}
    - TTL: 1시간 (3600초)
    - Compression: msgpack
    """

    # Redis 캐시 키 템플릿
    CACHE_KEY_TEMPLATE = "keyword_context:{date}:{symbol}"
    CACHE_TTL = 3600  # 1시간

    # 병렬 처리 설정
    MAX_WORKERS = 5  # Alpha Vantage Rate Limit에 맞춤
    API_TIMEOUT = 10  # 10초
    PIPELINE_TIMEOUT = 300  # 5분

    def __init__(self):
        """API 클라이언트 초기화"""
        # Alpha Vantage (Overview)
        self.av_client = None
        if hasattr(settings, 'ALPHA_VANTAGE_API_KEY'):
            try:
                self.av_client = AlphaVantageClient(
                    api_key=settings.ALPHA_VANTAGE_API_KEY
                )
            except Exception as e:
                logger.warning(f"Alpha Vantage client 초기화 실패: {e}")

        # Rate Limiter
        self.rate_limiter = get_rate_limiter("alpha_vantage")

        # News Providers (선택적)
        self.news_providers = []

        # MarketAux (우선순위 1: 감성 분석 포함)
        if MarketauxNewsProvider and hasattr(settings, 'MARKETAUX_API_KEY'):
            try:
                self.news_providers.append(
                    MarketauxNewsProvider(api_key=settings.MARKETAUX_API_KEY)
                )
                logger.info("MarketAux provider 초기화 완료")
            except Exception as e:
                logger.warning(f"MarketAux provider 초기화 실패: {e}")

        # Finnhub (우선순위 2: rate limit 여유)
        if FinnhubNewsProvider and hasattr(settings, 'FINNHUB_API_KEY'):
            try:
                self.news_providers.append(
                    FinnhubNewsProvider(api_key=settings.FINNHUB_API_KEY)
                )
                logger.info("Finnhub provider 초기화 완료")
            except Exception as e:
                logger.warning(f"Finnhub provider 초기화 실패: {e}")

        if not self.news_providers:
            logger.info("뉴스 provider가 초기화되지 않았습니다. 뉴스 수집이 스킵됩니다.")

    def collect_batch(
        self,
        symbols: List[str],
        target_date: date
    ) -> Dict[str, Any]:
        """
        배치 데이터 수집 (병렬)

        Args:
            symbols: 종목 심볼 리스트 (최대 20개)
            target_date: 대상 날짜

        Returns:
            {
                'successful': ['AAPL', 'MSFT', ...],
                'failed': [('GOOGL', 'HTTPError 429'), ...],
                'total_stocks': 20,
                'cache_hits': 5,
                'api_calls': 15,
                'duration_ms': 240000,
                'contexts': {
                    'AAPL': {...},
                    'MSFT': {...}
                }
            }
        """
        start_time = time.time()

        logger.info("keyword_data_collection_batch", extra={
            "status": "started",
            "total_stocks": len(symbols),
            "date": str(target_date),
        })

        successful = []
        failed = []
        cache_hits = 0
        api_calls = 0
        contexts = {}

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            # 모든 종목을 병렬로 처리
            future_to_symbol = {
                executor.submit(
                    self._collect_single,
                    symbol,
                    target_date
                ): symbol
                for symbol in symbols
            }

            # 결과 수집
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]

                try:
                    result = future.result(timeout=self.API_TIMEOUT)

                    if result['success']:
                        successful.append(symbol)
                        contexts[symbol] = result['context']

                        if result['from_cache']:
                            cache_hits += 1
                        else:
                            api_calls += 1

                        logger.info("keyword_data_collection", extra={
                            "phase": "overview",
                            "symbol": symbol,
                            "status": "success",
                            "duration_ms": result['duration_ms'],
                            "cache_hit": result['from_cache'],
                        })
                    else:
                        failed.append((symbol, result['error']))

                        logger.error("keyword_data_collection", extra={
                            "phase": "overview",
                            "symbol": symbol,
                            "status": "failed",
                            "error": result['error'],
                        })

                except Exception as exc:
                    failed.append((symbol, str(exc)))

                    logger.error("keyword_data_collection", extra={
                        "phase": "overview",
                        "symbol": symbol,
                        "status": "failed",
                        "error": str(exc),
                    })

        duration_ms = int((time.time() - start_time) * 1000)

        result = {
            'successful': successful,
            'failed': failed,
            'total_stocks': len(symbols),
            'cache_hits': cache_hits,
            'api_calls': api_calls,
            'duration_ms': duration_ms,
            'contexts': contexts,
        }

        logger.info("keyword_data_collection_batch", extra={
            "status": "completed",
            "successful": len(successful),
            "failed": len(failed),
            "cache_hits": cache_hits,
            "api_calls": api_calls,
            "duration_ms": duration_ms,
        })

        return result

    def _collect_single(
        self,
        symbol: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        단일 종목 데이터 수집

        Args:
            symbol: 종목 심볼
            target_date: 대상 날짜

        Returns:
            {
                'success': True,
                'from_cache': False,
                'duration_ms': 1234,
                'error': None,
                'context': {...}
            }
        """
        start_time = time.time()

        try:
            # 1. 캐시 조회
            cached_data = self.get_cached_context(str(target_date), symbol)
            if cached_data:
                return {
                    'success': True,
                    'from_cache': True,
                    'duration_ms': int((time.time() - start_time) * 1000),
                    'error': None,
                    'context': cached_data,
                }

            # 2. 데이터 수집
            context = self._empty_context()

            # Overview 수집 (Rate Limiting 적용)
            overview = self._fetch_overview(symbol)
            if overview:
                context['overview'] = overview

            # News 수집 (선택적)
            news = self._fetch_news(symbol)
            if news:
                context['news'] = news

            # Indicators는 빈 dict (MarketMover 모델에서 가져옴)
            context['indicators'] = {}

            # 3. Redis 캐싱
            self.set_cached_context(str(target_date), symbol, context)

            return {
                'success': True,
                'from_cache': False,
                'duration_ms': int((time.time() - start_time) * 1000),
                'error': None,
                'context': context,
            }

        except RateLimitExceeded as exc:
            # Rate Limit 초과 - 재시도 필요
            return {
                'success': False,
                'from_cache': False,
                'duration_ms': int((time.time() - start_time) * 1000),
                'error': f"RateLimitExceeded: {exc.limit_type}",
                'context': None,
            }

        except Exception as exc:
            # 기타 에러
            return {
                'success': False,
                'from_cache': False,
                'duration_ms': int((time.time() - start_time) * 1000),
                'error': str(exc),
                'context': None,
            }

    def _fetch_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Alpha Vantage로부터 기업 개요 수집 (Rate Limiting 적용)

        Args:
            symbol: 주식 심볼

        Returns:
            {
                'description': '...',
                'market_cap': '2.5T',
                'pe_ratio': 28.5,
                '52_week_high': 199.62,
                '52_week_low': 164.08
            } or None
        """
        if not self.av_client:
            return None

        try:
            # Rate Limiting 적용
            self.rate_limiter.acquire()

            data = self.av_client.get_company_overview(symbol)

            # Alpha Vantage 빈 응답 체크
            if not data or 'Symbol' not in data:
                logger.debug(f"    ⚠️ {symbol} overview 없음")
                return None

            # 필요한 필드만 추출
            overview = {}

            # Description
            if data.get('Description'):
                # 너무 긴 설명은 앞부분만 (500자)
                desc = data['Description'][:500]
                if len(data['Description']) > 500:
                    desc += '...'
                overview['description'] = desc

            # Market Cap (숫자 → 읽기 쉬운 형식)
            market_cap = data.get('MarketCapitalization')
            if market_cap and market_cap != 'None':
                try:
                    cap_num = float(market_cap)
                    if cap_num >= 1e12:
                        overview['market_cap'] = f"{cap_num / 1e12:.2f}T"
                    elif cap_num >= 1e9:
                        overview['market_cap'] = f"{cap_num / 1e9:.2f}B"
                    elif cap_num >= 1e6:
                        overview['market_cap'] = f"{cap_num / 1e6:.2f}M"
                except (ValueError, TypeError):
                    pass

            # PE Ratio
            pe_ratio = data.get('PERatio')
            if pe_ratio and pe_ratio != 'None':
                try:
                    overview['pe_ratio'] = float(pe_ratio)
                except (ValueError, TypeError):
                    pass

            # 52 Week High/Low
            week_52_high = data.get('52WeekHigh')
            if week_52_high and week_52_high != 'None':
                try:
                    overview['52_week_high'] = float(week_52_high)
                except (ValueError, TypeError):
                    pass

            week_52_low = data.get('52WeekLow')
            if week_52_low and week_52_low != 'None':
                try:
                    overview['52_week_low'] = float(week_52_low)
                except (ValueError, TypeError):
                    pass

            # Dividend Yield (추가)
            div_yield = data.get('DividendYield')
            if div_yield and div_yield != 'None':
                try:
                    overview['dividend_yield'] = float(div_yield) * 100  # 백분율
                except (ValueError, TypeError):
                    pass

            if overview:
                logger.debug(f"    ✓ {symbol} overview 수집 완료")
                return overview

            return None

        except Exception as e:
            logger.error(f"    ❌ {symbol} overview 수집 실패: {e}")
            return None

    def _fetch_news(self, symbol: str, limit: int = 3) -> Optional[List[Dict[str, Any]]]:
        """
        뉴스 provider로부터 최근 뉴스 수집 (Marketaux → Finnhub 폴백)

        Args:
            symbol: 주식 심볼
            limit: 최대 뉴스 개수 (기본값: 3)

        Returns:
            [
                {
                    'title': '...',
                    'source': 'Bloomberg',
                    'sentiment': 'positive',  # or 'neutral', 'negative'
                    'published_at': '2026-01-24T10:00:00'
                },
                ...
            ] or None

        폴백 전략:
        1. Marketaux 시도 (감성분석 포함)
        2. Marketaux 실패/Rate Limit 시 → Finnhub 시도
        3. 둘 다 실패 시 → None 반환 (Overview만으로 키워드 생성)
        """
        if not self.news_providers:
            logger.info(f"    ⚠️ {symbol} 뉴스 provider 없음 - 스킵")
            return None

        # 최근 7일 뉴스
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)

        news_articles = []
        used_provider = None
        errors = []

        # 여러 provider 시도 (MarketAux → Finnhub 순서)
        for provider in self.news_providers:
            provider_name = provider.__class__.__name__

            try:
                # Rate Limit 체크 (Marketaux는 15분 간격 필요)
                if hasattr(provider, 'last_request_time') and hasattr(provider, 'request_delay'):
                    time_since_last = time.time() - provider.last_request_time
                    wait_time = provider.request_delay - time_since_last

                    # 5초 이상 대기 필요하면 스킵하고 다음 provider 시도
                    if wait_time > 5:
                        logger.info(f"    ⏭️ {symbol} {provider_name} Rate Limit ({wait_time:.0f}초 대기 필요) - 다음 provider로")
                        errors.append((provider_name, f"Rate Limit: {wait_time:.0f}초 대기 필요"))
                        continue

                # 뉴스 수집 시도
                raw_articles = provider.fetch_company_news(
                    symbol=symbol,
                    from_date=from_date,
                    to_date=to_date
                )

                # RawNewsArticle → dict 변환
                for raw in raw_articles[:limit]:
                    article = {
                        'title': raw.title,
                        'source': raw.source,
                        'published_at': raw.published_at.isoformat(),
                        'provider': provider_name.lower().replace('newsprovider', ''),
                    }

                    # 감성 분석 (MarketAux만 제공)
                    if raw.sentiment_score is not None:
                        sentiment_value = float(raw.sentiment_score)
                        if sentiment_value > 0.2:
                            article['sentiment'] = 'positive'
                        elif sentiment_value < -0.2:
                            article['sentiment'] = 'negative'
                        else:
                            article['sentiment'] = 'neutral'
                    else:
                        article['sentiment'] = 'neutral'

                    news_articles.append(article)

                # 성공 시 provider 기록
                if news_articles:
                    used_provider = provider_name
                    logger.info(f"    ✓ {symbol} 뉴스 {len(news_articles)}개 수집 ({provider_name})")
                    break

            except Exception as e:
                error_msg = str(e)
                errors.append((provider_name, error_msg))
                logger.warning(f"    ⚠️ {symbol} {provider_name} 실패: {error_msg}")
                continue

        # 결과 반환
        if news_articles:
            return news_articles[:limit]

        # 모든 provider 실패
        if errors:
            error_summary = ", ".join([f"{name}: {msg}" for name, msg in errors])
            logger.warning(f"    ❌ {symbol} 모든 뉴스 provider 실패: {error_summary}")
        else:
            logger.debug(f"    ⚠️ {symbol} 뉴스 없음")

        return None

    def _empty_context(self) -> Dict[str, Any]:
        """빈 컨텍스트 반환 (fallback)"""
        return {
            'overview': {},
            'news': [],
            'indicators': {}
        }

    def get_cached_context(
        self,
        date_str: str,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Redis에서 컨텍스트 조회 (압축 해제)

        Args:
            date_str: 날짜 문자열 (YYYY-MM-DD)
            symbol: 종목 심볼

        Returns:
            dict or None
        """
        cache_key = self.CACHE_KEY_TEMPLATE.format(
            date=date_str,
            symbol=symbol.upper()
        )

        try:
            compressed = cache.get(cache_key)
            if compressed:
                logger.debug(f"Cache HIT: {cache_key}")
                return msgpack.unpackb(compressed, raw=False)
        except Exception as exc:
            logger.warning(f"Cache get error: {exc}")

        return None

    def set_cached_context(
        self,
        date_str: str,
        symbol: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Redis에 컨텍스트 저장 (압축)

        Args:
            date_str: 날짜 문자열 (YYYY-MM-DD)
            symbol: 종목 심볼
            data: 컨텍스트 데이터

        Returns:
            bool: 성공 여부
        """
        cache_key = self.CACHE_KEY_TEMPLATE.format(
            date=date_str,
            symbol=symbol.upper()
        )

        try:
            compressed = msgpack.packb(data, use_bin_type=True)
            cache.set(cache_key, compressed, timeout=self.CACHE_TTL)

            logger.debug(f"Cache SET: {cache_key} ({len(compressed)} bytes)")
            return True

        except Exception as exc:
            logger.warning(f"Cache set error: {exc}")
            return False

    def delete_cached_context(
        self,
        date_str: str,
        symbol: str
    ) -> bool:
        """
        Redis에서 컨텍스트 삭제

        Args:
            date_str: 날짜 문자열 (YYYY-MM-DD)
            symbol: 종목 심볼

        Returns:
            bool: 성공 여부
        """
        cache_key = self.CACHE_KEY_TEMPLATE.format(
            date=date_str,
            symbol=symbol.upper()
        )

        try:
            cache.delete(cache_key)
            logger.debug(f"Cache DELETE: {cache_key}")
            return True

        except Exception as exc:
            logger.warning(f"Cache delete error: {exc}")
            return False

    def get_batch_contexts(
        self,
        date_str: str,
        symbols: List[str]
    ) -> List[Dict[str, Any]]:
        """
        배치 컨텍스트 조회 (LLM 입력용)

        Args:
            date_str: 날짜 문자열 (YYYY-MM-DD)
            symbols: 종목 심볼 리스트

        Returns:
            list: 컨텍스트 리스트 (성공한 종목만)
        """
        contexts = []

        for symbol in symbols:
            context = self.get_cached_context(date_str, symbol)
            if context:
                contexts.append(context)
            else:
                logger.warning(f"No cached context for {symbol} on {date_str}")

        return contexts

    def estimate_tokens(
        self,
        contexts: List[Dict[str, Any]],
        include_prompt: bool = True
    ) -> Dict[str, int]:
        """
        토큰 수 추정

        Args:
            contexts: 컨텍스트 리스트
            include_prompt: 프롬프트 토큰 포함 여부

        Returns:
            {
                'context_tokens': 6000,
                'prompt_tokens': 1200,
                'total_input_tokens': 7200,
                'estimated_output_tokens': 6000
            }
        """
        import json

        # 컨텍스트 JSON 문자열
        context_str = json.dumps(contexts, ensure_ascii=False)

        # 토큰 추정 (1 char ≈ 0.4 tokens)
        context_tokens = int(len(context_str) * 0.4)

        prompt_tokens = 0
        if include_prompt:
            # 시스템 프롬프트: ~1000 토큰
            # 사용자 프롬프트 헤더: ~200 토큰
            prompt_tokens = 1200

        total_input = context_tokens + prompt_tokens

        # 출력 추정: 종목당 300 토큰
        estimated_output = len(contexts) * 300

        return {
            'context_tokens': context_tokens,
            'prompt_tokens': prompt_tokens,
            'total_input_tokens': total_input,
            'estimated_output_tokens': estimated_output,
        }


# 편의 함수
def collect_keyword_data_sync(
    symbols: List[str],
    target_date: date
) -> Dict[str, Any]:
    """
    동기 방식 데이터 수집

    Args:
        symbols: 종목 심볼 리스트
        target_date: 대상 날짜

    Returns:
        dict: 수집 결과
    """
    collector = KeywordDataCollector()
    return collector.collect_batch(symbols, target_date)


def get_keyword_contexts_batch(
    date_str: str,
    symbols: List[str]
) -> List[Dict[str, Any]]:
    """
    배치 컨텍스트 조회

    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)
        symbols: 종목 심볼 리스트

    Returns:
        list: 컨텍스트 리스트
    """
    collector = KeywordDataCollector()
    return collector.get_batch_contexts(date_str, symbols)


def estimate_batch_tokens(
    contexts: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    배치 토큰 수 추정

    Args:
        contexts: 컨텍스트 리스트

    Returns:
        dict: 토큰 추정 결과
    """
    collector = KeywordDataCollector()
    return collector.estimate_tokens(contexts)


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 테스트
    from datetime import date

    collector = KeywordDataCollector()

    # 5개 종목 테스트
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    test_date = date.today()

    print(f"\n{'='*60}")
    print(f"Market Movers 키워드 데이터 수집 테스트")
    print(f"종목: {', '.join(test_symbols)}")
    print(f"날짜: {test_date}")
    print(f"{'='*60}\n")

    result = collector.collect_batch(test_symbols, test_date)

    print(f"\n[결과]")
    print(f"  성공: {len(result['successful'])} / {result['total_stocks']}")
    print(f"  실패: {len(result['failed'])}")
    print(f"  캐시 히트: {result['cache_hits']}")
    print(f"  API 호출: {result['api_calls']}")
    print(f"  소요 시간: {result['duration_ms'] / 1000:.2f}초")

    if result['successful']:
        print(f"\n[성공 종목 샘플: {result['successful'][0]}]")
        sample = result['contexts'][result['successful'][0]]
        print(f"  Overview: {bool(sample['overview'])}")
        print(f"  News: {len(sample['news'])} articles")

        if sample['overview']:
            print(f"    - Market Cap: {sample['overview'].get('market_cap', 'N/A')}")
            print(f"    - PE Ratio: {sample['overview'].get('pe_ratio', 'N/A')}")

        if sample['news']:
            print(f"    - Latest: {sample['news'][0]['title'][:60]}...")
            print(f"    - Sentiment: {sample['news'][0]['sentiment']}")
