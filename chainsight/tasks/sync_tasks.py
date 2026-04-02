"""
CS-2-5: CompanyChainProfile 집약 + Phase 3 동기화 태스크.
"""

import logging
from celery import shared_task
from django.utils import timezone

from stocks.models import Stock, SP500Constituent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def aggregate_chain_profiles(self):
    """
    CS-2-5: 개별 프로파일 → ChainProfile 집약. Celery Beat: 주 1회 (일요일 05:00).
    """
    from chainsight.models import (
        CompanyChainProfile, CompanyGrowthStage, CompanyCapitalDNA,
        CompanySensitivityProfile, CompanyNarrativeTag,
    )

    sp500 = set(SP500Constituent.objects.filter(is_active=True).values_list('symbol', flat=True))
    success, fail = 0, 0

    for symbol in sp500:
        try:
            stock = Stock.objects.filter(symbol=symbol).first()
            if not stock:
                continue

            defaults = {'neo4j_synced': False}

            # GrowthStage
            gs = CompanyGrowthStage.objects.filter(symbol=stock).first()
            if gs:
                defaults['growth_stage'] = gs.stage
                defaults['revenue_cagr_3y'] = gs.revenue_cagr_3y

            # CapitalDNA
            cd = CompanyCapitalDNA.objects.filter(symbol=stock).first()
            if cd:
                defaults['capital_type'] = cd.capital_type
                defaults['net_cash_position'] = cd.net_cash_position

            # SensitivityProfile (있으면)
            sp = CompanySensitivityProfile.objects.filter(symbol=stock).first()
            if sp:
                defaults['rate_sensitivity'] = sp.rate_sensitivity
                defaults['forex_sensitivity'] = sp.forex_sensitivity
                defaults['commodity_sensitivity'] = sp.commodity_sensitivity
                defaults['regulation_type'] = sp.regulation_type
                defaults['beta'] = sp.beta

            # NarrativeTag (있으면)
            nt = CompanyNarrativeTag.objects.filter(symbol=stock).first()
            if nt:
                defaults['primary_narrative'] = nt.primary_narrative
                defaults['theme_tags'] = nt.theme_tags
                defaults['narrative_sentiment'] = nt.narrative_sentiment

            # validation CategorySignal (서비스 레이어)
            try:
                from validation.models import CategorySignal
                signals = CategorySignal.objects.filter(symbol=stock)
                for sig in signals:
                    if sig.category == 'profitability' and sig.score:
                        defaults['score_profitability'] = sig.score
                    elif sig.category == 'growth' and sig.score:
                        defaults['score_growth'] = sig.score
                    elif sig.category == 'financial_structure' and sig.score:
                        defaults['score_financial_structure'] = sig.score
            except Exception:
                pass

            # completeness 계산
            total_fields = 15
            filled = sum(1 for v in defaults.values() if v and v != False)
            from decimal import Decimal
            defaults['profile_completeness'] = Decimal(str(round(filled / total_fields, 2)))

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
    """CS-3-1: ChainProfile → Neo4j 속성 동기화. Phase 3 완료 후 활성화."""
    # Phase 3에서 구현
    logger.info("sync_profiles_to_neo4j: Phase 3에서 구현 예정")
    return {"status": "not_implemented"}


@shared_task(bind=True, max_retries=1, soft_time_limit=1800, time_limit=1860)
def sync_relations_to_neo4j(self):
    """CS-3-2: RelationConfidence → Neo4j 엣지 동기화. Phase 3 완료 후 활성화."""
    logger.info("sync_relations_to_neo4j: Phase 3에서 구현 예정")
    return {"status": "not_implemented"}
