"""
Alpha Vantage NEWS_SENTIMENT Provider — broad 재설계 (co-mention 소스).

옛 provider는 per-symbol(tickers=X 종목별 루프)이라 무료 25/day 예산 초과로 제거됨
(df85496 "Alpha Vantage provider 전면 제거"). 본 모듈은 broad 재설계:

- `fetch_broad_news`: tickers **미지정** + topics·시간창·limit=1000·sort 로 시장 전체를
  한 호출에 크롤 → 기사당 다종목 `ticker_sentiment` 배열이 co-mention 신호가 됨.
- `_parse_article`: 검증된 옛 파싱(ticker_sentiment[]→entities, relevance/sentiment 보존)을
  복원하되 broad 문맥(symbol=None)에서 "요청 심볼 강제 추가"를 하지 않는다.
- per-symbol `fetch_company_news`는 **회귀 금지**를 위해 빈 리스트(broad 전용 provider).

저장은 aggregator `_save_articles`/`_save_entities`(update_or_create, 멱등)를 재사용한다.

무료 티어: NEWS_SENTIMENT limit≤1000, 초당 1req 스로틀, 25 req/day. 히스토리는
time_from/time_to 로 과거 창 조회 가능(실측 04-24까지 도달).
"""

import logging
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import requests

from .base import BaseNewsProvider, RawNewsArticle

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Rate Limit 초과 (AV Note/Information 메시지)."""

    pass


class AlphaVantageNewsProvider(BaseNewsProvider):
    """Alpha Vantage NEWS_SENTIMENT — broad 수집 전용."""

    BASE_URL = "https://www.alphavantage.co"

    # broad 유니버스 커버리지용 topic 세트 (AV NEWS_SENTIMENT 유효 topics 전 섹터).
    # AV topic 태깅이 느슨하므로 광범위하게 걸어 특정 섹터 편향을 피한다.
    DEFAULT_TOPICS = (
        "technology,earnings,mergers_and_acquisitions,financial_markets,"
        "finance,economy_macro,life_sciences,manufacturing,"
        "energy_transportation,retail_wholesale,real_estate"
    )

    # relevance 컷: AV가 이미 저관련(<0.3) 종목을 잘 안 붙임(실측 median 0.99, p10 0.60).
    # 미래 안전판으로만 낮게 둔다. 실질 노이즈 게이팅은 하류 Jaccard/응집도가 담당.
    DEFAULT_RELEVANCE_CUT = Decimal("0.15")

    # 무료 티어 스로틀: 초당 1req (실측). 백필/캘리브레이션이 예산을 나눠 쓴다.
    MIN_INTERVAL_SEC = 1.1

    def __init__(
        self,
        api_key: str,
        relevance_cut: Optional[Decimal] = None,
        throttle: bool = True,
    ):
        self.api_key = api_key
        self.relevance_cut = (
            relevance_cut if relevance_cut is not None else self.DEFAULT_RELEVANCE_CUT
        )
        self._throttle = throttle
        self._last_call_ts = 0.0

    # ── BaseNewsProvider 계약 (broad 전용이라 per-symbol/market 경로는 no-op) ──

    def fetch_company_news(
        self, symbol: str, from_date: datetime, to_date: datetime
    ) -> List[RawNewsArticle]:
        """per-symbol 회귀 금지 — broad 전용 provider이므로 빈 리스트."""
        return []

    def fetch_market_news(
        self, category: str = "general", limit: int = 50
    ) -> List[RawNewsArticle]:
        """카테고리 시장 뉴스 미지원 — broad 경로(fetch_broad_news)를 쓴다."""
        return []

    # ── broad 핵심 ──

    def fetch_broad_news(
        self,
        topics: Optional[str] = None,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
        limit: int = 1000,
        sort: str = "LATEST",
    ) -> List[RawNewsArticle]:
        """
        시장 전체 broad 크롤 (tickers 미지정). 기사당 다종목이 그대로 보존된다.

        Args:
            topics: AV topic CSV (기본 DEFAULT_TOPICS).
            time_from/time_to: 시간창(백필 페이징용). None이면 AV 기본(최근).
            limit: 1~1000 (무료 상한 1000).
            sort: LATEST | EARLIEST | RELEVANCE.

        Returns:
            List[RawNewsArticle] — entities에 다종목 ticker_sentiment 매핑.

        Raises:
            RateLimitExceeded: AV Note/Information(스로틀·한도) 반환 시.
        """
        params: Dict[str, Any] = {
            "function": "NEWS_SENTIMENT",
            "limit": limit,
            "sort": sort,
            "apikey": self.api_key,
        }
        # topics는 명시 지정 시에만 전송한다. AV topics 다중 지정은 교집합처럼 좁혀
        # 결과가 급감(11개→0건, 실측 2026-07-03)하므로 broad 기본은 topics 미지정(전체).
        # DEFAULT_TOPICS는 topic별 실험용으로 남겨두되 자동 주입하지 않는다.
        if topics:
            params["topics"] = topics
        if time_from is not None:
            params["time_from"] = time_from.strftime("%Y%m%dT%H%M")
        if time_to is not None:
            params["time_to"] = time_to.strftime("%Y%m%dT%H%M")

        self._respect_throttle()
        try:
            resp = requests.get(f"{self.BASE_URL}/query", params=params, timeout=40)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001 — 네트워크/HTTP 실패는 상위가 재시도
            logger.error(f"AV broad NEWS_SENTIMENT failed: {e}")
            return []

        # AV는 한도/스로틀을 HTTP 200 + JSON 메시지로 반환한다.
        if "feed" not in data:
            msg = data.get("Note") or data.get("Information") or data.get(
                "Error Message"
            )
            if msg and ("Error Message" in data):
                logger.error(f"AV API error: {msg}")
                return []
            logger.warning(f"AV throttle/limit: {msg}")
            raise RateLimitExceeded(str(msg))

        feed = data.get("feed", [])
        articles: List[RawNewsArticle] = []
        for item in feed:
            try:
                article = self._parse_article(item, symbol=None)
                if article:
                    articles.append(article)
            except Exception as e:  # noqa: BLE001 — 개별 기사 파싱 실패는 건너뜀
                logger.warning(f"AV parse error: {e}")
                continue

        logger.info(
            f"AV broad: {len(articles)} articles "
            f"(topics={params.get('topics', '(all)')}, window={params.get('time_from')}~{params.get('time_to')})"
        )
        return articles

    def _respect_throttle(self):
        """초당 1req 스로틀 (프로세스 로컬)."""
        if not self._throttle:
            return
        elapsed = time.time() - self._last_call_ts
        if elapsed < self.MIN_INTERVAL_SEC:
            time.sleep(self.MIN_INTERVAL_SEC - elapsed)
        self._last_call_ts = time.time()

    # ── 파싱 (df85496^ 복원 + broad 대응: symbol=None) ──

    def _parse_article(
        self, item: Dict[str, Any], symbol: Optional[str] = None
    ) -> Optional[RawNewsArticle]:
        """
        NEWS_SENTIMENT feed 항목 → RawNewsArticle.

        ticker_sentiment[] 전체를 entities로 보존(다종목=co-mention). relevance_cut
        미만 종목은 제외. broad(symbol=None)에서는 "요청 심볼 강제 추가"를 하지 않는다.
        """
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            return None

        # 길이 방어: NewsArticle.url/image_url은 varchar(2000). broad는 다양한 소스라
        # 초장 URL이 섞인다. url 초과는 skip(unique 키라 절단 시 충돌 위험), image_url 초과는 비움.
        if len(url) > 2000:
            logger.warning(f"AV url too long ({len(url)}) — skip: {url[:80]}...")
            return None

        published_at = self._parse_av_date(item.get("time_published", ""))
        if not published_at:
            return None

        sentiment_score = self._safe_decimal(item.get("overall_sentiment_score"))

        entities: List[Dict[str, Any]] = []
        for ts in item.get("ticker_sentiment", []):
            ticker = (ts.get("ticker") or "").upper()
            if not ticker:
                continue
            relevance = self._safe_decimal(ts.get("relevance_score", "1.0")) or Decimal(
                "1.00000"
            )
            if relevance < self.relevance_cut:
                continue
            entities.append(
                {
                    "symbol": ticker,
                    "entity_name": ticker,
                    "entity_type": "equity",
                    "source": "alpha_vantage",
                    "match_score": relevance,
                    "sentiment_score": self._safe_decimal(
                        ts.get("ticker_sentiment_score")
                    ),
                }
            )

        # per-symbol 문맥에서만 요청 심볼을 보강(broad는 symbol=None → 스킵).
        if symbol and not any(e["symbol"] == symbol.upper() for e in entities):
            entities.insert(
                0,
                {
                    "symbol": symbol.upper(),
                    "entity_name": symbol.upper(),
                    "entity_type": "equity",
                    "source": "alpha_vantage",
                    "match_score": Decimal("1.00000"),
                    "sentiment_score": sentiment_score,
                },
            )

        banner = item.get("banner_image", "") or ""
        if len(banner) > 2000:  # image_url varchar(2000) — 초과 시 비움(비필수 필드)
            banner = ""

        return RawNewsArticle(
            url=url,
            title=title,
            summary=item.get("summary", ""),
            source=item.get("source", "Alpha Vantage"),
            published_at=published_at,
            image_url=banner,
            language="en",
            category="company",
            provider_id=url,  # AV는 별도 ID 없음 → url을 provider_id로
            provider_name="alpha_vantage",
            sentiment_score=sentiment_score,
            sentiment_source="alpha_vantage" if sentiment_score is not None else "none",
            entities=entities,
            is_press_release=False,
        )

    @staticmethod
    def _parse_av_date(date_str: str) -> Optional[datetime]:
        """AV 날짜 'YYYYMMDDTHHmmss' (또는 분단위) 파싱."""
        if not date_str:
            return None
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        logger.warning(f"AV unparseable date: {date_str}")
        return None

    @staticmethod
    def _safe_decimal(value) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    # ── BaseNewsProvider rate-limit 계약 ──

    def get_rate_limit_key(self) -> str:
        return "news_rate_limit:alpha_vantage"

    def get_rate_limit(self) -> Dict[str, int]:
        # 무료 티어: 25 req/day, 초당 1req 스로틀.
        return {"calls": 25, "period": 86400}
