"""
Quote Enricher Service

FMP Quote API를 사용하여 종목 데이터에 실시간 시세 정보를 추가합니다.
- 변동률 (changesPercentage)
- 당일 고가/저가 (dayHigh, dayLow)
- 전일 종가 (previousClose)
- 시가 (open)

향후 AWS Lambda로 전환 시 재사용 가능하도록 설계되었습니다.
"""
import httpx
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings
from django.core.cache import cache
from typing import Optional

logger = logging.getLogger(__name__)


class QuoteEnricher:
    """
    FMP Quote API를 사용한 시세 정보 보강 서비스

    스크리너 결과에 실시간 변동률, 고가/저가 등의 정보를 추가합니다.
    """

    BASE_URL = "https://financialmodelingprep.com/stable"
    CACHE_TTL = 60  # 1분 (실시간 시세는 짧은 캐시)
    BATCH_SIZE = 50  # FMP API 최대 배치 크기

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: FMP API 키 (미지정 시 settings에서 가져옴)
        """
        self.api_key = api_key or getattr(settings, 'FMP_API_KEY', None)
        if not self.api_key:
            logger.warning("FMP_API_KEY가 설정되지 않았습니다.")

    def _fetch_single_quote(self, symbol: str) -> tuple[str, Optional[dict]]:
        """
        단일 종목 시세 조회 (내부 헬퍼)

        Returns:
            (symbol, quote_data) 튜플
        """
        # 캐시 확인
        cache_key = f"fmp:quote:{symbol}"
        cached = cache.get(cache_key)
        if cached:
            return (symbol, cached)

        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/quote",
                    params={"symbol": symbol, "apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            if isinstance(data, list) and len(data) > 0:
                quote = data[0]
                cache.set(cache_key, quote, self.CACHE_TTL)
                return (symbol, quote)

        except Exception as e:
            logger.debug(f"Quote 조회 실패 ({symbol}): {e}")

        return (symbol, None)

    def get_batch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """
        여러 종목의 시세 정보를 병렬로 일괄 조회

        FMP stable/quote API는 배치를 지원하지 않으므로 개별 요청을 수행합니다.
        ThreadPoolExecutor를 사용해 병렬 처리로 속도를 개선합니다.

        Args:
            symbols: 종목 심볼 리스트 (최대 100개)

        Returns:
            {symbol: quote_data} 형태의 딕셔너리
        """
        if not symbols or not self.api_key:
            return {}

        # 최대 100개로 제한
        symbols = symbols[:100]
        quotes = {}

        # 캐시된 것과 조회 필요한 것 분리
        symbols_to_fetch = []
        for symbol in symbols:
            cache_key = f"fmp:quote:{symbol}"
            cached = cache.get(cache_key)
            if cached:
                quotes[symbol] = cached
            else:
                symbols_to_fetch.append(symbol)

        # 캐시 미스된 심볼들을 병렬로 조회
        if symbols_to_fetch:
            # 동시 요청 수 제한 (FMP Rate limit 고려)
            max_workers = min(10, len(symbols_to_fetch))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._fetch_single_quote, symbol): symbol
                    for symbol in symbols_to_fetch
                }

                for future in as_completed(futures):
                    try:
                        symbol, quote = future.result()
                        if quote:
                            quotes[symbol] = quote
                    except Exception as e:
                        logger.debug(f"Quote 조회 에러: {e}")

        if quotes:
            logger.info(f"FMP Quote API 조회 완료: {len(quotes)}개 종목 (캐시: {len(symbols) - len(symbols_to_fetch)}, API: {len(symbols_to_fetch)})")

        return quotes

    def enrich_stocks(self, stocks: list[dict]) -> list[dict]:
        """
        종목 리스트에 시세 정보를 추가

        Args:
            stocks: 종목 데이터 리스트 (symbol 필드 필수)

        Returns:
            시세 정보가 추가된 종목 리스트

        추가되는 필드:
            - change: 전일 대비 변동 금액
            - changesPercentage: 전일 대비 변동률 (%)
            - dayHigh: 당일 고가
            - dayLow: 당일 저가
            - previousClose: 전일 종가
            - open: 시가
        """
        if not stocks:
            return stocks

        # 심볼 추출
        symbols = [s.get("symbol") for s in stocks if s.get("symbol")]

        if not symbols:
            return stocks

        # 시세 정보 일괄 조회
        quotes = self.get_batch_quotes(symbols)

        if not quotes:
            return stocks

        # 종목 데이터에 시세 정보 병합
        for stock in stocks:
            symbol = stock.get("symbol")
            if symbol and symbol in quotes:
                quote = quotes[symbol]
                stock["change"] = quote.get("change")
                stock["changesPercentage"] = quote.get("changePercentage")
                stock["dayHigh"] = quote.get("dayHigh")
                stock["dayLow"] = quote.get("dayLow")
                stock["previousClose"] = quote.get("previousClose")
                stock["open"] = quote.get("open")

        return stocks

    def get_single_quote(self, symbol: str) -> Optional[dict]:
        """
        단일 종목의 시세 정보 조회

        Args:
            symbol: 종목 심볼

        Returns:
            시세 정보 딕셔너리 또는 None
        """
        quotes = self.get_batch_quotes([symbol])
        return quotes.get(symbol)

    def calculate_change_percentage(
        self,
        current_price: float,
        previous_price: float
    ) -> Optional[float]:
        """
        변동률 계산 (순수 함수)

        Args:
            current_price: 현재 가격
            previous_price: 이전 가격

        Returns:
            변동률 (%) 또는 None (계산 불가 시)

        Example:
            >>> enricher = QuoteEnricher()
            >>> enricher.calculate_change_percentage(105, 100)
            5.0
            >>> enricher.calculate_change_percentage(95, 100)
            -5.0
        """
        if previous_price is None or previous_price == 0:
            return None
        if current_price is None:
            return None

        return ((current_price - previous_price) / previous_price) * 100
