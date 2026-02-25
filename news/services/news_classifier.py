"""
뉴스 분류 서비스 (News Intelligence Pipeline v3 - Phase 1)

3단계 규칙 엔진으로 뉴스를 분류하고 중요도를 산정합니다.
- Engine A: 종목 매칭 (SymbolMatcher + cashtag/괄호 regex)
- Engine B: 섹터 분류 (키워드→섹터 매핑)
- Engine C: 5-factor 중요도 스코어링
- 퍼센타일 선별: 당일 누적 기준 상위 15%, 미분석 필터
"""

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from ..models import NewsArticle
from .keyword_sector_map import match_sectors

logger = logging.getLogger(__name__)

# ── Engine A: Ticker 추출 Regex 패턴 ──

# $AAPL 형태의 cashtag
CASHTAG_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')

# (NASDAQ: AAPL) 또는 (NYSE: AAPL) 형태
EXCHANGE_PATTERN = re.compile(
    r'\((?:NYSE|NASDAQ|AMEX|NYSEMKT):\s*([A-Z]{1,5})\)'
)

# 동음이의어 문맥 필터 키워드 (주변에 이 단어가 있어야 주식으로 인정)
STOCK_CONTEXT_WORDS = {
    'stock', 'stocks', 'share', 'shares', 'equity', 'equities',
    'earnings', 'revenue', 'profit', 'dividend', 'market cap',
    'ipo', 'sec', 'filing', 'analyst', 'upgrade', 'downgrade',
    'buy', 'sell', 'hold', 'target price', 'wall street',
    'quarter', 'q1', 'q2', 'q3', 'q4', 'fiscal', 'guidance',
    'nasdaq', 'nyse', 's&p', 'dow',
}

# 동음이의어 목록 (주식과 일반 단어가 모두 될 수 있는 ticker)
AMBIGUOUS_TICKERS = {
    'META', 'NOW', 'ALL', 'IT', 'ON', 'ARE', 'HAS', 'CAN',
    'SO', 'MO', 'AN', 'GO', 'KEY', 'BIG', 'LOW', 'HIGH',
    'TRUE', 'FAST', 'GOOD', 'BEST', 'WELL', 'REAL',
}

# ── Engine C: 수동 가중치 (초기 β₁~β₅) ──

DEFAULT_WEIGHTS = {
    'source_credibility': 0.15,    # β₁: 소스 신뢰도
    'entity_count': 0.20,          # β₂: 종목/섹터 매칭 수
    'sentiment_magnitude': 0.20,   # β₃: 감성 강도
    'recency': 0.25,               # β₄: 시의성
    'keyword_relevance': 0.20,     # β₅: 키워드 관련성
}

# 소스 신뢰도 점수 (0~1)
SOURCE_CREDIBILITY = {
    'reuters': 1.0,
    'bloomberg': 1.0,
    'wsj': 0.95,
    'wall street journal': 0.95,
    'cnbc': 0.90,
    'financial times': 0.95,
    'ft': 0.95,
    'barrons': 0.90,
    "barron's": 0.90,
    'marketwatch': 0.85,
    'seeking alpha': 0.75,
    'motley fool': 0.70,
    'yahoo finance': 0.80,
    'benzinga': 0.75,
    'investopedia': 0.70,
    'the verge': 0.70,
    'techcrunch': 0.70,
    'associated press': 0.90,
    'ap': 0.90,
}
DEFAULT_SOURCE_SCORE = 0.5

# 퍼센타일 선별 비율
TOP_PERCENTILE = 0.15  # 상위 15%


class NewsClassifier:
    """
    뉴스 분류 + 중요도 산정 + 퍼센타일 선별 서비스

    classify_batch() → 수집 직후 체이닝
    select_for_analysis() → LLM 분석 대상 선별

    Phase 5: 배포된 ML 모델 가중치 자동 적용
    """

    def __init__(self, weights: Optional[dict] = None):
        if weights is not None:
            self.weights = weights
        else:
            # Phase 5: 배포된 ML 가중치 자동 적용
            self.weights = self._load_deployed_weights()
        self._symbol_matcher = None

    @staticmethod
    def _load_deployed_weights() -> dict:
        """배포된 ML 모델 가중치 로드, 없으면 수동 가중치 사용"""
        try:
            from .ml_production_manager import MLProductionManager
            deployed = MLProductionManager.get_deployed_weights()
            if deployed:
                logger.info(f"Using deployed ML weights: {deployed}")
                return deployed
        except Exception as e:
            logger.debug(f"ML weights not available: {e}")
        return DEFAULT_WEIGHTS

    @property
    def symbol_matcher(self):
        """SymbolMatcher lazy initialization"""
        if self._symbol_matcher is None:
            from serverless.services.symbol_matcher import get_symbol_matcher
            self._symbol_matcher = get_symbol_matcher()
        return self._symbol_matcher

    # ════════════════════════════════════════
    # Engine A: 종목 매칭
    # ════════════════════════════════════════

    def extract_tickers(self, article: NewsArticle) -> list[str]:
        """
        뉴스에서 관련 ticker 추출

        우선순위:
        1. 기존 NewsEntity (provider가 제공한 ticker)
        2. Cashtag ($AAPL)
        3. 거래소 괄호 패턴 (NASDAQ: AAPL)
        4. SymbolMatcher (본문 내 회사명)
        """
        tickers = set()

        # 1. 기존 NewsEntity에서 ticker
        entity_symbols = list(
            article.entities.values_list('symbol', flat=True)
        )
        tickers.update(s.upper() for s in entity_symbols)

        # 2-3. 제목 + 본문에서 regex 추출
        text = f"{article.title} {article.summary or ''}"
        tickers.update(self._extract_cashtags(text))
        tickers.update(self._extract_exchange_tickers(text))

        # 4. 본문 내 회사명 → SymbolMatcher
        if len(tickers) < 3:  # 이미 충분하면 skip
            matched = self._match_company_names(text)
            tickers.update(matched)

        return sorted(tickers)[:10]  # 최대 10개

    def _extract_cashtags(self, text: str) -> set[str]:
        """$AAPL 형태의 cashtag 추출"""
        matches = CASHTAG_PATTERN.findall(text)
        return {m for m in matches if len(m) >= 1}

    def _extract_exchange_tickers(self, text: str) -> set[str]:
        """(NASDAQ: AAPL) 형태의 ticker 추출"""
        matches = EXCHANGE_PATTERN.findall(text)
        return set(matches)

    def _match_company_names(self, text: str) -> set[str]:
        """본문 내 회사명을 SymbolMatcher로 매칭"""
        tickers = set()
        text_lower = text.lower()

        # 대문자로 시작하는 단어들을 후보로 추출 (간단한 NER 대체)
        # 2~3개 단어 조합까지 시도
        words = text.split()
        candidates = set()

        for i, word in enumerate(words):
            # 1-word candidate
            clean = re.sub(r'[^\w\s&\'-]', '', word).strip()
            if clean and clean[0].isupper() and len(clean) >= 3:
                candidates.add(clean)
                # 2-word candidate
                if i + 1 < len(words):
                    next_word = re.sub(r'[^\w\s&\'-]', '', words[i + 1]).strip()
                    candidates.add(f"{clean} {next_word}")

        for candidate in candidates:
            symbol = self.symbol_matcher.match(candidate)
            if symbol:
                # 동음이의어 문맥 필터
                if symbol in AMBIGUOUS_TICKERS:
                    if not self._has_stock_context(text_lower):
                        continue
                tickers.add(symbol)

        return tickers

    def _has_stock_context(self, text_lower: str) -> bool:
        """주식 관련 문맥이 있는지 확인"""
        return any(word in text_lower for word in STOCK_CONTEXT_WORDS)

    # ════════════════════════════════════════
    # Engine B: 섹터 분류
    # ════════════════════════════════════════

    def extract_sectors(self, article: NewsArticle) -> list[str]:
        """뉴스에서 관련 섹터 추출 (키워드 매핑)"""
        text = f"{article.title} {article.summary or ''}"
        return match_sectors(text)

    # ════════════════════════════════════════
    # Engine C: 5-factor 중요도 스코어링
    # ════════════════════════════════════════

    def calculate_importance(
        self,
        article: NewsArticle,
        tickers: list[str],
        sectors: list[str],
    ) -> float:
        """
        5-factor 가중 합산으로 importance_score 계산

        β₁: source_credibility (소스 신뢰도)
        β₂: entity_count (종목/섹터 매칭 수)
        β₃: sentiment_magnitude (감성 강도)
        β₄: recency (시의성)
        β₅: keyword_relevance (키워드 관련성)
        """
        w = self.weights

        # β₁: 소스 신뢰도
        source_lower = (article.source or '').lower().strip()
        f1 = SOURCE_CREDIBILITY.get(source_lower, DEFAULT_SOURCE_SCORE)

        # β₂: 종목/섹터 매칭 수 (normalize: 0~1)
        entity_raw = len(tickers) + len(sectors)
        f2 = min(entity_raw / 5.0, 1.0)  # 5개 이상이면 1.0

        # β₃: 감성 강도 (절대값, 0~1)
        if article.sentiment_score is not None:
            f3 = min(abs(float(article.sentiment_score)), 1.0)
        else:
            f3 = 0.3  # 감성 정보 없으면 기본값

        # β₄: 시의성 (최근일수록 높음)
        hours_ago = (
            timezone.now() - article.published_at
        ).total_seconds() / 3600
        if hours_ago <= 2:
            f4 = 1.0
        elif hours_ago <= 6:
            f4 = 0.85
        elif hours_ago <= 12:
            f4 = 0.7
        elif hours_ago <= 24:
            f4 = 0.5
        else:
            f4 = max(0.1, 1.0 - hours_ago / 168)  # 1주일에 걸쳐 감소

        # β₅: 키워드 관련성 (섹터 매칭 깊이)
        f5 = min(len(sectors) / 3.0, 1.0) if sectors else 0.0

        score = (
            w['source_credibility'] * f1
            + w['entity_count'] * f2
            + w['sentiment_magnitude'] * f3
            + w['recency'] * f4
            + w['keyword_relevance'] * f5
        )

        return round(min(max(score, 0.0), 1.0), 4)

    # ════════════════════════════════════════
    # 통합: 분류 배치
    # ════════════════════════════════════════

    def classify_batch(self, article_ids: Optional[list] = None, hours: int = 4) -> dict:
        """
        뉴스 배치 분류 (수집 직후 체이닝)

        Args:
            article_ids: 특정 뉴스 ID 리스트 (None이면 최근 N시간)
            hours: article_ids가 None일 때 조회 범위

        Returns:
            dict: {classified: int, skipped: int, errors: int}
        """
        if article_ids:
            articles = NewsArticle.objects.filter(
                id__in=article_ids,
                importance_score__isnull=True,
            )
        else:
            cutoff = timezone.now() - __import__('datetime').timedelta(hours=hours)
            articles = NewsArticle.objects.filter(
                published_at__gte=cutoff,
                importance_score__isnull=True,
            )

        classified = 0
        skipped = 0
        errors = 0

        for article in articles:
            try:
                tickers = self.extract_tickers(article)
                sectors = self.extract_sectors(article)
                score = self.calculate_importance(article, tickers, sectors)

                article.rule_tickers = tickers if tickers else None
                article.rule_sectors = sectors if sectors else None
                article.importance_score = score
                article.save(update_fields=[
                    'rule_tickers', 'rule_sectors', 'importance_score', 'updated_at',
                ])
                classified += 1

            except Exception as e:
                logger.error(f"Classification error for {article.id}: {e}")
                errors += 1

        result = {'classified': classified, 'skipped': skipped, 'errors': errors}
        logger.info(f"NewsClassifier batch complete: {result}")
        return result

    # ════════════════════════════════════════
    # 퍼센타일 선별 (당일 누적 기준 + 미전송 필터)
    # ════════════════════════════════════════

    def select_for_analysis(self) -> list:
        """
        당일 누적 기준 상위 15% 중 llm_analyzed=False인 뉴스 선별

        Returns:
            list: 분석 대상 NewsArticle ID 리스트
        """
        today = timezone.now().date()
        start_of_day = timezone.make_aware(
            datetime.combine(today, datetime.min.time())
        )

        # 오늘 모든 뉴스의 importance_score
        all_today = NewsArticle.objects.filter(
            published_at__gte=start_of_day,
            importance_score__isnull=False,
        ).order_by('-importance_score')

        total = all_today.count()
        if total == 0:
            return []

        # 상위 15% 임계값 계산
        top_count = max(1, int(total * TOP_PERCENTILE))
        threshold_article = list(
            all_today.values_list('importance_score', flat=True)[:top_count]
        )
        if not threshold_article:
            return []

        threshold = threshold_article[-1]  # 상위 N번째 점수

        # threshold 이상 & llm_analyzed=False
        candidates = NewsArticle.objects.filter(
            published_at__gte=start_of_day,
            importance_score__gte=threshold,
            llm_analyzed=False,
        ).values_list('id', flat=True)

        selected = list(candidates)

        # 최소 보장: 선별된 것이 없으면 최소 1건
        if not selected and total > 0:
            top_one = all_today.filter(
                llm_analyzed=False,
            ).values_list('id', flat=True).first()
            if top_one:
                selected = [top_one]

        logger.info(
            f"select_for_analysis: {len(selected)} articles selected "
            f"(total={total}, threshold={threshold:.4f})"
        )
        return selected
