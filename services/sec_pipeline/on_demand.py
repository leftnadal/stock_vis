"""
SEC-PR-15: On-demand filing 수집.

비-S&P 500 종목도 사용자 조회 시 수집 트리거.
1년 이내 문서 있으면 반환, 없으면 collect.delay 트리거.
중복 방지: 1시간 이내 로그 확인.
"""

import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


def get_or_collect_filing(symbol: str) -> Optional[dict]:
    """
    On-demand filing 조회 또는 수집 트리거.

    Returns:
        dict — 기존 데이터 있으면 즉시 반환
        None — 수집 트리거됨 (비동기)
    """
    from .models import FilingProcessLog, RawDocumentStore

    symbol = symbol.upper()
    one_year_ago = timezone.now() - timedelta(days=365)

    # 1년 이내 문서 확인
    existing = (
        RawDocumentStore.objects.filter(
            symbol_id=symbol, filing_date__gte=one_year_ago.date()
        )
        .order_by("-filing_date")
        .first()
    )

    if existing:
        return {
            "symbol": symbol,
            "status": "available",
            "filing_date": str(existing.filing_date),
            "fiscal_year": existing.fiscal_year,
            "doc_status": existing.status,
        }

    # 중복 방지: 1시간 이내 수집 로그 확인
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_log = FilingProcessLog.objects.filter(
        symbol=symbol,
        stage="fmp_metadata",
        started_at__gte=one_hour_ago,
    ).exists()

    if recent_log:
        return {
            "symbol": symbol,
            "status": "collecting",
            "message": "Collection already in progress",
        }

    # 비동기 수집 트리거
    from .tasks import collect_and_extract

    collect_and_extract.delay(symbol)

    logger.info(f"On-demand collection triggered for {symbol}")
    return None
