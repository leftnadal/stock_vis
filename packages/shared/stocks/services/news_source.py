"""
News source 추상화 (NEWSFIX-BE · D-NEWSMATCH-FIX-PATH 1′).

EODNewsEnricher가 뉴스를 조회하는 방식을 의존성 주입 seam으로 분리한다.
- 기본 구현 `StockNewsSource` = 현행 StockNews 쿼리를 **그대로** 감싼다(행위 보존).
- 실뉴스(NewsEntity, `services.news`) 기반 구현은 **앱 계층 슬라이스**에서 이 프로토콜을
  만족시키는 어댑터를 주입한다 — shared는 `apps.*`/`services.*`를 import하지 않는다
  (단방향 경계 · D-BOUNDARY-NO-DYNAMIC-EVASION: 동적 import 우회도 금지).

프로토콜 반환값은 아래 속성을 갖는 객체(duck-typed)여야 한다 — EODNewsEnricher._build_news_dict가
읽는 필드와 동일:
    headline, summary, source, url, sentiment, published_at
`published_at`은 `.date()`를 갖는 datetime 이거나 None.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional, Protocol, runtime_checkable

from packages.shared.stocks.models import StockNews


@runtime_checkable
class NewsSource(Protocol):
    """enricher가 소비하는 뉴스 조회 seam.

    구현체는 매칭 창(창 규약)을 호출자(enricher)가 넘긴 날짜 인자로만 판단한다 —
    창 계산(today/7d/30d)은 enricher가 소유하고, source는 조회만 한다.
    """

    def latest_on_date(self, symbol: str, target_date: date) -> Optional[Any]:
        """symbol 매칭 + 해당 일자 발행 뉴스 중 최신 1건 (없으면 None)."""
        ...

    def latest_between(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[Any]:
        """symbol 매칭 + [start_date, end_date] 발행 뉴스 중 최신 1건 (없으면 None)."""
        ...

    def latest_by_industry_between(
        self, industry: str, start_date: date, end_date: date
    ) -> Optional[Any]:
        """industry 매칭 + [start_date, end_date] 발행 뉴스 중 최신 1건 (없으면 None)."""
        ...


class StockNewsSource:
    """기본 source — 현행 StockNews 쿼리 4종을 그대로 재현(행위 보존).

    NEWSFIX-BE 이전 enricher의 인라인 쿼리와 **동일**한 filter/order를 사용한다.
    StockNews 테이블이 비어 있으면(현 운영 상태) 전건 None → enricher는 profile 폴백.
    """

    def latest_on_date(self, symbol: str, target_date: date) -> Optional[Any]:
        return (
            StockNews.objects.filter(
                symbol=symbol,
                published_at__date=target_date,
            )
            .order_by("-published_at")
            .first()
        )

    def latest_between(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[Any]:
        return (
            StockNews.objects.filter(
                symbol=symbol,
                published_at__date__gte=start_date,
                published_at__date__lte=end_date,
            )
            .order_by("-published_at")
            .first()
        )

    def latest_by_industry_between(
        self, industry: str, start_date: date, end_date: date
    ) -> Optional[Any]:
        return (
            StockNews.objects.filter(
                industry=industry,
                published_at__date__gte=start_date,
                published_at__date__lte=end_date,
            )
            .order_by("-published_at")
            .first()
        )
