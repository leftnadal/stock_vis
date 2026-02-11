"""
Symbol Matcher Service (Phase 5)

회사명 → 티커 심볼 매칭 서비스.
FMP Search API + PostgreSQL Stock DB + Redis 캐시 활용.

주요 기능:
1. 회사명으로 티커 심볼 조회
2. Fuzzy matching (유사 회사명 허용)
3. 캐싱 (Redis 24시간 TTL)
4. 배치 처리 (비용 절감)

Usage:
    from serverless.services.symbol_matcher import SymbolMatcher

    matcher = SymbolMatcher()

    # 단일 매칭
    symbol = matcher.match("Apple Inc.")  # "AAPL"
    symbol = matcher.match("Taiwan Semiconductor")  # "TSM"

    # 배치 매칭
    results = matcher.match_batch(["Apple", "Microsoft", "NVIDIA"])
    # {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA"}
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from django.core.cache import cache
from django.db.models import Q

from stocks.models import Stock

logger = logging.getLogger(__name__)


class SymbolMatcher:
    """
    회사명 → 티커 심볼 매칭 서비스

    매칭 우선순위:
    1. 하드코딩 매핑 (자주 사용되는 변형)
    2. PostgreSQL Stock DB 정확 매칭
    3. PostgreSQL Stock DB 부분 매칭
    4. FMP Search API (캐시됨)
    """

    CACHE_PREFIX = 'symbol_match:'
    CACHE_TTL = 86400  # 24시간

    # 자주 사용되는 회사명 → 티커 하드코딩 매핑
    HARDCODED_MAPPINGS = {
        # Tech Giants
        'apple': 'AAPL',
        'apple inc': 'AAPL',
        'apple inc.': 'AAPL',
        'microsoft': 'MSFT',
        'microsoft corp': 'MSFT',
        'microsoft corporation': 'MSFT',
        'google': 'GOOGL',
        'alphabet': 'GOOGL',
        'alphabet inc': 'GOOGL',
        'amazon': 'AMZN',
        'amazon.com': 'AMZN',
        'amazon inc': 'AMZN',
        'meta': 'META',
        'meta platforms': 'META',
        'facebook': 'META',
        'nvidia': 'NVDA',
        'nvidia corp': 'NVDA',
        'nvidia corporation': 'NVDA',
        'tesla': 'TSLA',
        'tesla inc': 'TSLA',
        'tesla motors': 'TSLA',

        # Semiconductors
        'amd': 'AMD',
        'advanced micro devices': 'AMD',
        'intel': 'INTC',
        'intel corp': 'INTC',
        'intel corporation': 'INTC',
        'tsmc': 'TSM',
        'taiwan semiconductor': 'TSM',
        'taiwan semiconductor manufacturing': 'TSM',
        'broadcom': 'AVGO',
        'broadcom inc': 'AVGO',
        'qualcomm': 'QCOM',
        'qualcomm inc': 'QCOM',
        'micron': 'MU',
        'micron technology': 'MU',
        'arm': 'ARM',
        'arm holdings': 'ARM',

        # Software & Cloud
        'salesforce': 'CRM',
        'salesforce.com': 'CRM',
        'adobe': 'ADBE',
        'adobe inc': 'ADBE',
        'oracle': 'ORCL',
        'oracle corp': 'ORCL',
        'ibm': 'IBM',
        'cisco': 'CSCO',
        'cisco systems': 'CSCO',
        'servicenow': 'NOW',
        'snowflake': 'SNOW',
        'palantir': 'PLTR',
        'palantir technologies': 'PLTR',

        # Finance
        'jpmorgan': 'JPM',
        'jp morgan': 'JPM',
        'jpmorgan chase': 'JPM',
        'goldman sachs': 'GS',
        'goldman': 'GS',
        'bank of america': 'BAC',
        'bofa': 'BAC',
        'morgan stanley': 'MS',
        'wells fargo': 'WFC',
        'citigroup': 'C',
        'citi': 'C',
        'blackrock': 'BLK',
        'berkshire hathaway': 'BRK.B',
        'berkshire': 'BRK.B',

        # Healthcare & Pharma
        'johnson & johnson': 'JNJ',
        'j&j': 'JNJ',
        'pfizer': 'PFE',
        'moderna': 'MRNA',
        'eli lilly': 'LLY',
        'lilly': 'LLY',
        'merck': 'MRK',
        'abbvie': 'ABBV',
        'unitedhealth': 'UNH',
        'unitedhealth group': 'UNH',

        # Consumer & Retail
        'walmart': 'WMT',
        'costco': 'COST',
        'target': 'TGT',
        'home depot': 'HD',
        'nike': 'NKE',
        'starbucks': 'SBUX',
        'coca-cola': 'KO',
        'coca cola': 'KO',
        'coke': 'KO',
        'pepsi': 'PEP',
        'pepsico': 'PEP',
        'mcdonalds': 'MCD',
        "mcdonald's": 'MCD',

        # Gaming & Entertainment
        'activision': 'ATVI',
        'activision blizzard': 'ATVI',
        'electronic arts': 'EA',
        'ea': 'EA',
        'netflix': 'NFLX',
        'disney': 'DIS',
        'walt disney': 'DIS',
        'warner bros': 'WBD',
        'warner bros discovery': 'WBD',
        'spotify': 'SPOT',

        # Automotive
        'ford': 'F',
        'ford motor': 'F',
        'general motors': 'GM',
        'gm': 'GM',
        'toyota': 'TM',
        'honda': 'HMC',
        'rivian': 'RIVN',
        'lucid': 'LCID',
        'lucid motors': 'LCID',

        # Energy & Utilities
        'exxon': 'XOM',
        'exxonmobil': 'XOM',
        'chevron': 'CVX',
        'conocophillips': 'COP',
        'bp': 'BP',
        'shell': 'SHEL',

        # Telecom
        'verizon': 'VZ',
        'at&t': 'T',
        'att': 'T',
        't-mobile': 'TMUS',
        'tmobile': 'TMUS',

        # Other notable
        'boeing': 'BA',
        'lockheed martin': 'LMT',
        'raytheon': 'RTX',
        'caterpillar': 'CAT',
        '3m': 'MMM',
        'ups': 'UPS',
        'fedex': 'FDX',
        'visa': 'V',
        'mastercard': 'MA',
        'paypal': 'PYPL',
        'square': 'SQ',
        'block': 'SQ',
        'coinbase': 'COIN',
        'robinhood': 'HOOD',
    }

    # 불필요한 접미사 패턴
    SUFFIX_PATTERNS = [
        r'\s+(inc\.?|corp\.?|co\.?|ltd\.?|llc|lp|plc|sa|ag|nv)$',
        r'\s+(incorporated|corporation|company|limited)$',
        r'\s+(holdings?|group|enterprises?)$',
    ]

    def __init__(self):
        # 접미사 패턴 컴파일
        self._suffix_pattern = re.compile(
            '|'.join(self.SUFFIX_PATTERNS),
            re.IGNORECASE
        )
        logger.info("SymbolMatcher initialized")

    def match(self, company_name: str) -> Optional[str]:
        """
        회사명으로 티커 심볼 조회

        Args:
            company_name: 회사명 (예: "Apple Inc.", "Microsoft")

        Returns:
            티커 심볼 (예: "AAPL") 또는 None
        """
        if not company_name or len(company_name) < 2:
            return None

        # 정규화
        normalized = self._normalize_name(company_name)

        # 1. 캐시 확인
        cache_key = f"{self.CACHE_PREFIX}{normalized}"
        cached = cache.get(cache_key)
        if cached:
            return cached if cached != '__NOT_FOUND__' else None

        # 2. 하드코딩 매핑
        symbol = self.HARDCODED_MAPPINGS.get(normalized)
        if symbol:
            cache.set(cache_key, symbol, self.CACHE_TTL)
            return symbol

        # 3. PostgreSQL 정확 매칭
        symbol = self._match_from_db_exact(normalized, company_name)
        if symbol:
            cache.set(cache_key, symbol, self.CACHE_TTL)
            return symbol

        # 4. PostgreSQL 부분 매칭
        symbol = self._match_from_db_partial(normalized, company_name)
        if symbol:
            cache.set(cache_key, symbol, self.CACHE_TTL)
            return symbol

        # 매칭 실패
        cache.set(cache_key, '__NOT_FOUND__', self.CACHE_TTL)
        logger.debug(f"Symbol not found for: {company_name}")
        return None

    def match_batch(self, company_names: List[str]) -> Dict[str, Optional[str]]:
        """
        배치 회사명 매칭

        Args:
            company_names: 회사명 리스트

        Returns:
            {회사명: 티커} 딕셔너리
        """
        results = {}

        for name in company_names:
            results[name] = self.match(name)

        matched = sum(1 for v in results.values() if v)
        logger.info(f"Batch match: {matched}/{len(company_names)} matched")

        return results

    def get_match_confidence(
        self,
        company_name: str,
        symbol: str
    ) -> float:
        """
        매칭 신뢰도 계산

        Args:
            company_name: 입력 회사명
            symbol: 매칭된 티커

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        try:
            stock = Stock.objects.get(symbol=symbol.upper())
            db_name = stock.stock_name or ''

            # 이름 유사도 계산
            normalized_input = self._normalize_name(company_name)
            normalized_db = self._normalize_name(db_name)

            return SequenceMatcher(
                None, normalized_input, normalized_db
            ).ratio()

        except Stock.DoesNotExist:
            return 0.5  # DB에 없으면 중간 신뢰도
        except Exception:
            return 0.5  # 기타 에러시 중간 신뢰도

    def _normalize_name(self, name: str) -> str:
        """회사명 정규화"""
        # 소문자 변환
        normalized = name.lower().strip()

        # 접미사 제거
        normalized = self._suffix_pattern.sub('', normalized)

        # 특수문자 정리
        normalized = re.sub(r'[^\w\s&]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized.strip()

    def _match_from_db_exact(
        self,
        normalized: str,
        original: str
    ) -> Optional[str]:
        """PostgreSQL 정확 매칭"""
        try:
            # 심볼로 직접 매칭 (티커가 입력된 경우)
            if re.match(r'^[A-Z]{1,5}$', original.upper()):
                if Stock.objects.filter(symbol=original.upper()).exists():
                    return original.upper()

            # 이름 정확 매칭 (대소문자 무시)
            stock = Stock.objects.filter(
                Q(stock_name__iexact=original) |
                Q(stock_name__iexact=normalized)
            ).first()

            if stock:
                return stock.symbol

        except Exception as e:
            logger.error(f"DB exact match error: {e}")

        return None

    def _match_from_db_partial(
        self,
        normalized: str,
        original: str
    ) -> Optional[str]:
        """PostgreSQL 부분 매칭"""
        try:
            # 이름에 포함된 종목 검색
            stocks = Stock.objects.filter(
                Q(stock_name__icontains=original) |
                Q(stock_name__icontains=normalized)
            )[:10]

            if not stocks:
                return None

            # 가장 유사한 종목 선택
            best_match = None
            best_score = 0.0

            for stock in stocks:
                stock_name_str = self._normalize_name(stock.stock_name or '')
                score = SequenceMatcher(None, normalized, stock_name_str).ratio()

                if score > best_score and score >= 0.6:
                    best_score = score
                    best_match = stock.symbol

            return best_match

        except Exception as e:
            logger.error(f"DB partial match error: {e}")

        return None


# 싱글톤 인스턴스
_symbol_matcher = None


def get_symbol_matcher() -> SymbolMatcher:
    """싱글톤 인스턴스 반환"""
    global _symbol_matcher
    if _symbol_matcher is None:
        _symbol_matcher = SymbolMatcher()
    return _symbol_matcher
