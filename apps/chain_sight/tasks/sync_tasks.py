"""
CS-2-5: CompanyChainProfile 집약 + Phase 3 동기화 태스크.
"""

import logging

from celery import shared_task
from django.utils import timezone

from packages.shared.stocks.models import SP500Constituent, Stock

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def aggregate_chain_profiles(self):
    """
    CS-2-5: 개별 프로파일 → ChainProfile 집약. Celery Beat: 주 1회 (일요일 05:00).
    """
    from apps.chain_sight.models import (
        CompanyCapitalDNA,
        CompanyChainProfile,
        CompanyGrowthStage,
        CompanyNarrativeTag,
        CompanySensitivityProfile,
    )

    sp500 = set(
        SP500Constituent.objects.filter(is_active=True).values_list("symbol", flat=True)
    )
    success, fail = 0, 0

    for symbol in sp500:
        try:
            stock = Stock.objects.filter(symbol=symbol).first()
            if not stock:
                continue

            # audit P0 #9: neo4j_synced → neo4j_dirty (의미 반전, True=동기화 필요)
            defaults = {"neo4j_dirty": True}

            # GrowthStage
            gs = CompanyGrowthStage.objects.filter(symbol=stock).first()
            if gs:
                defaults["growth_stage"] = gs.stage
                defaults["revenue_cagr_3y"] = gs.revenue_cagr_3y

            # CapitalDNA
            cd = CompanyCapitalDNA.objects.filter(symbol=stock).first()
            if cd:
                defaults["capital_type"] = cd.capital_type
                defaults["net_cash_position"] = cd.net_cash_position

            # SensitivityProfile (있으면)
            sp = CompanySensitivityProfile.objects.filter(symbol=stock).first()
            if sp:
                defaults["rate_sensitivity"] = sp.rate_sensitivity
                defaults["forex_sensitivity"] = sp.forex_sensitivity
                defaults["commodity_sensitivity"] = sp.commodity_sensitivity
                defaults["regulation_type"] = sp.regulation_type
                defaults["beta"] = sp.beta

            # NarrativeTag (있으면)
            nt = CompanyNarrativeTag.objects.filter(symbol=stock).first()
            if nt:
                defaults["primary_narrative"] = nt.primary_narrative
                defaults["theme_tags"] = nt.theme_tags
                defaults["narrative_sentiment"] = nt.narrative_sentiment

            # validation CategorySignal (서비스 레이어)
            try:
                from services.validation.models import CategorySignal

                signals = CategorySignal.objects.filter(symbol=stock)
                for sig in signals:
                    if sig.category == "profitability" and sig.score:
                        defaults["score_profitability"] = sig.score
                    elif sig.category == "growth" and sig.score:
                        defaults["score_growth"] = sig.score
                    elif sig.category == "financial_structure" and sig.score:
                        defaults["score_financial_structure"] = sig.score
            except Exception:
                pass

            # completeness 계산
            total_fields = 15
            filled = sum(1 for v in defaults.values() if v and v != False)
            from decimal import Decimal

            defaults["profile_completeness"] = Decimal(
                str(round(filled / total_fields, 2))
            )

            CompanyChainProfile.objects.update_or_create(
                symbol=stock, defaults=defaults
            )
            success += 1
        except Exception as e:
            fail += 1
            logger.error(f"ChainProfile {symbol}: {e}")

    result = {"success": success, "fail": fail}
    logger.info(f"ChainProfile 집약: {result}")
    return result


@shared_task(bind=True, max_retries=1, soft_time_limit=1800, time_limit=1860)
def sync_profiles_to_neo4j(self):
    """CS-3-1: ChainProfile → Neo4j :Stock 속성 Delta Sync."""
    from apps.chain_sight.graph import get_graph_repository
    from apps.chain_sight.models import CompanyChainProfile

    repo = get_graph_repository()
    pending = CompanyChainProfile.objects.filter(neo4j_dirty=True)
    total = pending.count()
    success, fail = 0, 0

    for profile in pending.iterator():
        try:
            props = {}
            for field in [
                "growth_stage",
                "capital_type",
                "rate_sensitivity",
                "forex_sensitivity",
                "commodity_sensitivity",
                "regulation_type",
                "primary_narrative",
                "narrative_sentiment",
                "business_model_type",
                "overall_grade",
            ]:
                val = getattr(profile, field, None)
                if val:
                    props[field] = str(val)

            for field in [
                "revenue_cagr_3y",
                "beta",
                "score_profitability",
                "score_growth",
                "score_financial_structure",
                "profile_completeness",
            ]:
                val = getattr(profile, field, None)
                if val is not None:
                    props[field] = float(val)

            if profile.net_cash_position is not None:
                props["net_cash_position"] = profile.net_cash_position

            if profile.theme_tags:
                props["theme_tags"] = profile.theme_tags

            if props:
                repo.run_query(
                    "MATCH (s:Stock {ticker: $ticker}) SET s += $props",
                    {"ticker": profile.symbol_id, "props": props},
                )

            profile.neo4j_dirty = False
            profile.neo4j_synced_at = timezone.now()
            profile.save(update_fields=["neo4j_dirty", "neo4j_synced_at"])
            success += 1
        except Exception as e:
            fail += 1
            logger.error(f"Profile sync {profile.symbol_id}: {e}")

    logger.info(f"Profile sync: {success}/{total} 성공, {fail} 실패")
    return {"total": total, "success": success, "fail": fail}


@shared_task(bind=True, max_retries=1, soft_time_limit=1800, time_limit=1860)
def sync_relations_to_neo4j(self):
    """
    CS-3-2: RelationConfidence → Neo4j 엣지 동기화.
    동적 타입 지원하는 dirty sync로 위임. 레거시 RELATED_TO 엣지 1회 정리.
    """
    from django.core.cache import cache

    from apps.chain_sight.models import RelationConfidence
    from apps.chain_sight.services.neo4j_sync import sync_dirty_relations

    # ── 레거시 RELATED_TO 엣지 1회 정리 ──
    cleanup_key = "chainsight:related_to_cleanup_v1"
    if not cache.get(cleanup_key):
        try:
            from apps.chain_sight.graph import get_graph_repository

            repo = get_graph_repository()
            repo.run_query("MATCH ()-[r:RELATED_TO]-() DELETE r")
            # 기존 레코드 dirty 리셋 → dirty sync가 동적 타입으로 재생성
            # audit P0 #9: synced_to_neo4j 제거, neo4j_dirty 단일 소스
            reset_count = RelationConfidence.objects.filter(
                relation_status__in=["confirmed", "probable"]
            ).update(neo4j_dirty=True)
            cache.set(cleanup_key, True, timeout=86400 * 365)
            logger.info(
                f"Legacy RELATED_TO cleanup: edges deleted, {reset_count} records reset"
            )
        except Exception as e:
            logger.error(f"Legacy cleanup failed: {e}")

    # ── dirty sync 위임 (동적 타입: PEER_OF, CO_MENTIONED, PRICE_CORRELATED 등) ──
    count = sync_dirty_relations()
    logger.info(f"Relation sync via dirty sync: {count} relations synced")
    return {"synced": count}
