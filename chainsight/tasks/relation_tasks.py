"""
CS-2-2~2-3: 관계 발견 태스크
- extract_co_mentions: 뉴스 동시출현 쌍 추출
- calculate_price_co_movement: 주가 동조 계산
"""

import logging
from collections import defaultdict
from datetime import timedelta
from itertools import combinations

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, soft_time_limit=1800, time_limit=1860)
def extract_co_mentions(self, days_back: int = 90):
    """
    CS-2-2: NewsEntity에서 동시출현 쌍 추출 → CoMentionEdge 적재.
    Celery Beat: 매일 06:30.
    """
    from news.models import NewsEntity
    from chainsight.models import CoMentionEdge, ChainNewsEvent
    from chainsight.utils import normalize_pair
    from django.db.models import Count

    cutoff = timezone.now() - timedelta(days=days_back)

    # 2개 이상 entity가 있는 기사 찾기
    multi_news_ids = list(
        NewsEntity.objects.filter(news__published_at__gte=cutoff)
        .values('news_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gte=2)
        .values_list('news_id', flat=True)
    )

    # 기사별 symbol 수집
    pair_counts = defaultdict(lambda: {"count": 0, "last_date": None, "first_date": None})
    events_saved = 0

    for news_id in multi_news_ids:
        entities = NewsEntity.objects.filter(news_id=news_id).select_related('news')
        symbols = list(set(e.symbol for e in entities if e.symbol))

        if len(symbols) < 2:
            continue

        published_at = entities[0].news.published_at

        # ChainNewsEvent 중간 저장
        news_obj = entities[0].news
        try:
            _, created = ChainNewsEvent.objects.get_or_create(
                source=news_obj.source or 'unknown',
                source_id=str(news_obj.id),
                defaults={
                    'symbol_id': symbols[0],
                    'title': (news_obj.title or '')[:500],
                    'summary': (news_obj.summary or '')[:500],
                    'published_at': published_at,
                    'co_mentioned_symbols': symbols[1:],
                }
            )
            if created:
                events_saved += 1
        except Exception:
            pass

        # 조합 추출
        for a, b in combinations(symbols, 2):
            pair = normalize_pair(a, b)
            pair_counts[pair]["count"] += 1
            dt = published_at.date() if published_at else None
            if dt:
                if not pair_counts[pair]["last_date"] or dt > pair_counts[pair]["last_date"]:
                    pair_counts[pair]["last_date"] = dt
                if not pair_counts[pair]["first_date"] or dt < pair_counts[pair]["first_date"]:
                    pair_counts[pair]["first_date"] = dt

    # CoMentionEdge upsert
    created_cnt, updated_cnt = 0, 0
    for (a, b), data in pair_counts.items():
        obj, is_new = CoMentionEdge.objects.get_or_create(
            symbol_a=a, symbol_b=b,
            defaults={
                "co_mention_count": data["count"],
                "last_co_mention_date": data["last_date"],
                "first_co_mention_date": data["first_date"],
            }
        )
        if is_new:
            created_cnt += 1
        else:
            obj.co_mention_count = data["count"]  # 전체 기간 재계산이므로 덮어쓰기
            if data["last_date"]:
                obj.last_co_mention_date = data["last_date"]
            if data["first_date"]:
                obj.first_co_mention_date = data["first_date"]
            obj.save()
            updated_cnt += 1

    result = {
        "news_checked": len(multi_news_ids),
        "events_saved": events_saved,
        "pairs": len(pair_counts),
        "created": created_cnt,
        "updated": updated_cnt,
    }
    logger.info(f"CoMention 추출: {result}")
    return result


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_price_co_movement(self, period_days: int = 90):
    """
    CS-2-3: 주가 동조 계산. PEER_OF 관계가 있는 쌍에 대해 90일 correlation.
    Celery Beat: 주 1회 (일요일 03:00).
    """
    import numpy as np
    from decimal import Decimal
    from stocks.models import DailyPrice
    from chainsight.models import PriceCoMovement
    from chainsight.graph import get_graph_repository

    repo = get_graph_repository()

    # PEER_OF 관계가 있는 쌍 조회
    peers = repo.run_query("""
        MATCH (a:Stock)-[:PEER_OF]-(b:Stock)
        WHERE a.ticker < b.ticker
        RETURN DISTINCT a.ticker AS sym_a, b.ticker AS sym_b
    """)

    cutoff = timezone.now() - timedelta(days=period_days + 10)
    period_key = f"{period_days}d"
    success, fail = 0, 0

    for pair in peers:
        try:
            sym_a, sym_b = pair["sym_a"], pair["sym_b"]

            prices_a = list(
                DailyPrice.objects.filter(stock_id=sym_a, date__gte=cutoff)
                .order_by('date').values_list('date', 'close_price')
            )
            prices_b = list(
                DailyPrice.objects.filter(stock_id=sym_b, date__gte=cutoff)
                .order_by('date').values_list('date', 'close_price')
            )

            if len(prices_a) < 20 or len(prices_b) < 20:
                continue

            # 날짜 교집합
            dates_a = {d: float(p) for d, p in prices_a}
            dates_b = {d: float(p) for d, p in prices_b}
            common_dates = sorted(set(dates_a.keys()) & set(dates_b.keys()))

            if len(common_dates) < 20:
                continue

            vals_a = np.array([dates_a[d] for d in common_dates])
            vals_b = np.array([dates_b[d] for d in common_dates])

            # 수익률 correlation
            returns_a = np.diff(vals_a) / vals_a[:-1]
            returns_b = np.diff(vals_b) / vals_b[:-1]

            if len(returns_a) < 10:
                continue

            corr = float(np.corrcoef(returns_a, returns_b)[0, 1])
            if np.isnan(corr):
                continue

            PriceCoMovement.objects.update_or_create(
                symbol_a=sym_a, symbol_b=sym_b, period=period_key,
                defaults={'correlation': Decimal(str(round(corr, 4)))}
            )
            success += 1
        except Exception as e:
            fail += 1

        if (success + fail) % 500 == 0 and (success + fail) > 0:
            logger.info(f"PriceCoMovement: {success + fail}/{len(peers)} processed")

    result = {"total_peers": len(peers), "success": success, "fail": fail}
    logger.info(f"PriceCoMovement: {result}")
    return result
