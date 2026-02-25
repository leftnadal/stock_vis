"""
ML Label 수집 서비스 (News Intelligence Pipeline v3 - Phase 2)

DailyPrice 기반 +24h 변동폭 계산으로 ML Label을 수집합니다.
- Company News 우선 (source_tickers로 ticker 명시)
- 섹터별 threshold로 ml_label_important 판정
- label_confidence 계산 (동일 종목 뉴스 수 + 주말/휴일 감쇠)
- NYSE 거래 캘린더 기반 거래일 판별
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from django.db.models import Count, Q
from django.utils import timezone

from stocks.models import DailyPrice, Stock
from ..models import NewsArticle

logger = logging.getLogger(__name__)


# 2026년 NYSE 휴일 (확장 가능)
NYSE_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # MLK Jr. Day
    date(2026, 2, 16),   # Presidents' Day
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 7, 3),    # Independence Day (observed)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
}

# 2025년 NYSE 휴일
NYSE_HOLIDAYS_2025 = {
    date(2025, 1, 1),
    date(2025, 1, 20),
    date(2025, 2, 17),
    date(2025, 4, 18),
    date(2025, 5, 26),
    date(2025, 7, 4),
    date(2025, 9, 1),
    date(2025, 11, 27),
    date(2025, 12, 25),
}

ALL_NYSE_HOLIDAYS = NYSE_HOLIDAYS_2025 | NYSE_HOLIDAYS_2026

# 섹터별 중요 뉴스 판정 threshold (% 변동폭)
SECTOR_THRESHOLDS = {
    'Technology': 2.5,
    'Communication Services': 2.0,
    'Consumer Discretionary': 2.0,
    'Healthcare': 2.0,
    'Financials': 1.5,
    'Industrials': 1.5,
    'Consumer Staples': 1.0,
    'Energy': 2.5,
    'Materials': 2.0,
    'Real Estate': 1.5,
    'Utilities': 1.0,
}
DEFAULT_THRESHOLD = 2.0


def is_trading_day(d: date) -> bool:
    """NYSE 거래일 여부"""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if d in ALL_NYSE_HOLIDAYS:
        return False
    return True


def next_trading_day(d: date) -> date:
    """다음 거래일 반환"""
    candidate = d + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def is_pre_holiday(d: date) -> bool:
    """장 휴일 전날 여부 (다음 거래일이 2일 이상 떨어짐)"""
    nxt = next_trading_day(d)
    return (nxt - d).days > 1


class MLLabelCollector:
    """
    ML Label 수집 서비스

    매일 19:00 EST에 실행:
    1. 어제 수집된 뉴스 중 ml_label_24h IS NULL 조회
    2. Company News 우선 (source_tickers 명시)
    3. DailyPrice에서 변동폭 계산
    4. 섹터별 threshold → ml_label_important 판정
    5. label_confidence 계산
    """

    def collect_labels(self, lookback_days: int = 2) -> dict:
        """
        Label 수집 메인 메서드

        Args:
            lookback_days: 조회 범위 (기본 2일 - 어제+그저께 미처리분)

        Returns:
            dict: {processed: int, labeled: int, skipped: int, errors: int}
        """
        cutoff = timezone.now() - timedelta(days=lookback_days)

        # ml_label_24h IS NULL이고, 관련 ticker가 있는 뉴스
        articles = NewsArticle.objects.filter(
            published_at__gte=cutoff,
            ml_label_24h__isnull=True,
        ).filter(
            # Company News (source_tickers from NewsEntity) 또는 rule_tickers가 있는 것
            Q(entities__isnull=False) | Q(rule_tickers__isnull=False)
        ).distinct().select_related().prefetch_related('entities')

        processed = 0
        labeled = 0
        skipped = 0
        errors = 0

        for article in articles:
            try:
                result = self._process_article(article)
                processed += 1
                if result:
                    labeled += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Label collection error for {article.id}: {e}")
                errors += 1

        result = {
            'processed': processed,
            'labeled': labeled,
            'skipped': skipped,
            'errors': errors,
        }
        logger.info(f"MLLabelCollector complete: {result}")
        return result

    def _process_article(self, article: NewsArticle) -> bool:
        """
        단일 뉴스의 ML Label 수집

        Returns:
            True if label was set, False if skipped
        """
        # 1. ticker 결정
        tickers = self._get_tickers(article)
        if not tickers:
            return False

        # 2. 발행일과 다음 거래일 결정
        pub_date = article.published_at.date()
        if not is_trading_day(pub_date):
            # 비거래일 뉴스 → 다음 거래일을 기준일로
            base_date = next_trading_day(pub_date)
        else:
            base_date = pub_date

        label_date = next_trading_day(base_date)

        # 3. DailyPrice 조회 (첫 번째 유효 ticker 기준)
        change_pct = None
        used_ticker = None

        for ticker in tickers:
            change_pct = self._calculate_change(ticker, base_date, label_date)
            if change_pct is not None:
                used_ticker = ticker
                break

        if change_pct is None:
            return False

        # 4. 섹터별 threshold → ml_label_important
        sector = self._get_sector(used_ticker)
        threshold = SECTOR_THRESHOLDS.get(sector, DEFAULT_THRESHOLD)
        is_important = abs(change_pct) >= threshold

        # 5. label_confidence 계산
        confidence = self._calculate_confidence(article, pub_date)

        # 6. 저장
        article.ml_label_24h = round(change_pct, 4)
        article.ml_label_important = is_important
        article.ml_label_confidence = round(confidence, 4)
        article.ml_label_updated_at = timezone.now()
        article.save(update_fields=[
            'ml_label_24h', 'ml_label_important',
            'ml_label_confidence', 'ml_label_updated_at',
        ])

        return True

    def _get_tickers(self, article: NewsArticle) -> list[str]:
        """뉴스에서 관련 ticker 추출 (Company News source_tickers 우선)"""
        tickers = []

        # 1. NewsEntity에서 ticker (Finnhub Company News의 경우 정확)
        entity_symbols = list(
            article.entities.values_list('symbol', flat=True)
        )
        if entity_symbols:
            tickers.extend(entity_symbols)

        # 2. rule_tickers (규칙 엔진 결과)
        if article.rule_tickers:
            for t in article.rule_tickers:
                if t not in tickers:
                    tickers.append(t)

        return tickers[:5]  # 최대 5개

    def _calculate_change(
        self, ticker: str, base_date: date, label_date: date
    ) -> Optional[float]:
        """DailyPrice 기반 변동폭 계산"""
        try:
            base_price = DailyPrice.objects.filter(
                stock__symbol=ticker.upper(),
                date=base_date,
            ).first()

            label_price = DailyPrice.objects.filter(
                stock__symbol=ticker.upper(),
                date=label_date,
            ).first()

            if not base_price or not label_price:
                return None
            if not base_price.close_price or base_price.close_price == 0:
                return None

            change = (
                (float(label_price.close_price) - float(base_price.close_price))
                / float(base_price.close_price)
                * 100
            )
            return change

        except Exception as e:
            logger.debug(f"Price lookup failed for {ticker}: {e}")
            return None

    def _get_sector(self, ticker: str) -> str:
        """종목의 섹터 조회"""
        try:
            stock = Stock.objects.filter(symbol=ticker.upper()).first()
            if stock and stock.sector:
                return stock.sector
        except Exception:
            pass
        return ''

    def _calculate_confidence(self, article: NewsArticle, pub_date: date) -> float:
        """
        Label 신뢰도 계산

        규칙:
        - 당일 같은 종목 관련 뉴스 1건: 1.0
        - 2건: 0.6
        - 3건+: 0.3
        - 금요일 뉴스: ×0.5
        - 장 휴일 전날: ×0.5
        """
        tickers = self._get_tickers(article)
        if not tickers:
            return 0.3

        primary_ticker = tickers[0]

        # 같은 날 같은 종목의 뉴스 수
        same_day_count = NewsArticle.objects.filter(
            published_at__date=pub_date,
        ).filter(
            Q(entities__symbol=primary_ticker) |
            Q(rule_tickers__contains=[primary_ticker])
        ).distinct().count()

        # 기본 confidence
        if same_day_count <= 1:
            confidence = 1.0
        elif same_day_count == 2:
            confidence = 0.6
        else:
            confidence = 0.3

        # 금요일 감쇠
        if pub_date.weekday() == 4:  # Friday
            confidence *= 0.5

        # 장 휴일 전날 감쇠
        if is_pre_holiday(pub_date):
            confidence *= 0.5

        return max(confidence, 0.05)  # 최소 0.05
