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
    from django.db.models import Count

    from apps.chain_sight.models import ChainNewsEvent, CoMentionEdge
    from apps.chain_sight.utils import normalize_pair
    from news.models import NewsEntity

    cutoff = timezone.now() - timedelta(days=days_back)

    # 2개 이상 entity가 있는 기사 찾기
    multi_news_ids = list(
        NewsEntity.objects.filter(news__published_at__gte=cutoff)
        .values("news_id")
        .annotate(cnt=Count("id"))
        .filter(cnt__gte=2)
        .values_list("news_id", flat=True)
    )

    # 기사별 symbol 수집
    pair_counts = defaultdict(
        lambda: {"count": 0, "last_date": None, "first_date": None}
    )
    events_saved = 0

    for news_id in multi_news_ids:
        entities = NewsEntity.objects.filter(news_id=news_id).select_related("news")
        symbols = list(set(e.symbol for e in entities if e.symbol))

        if len(symbols) < 2:
            continue

        published_at = entities[0].news.published_at

        # ChainNewsEvent 중간 저장
        news_obj = entities[0].news
        try:
            _, created = ChainNewsEvent.objects.get_or_create(
                source=news_obj.source or "unknown",
                source_id=str(news_obj.id),
                defaults={
                    "symbol_id": symbols[0],
                    "title": (news_obj.title or "")[:500],
                    "summary": (news_obj.summary or "")[:500],
                    "published_at": published_at,
                    "co_mentioned_symbols": symbols[1:],
                },
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
                if (
                    not pair_counts[pair]["last_date"]
                    or dt > pair_counts[pair]["last_date"]
                ):
                    pair_counts[pair]["last_date"] = dt
                if (
                    not pair_counts[pair]["first_date"]
                    or dt < pair_counts[pair]["first_date"]
                ):
                    pair_counts[pair]["first_date"] = dt

    # CoMentionEdge upsert
    created_cnt, updated_cnt = 0, 0
    for (a, b), data in pair_counts.items():
        obj, is_new = CoMentionEdge.objects.get_or_create(
            symbol_a=a,
            symbol_b=b,
            defaults={
                "co_mention_count": data["count"],
                "last_co_mention_date": data["last_date"],
                "first_co_mention_date": data["first_date"],
            },
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
    from decimal import Decimal

    import numpy as np

    from apps.chain_sight.graph import get_graph_repository
    from apps.chain_sight.models import PriceCoMovement
    from packages.shared.stocks.models import DailyPrice

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
                .order_by("date")
                .values_list("date", "close_price")
            )
            prices_b = list(
                DailyPrice.objects.filter(stock_id=sym_b, date__gte=cutoff)
                .order_by("date")
                .values_list("date", "close_price")
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
                symbol_a=sym_a,
                symbol_b=sym_b,
                period=period_key,
                defaults={"correlation": Decimal(str(round(corr, 4)))},
            )
            success += 1
        except Exception as e:
            fail += 1

        if (success + fail) % 500 == 0 and (success + fail) > 0:
            logger.info(f"PriceCoMovement: {success + fail}/{len(peers)} processed")

    result = {"total_peers": len(peers), "success": success, "fail": fail}
    logger.info(f"PriceCoMovement: {result}")
    return result


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def update_relation_confidence(self):
    """
    CS-2-4: RelationConfidence 종합 판정. Celery Beat: 주 1회 (일요일 04:00).
    """
    from apps.chain_sight.graph import get_graph_repository
    from apps.chain_sight.models import (
        CoMentionEdge,
        PriceCoMovement,
        RelationConfidence,
    )
    from apps.chain_sight.utils import normalize_pair

    repo = get_graph_repository()

    # 1) 모든 PEER_OF 쌍 수집
    peers = repo.run_query("""
        MATCH (a:Stock)-[:PEER_OF]-(b:Stock)
        WHERE a.ticker < b.ticker
        RETURN DISTINCT a.ticker AS sym_a, b.ticker AS sym_b
    """)

    # 2) 같은 industry 쌍
    same_industry = repo.run_query("""
        MATCH (a:Stock)-[:BELONGS_TO_INDUSTRY]->(i:Industry)<-[:BELONGS_TO_INDUSTRY]-(b:Stock)
        WHERE a.ticker < b.ticker
        RETURN DISTINCT a.ticker AS sym_a, b.ticker AS sym_b
    """)

    # 모든 후보 쌍 통합
    all_pairs = set()
    peer_set = set()
    industry_set = set()

    for p in peers:
        pair = (p["sym_a"], p["sym_b"])
        all_pairs.add(pair)
        peer_set.add(pair)

    for p in same_industry:
        pair = (p["sym_a"], p["sym_b"])
        all_pairs.add(pair)
        industry_set.add(pair)

    # co-mention 쌍
    co_mention_map = {}
    for cm in CoMentionEdge.objects.filter(co_mention_count__gte=2):
        pair = normalize_pair(cm.symbol_a, cm.symbol_b)
        co_mention_map[pair] = cm.co_mention_count
        all_pairs.add(pair)

    # price correlation 쌍
    price_map = {}
    for pc in PriceCoMovement.objects.filter(correlation__gte=0.5):
        pair = normalize_pair(pc.symbol_a, pc.symbol_b)
        price_map[pair] = float(pc.correlation)
        all_pairs.add(pair)

    # 3) 각 쌍에 대해 관계 타입별 RelationConfidence 판정
    #    - peer/industry → PEER_OF (truth)
    #    - co_mention → CO_MENTIONED (market)
    #    - price_corr → PRICE_CORRELATED (market)
    created, updated = 0, 0
    for sym_a, sym_b in all_pairs:
        has_peer = (sym_a, sym_b) in peer_set
        has_industry = (sym_a, sym_b) in industry_set
        has_news = (sym_a, sym_b) in co_mention_map
        has_price = (sym_a, sym_b) in price_map

        # ── PEER_OF (truth): peer 또는 industry 증거가 있을 때 ──
        if has_peer or has_industry:
            peer_sources = []
            if has_peer:
                peer_sources.append("peer")
            if has_industry:
                peer_sources.append("industry")
            if len(peer_sources) >= 2:
                tier, status, score = 1, "confirmed", 85
            else:
                tier, status, score = 2, "probable", 60

            parts = []
            if has_peer:
                parts.append("Peer 관계")
            if has_industry:
                parts.append("같은 산업")
            summary = " + ".join(parts)

            obj, is_new = RelationConfidence.objects.update_or_create(
                symbol_a=sym_a,
                symbol_b=sym_b,
                relation_type="PEER_OF",
                defaults={
                    "relation_category": "truth",
                    "canonical_direction": "both",
                    "relation_status": status,
                    "truth_score": score,
                    "evidence_tier_best": tier,
                    "evidence_count_total": len(peer_sources),
                    "evidence_count_independent": len(peer_sources),
                    "evidence_sources": {"sources": peer_sources},
                    "has_peer_source": has_peer,
                    "has_industry_source": has_industry,
                    "has_news_source": False,
                    "has_price_source": False,
                    "relation_basis_summary": summary,
                    # audit P0 #9: synced_to_neo4j 제거. update_or_create는 save()를 호출하므로 neo4j_dirty=True 자동.
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        # ── CO_MENTIONED (market): 뉴스 동시출현 증거 ──
        if has_news:
            count = co_mention_map[(sym_a, sym_b)]
            if count >= 10:
                tier, status, score = 1, "confirmed", 85
            elif count >= 5:
                tier, status, score = 2, "probable", 60
            else:
                tier, status, score = 3, "weak", 35

            obj, is_new = RelationConfidence.objects.update_or_create(
                symbol_a=sym_a,
                symbol_b=sym_b,
                relation_type="CO_MENTIONED",
                defaults={
                    "relation_category": "market",
                    "canonical_direction": "both",
                    "relation_status": status,
                    "market_score": score,
                    "truth_score": 0,
                    "evidence_tier_best": tier,
                    "evidence_count_total": 1,
                    "evidence_count_independent": 1,
                    "evidence_sources": {
                        "sources": ["news"],
                        "co_mention_count": count,
                    },
                    "has_peer_source": False,
                    "has_industry_source": False,
                    "has_news_source": True,
                    "has_price_source": False,
                    "relation_basis_summary": f"뉴스 동시출현 {count}회",
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        # ── PRICE_CORRELATED (market): 주가 상관 증거 ──
        if has_price:
            corr = price_map[(sym_a, sym_b)]
            if corr >= 0.8:
                tier, status, score = 1, "confirmed", 85
            elif corr >= 0.6:
                tier, status, score = 2, "probable", 60
            else:
                tier, status, score = 3, "weak", 35

            obj, is_new = RelationConfidence.objects.update_or_create(
                symbol_a=sym_a,
                symbol_b=sym_b,
                relation_type="PRICE_CORRELATED",
                defaults={
                    "relation_category": "market",
                    "canonical_direction": "both",
                    "relation_status": status,
                    "market_score": score,
                    "truth_score": 0,
                    "evidence_tier_best": tier,
                    "evidence_count_total": 1,
                    "evidence_count_independent": 1,
                    "evidence_sources": {"sources": ["price"], "correlation": corr},
                    "has_peer_source": False,
                    "has_industry_source": False,
                    "has_news_source": False,
                    "has_price_source": True,
                    "relation_basis_summary": f"주가 상관 {corr:.2f}",
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

    result = {"total_pairs": len(all_pairs), "created": created, "updated": updated}
    logger.info(f"RelationConfidence: {result}")
    return result


@shared_task(bind=True, max_retries=0, soft_time_limit=600, time_limit=660)
def check_stale_and_decay(self):
    """
    CS-2-4: Stale 하향 전이. Celery Beat: 주 1회 (일요일 04:30).
    """
    from apps.chain_sight.models import RelationConfidence

    now = timezone.now()
    decayed = 0

    # audit P0 #9: queryset.update()는 save() 미호출 → neo4j_dirty 수동 토글
    # confirmed → stale (90일)
    stale = RelationConfidence.objects.filter(
        relation_status="confirmed",
        last_observed_at__lt=now - timedelta(days=90),
    )
    decayed += stale.update(relation_status="stale", neo4j_dirty=True)

    # probable → weak (60일)
    weak = RelationConfidence.objects.filter(
        relation_status="probable",
        last_observed_at__lt=now - timedelta(days=60),
    )
    decayed += weak.update(relation_status="weak", neo4j_dirty=True)

    # weak → hidden (30일)
    hidden = RelationConfidence.objects.filter(
        relation_status="weak",
        last_observed_at__lt=now - timedelta(days=30),
    )
    decayed += hidden.update(relation_status="hidden", neo4j_dirty=True)

    logger.info(f"Stale decay: {decayed}건 하향 전이")
    return {"decayed": decayed}
