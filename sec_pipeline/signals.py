"""
SEC-PR-8: post_save signal — UnmatchedCompanyQueue resolved 처리.

status='matched' + resolved_ticker 있을 때:
1. 같은 이름 + 같은 sector의 evidence.target_company 업데이트
2. CompanyAlias 등록
3. neo4j_dirty=True

⚠️ 다른 sector evidence에 전파 금지
⚠️ Neo4j 직접 동기화 금지. dirty flag만.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='sec_pipeline.UnmatchedCompanyQueue')
def on_unmatched_resolved(sender, instance, **kwargs):
    """UnmatchedCompanyQueue가 matched로 변경되면 evidence 업데이트."""
    if instance.status != 'matched' or not instance.resolved_ticker:
        return

    from stocks.models import Stock
    from .models import SupplyChainEvidence, CompanyAlias

    resolved_ticker = instance.resolved_ticker.upper()
    target_stock = Stock.objects.filter(symbol=resolved_ticker).first()

    # target_stock이 DB에 없으면 CompanyAlias만 등록
    raw_name = instance.raw_company_name

    # 같은 이름의 evidence 업데이트 — 같은 sector 내로 제한
    source_sectors = instance.source_sectors or ['']
    updated = 0

    for sector in source_sectors:
        # 해당 sector 소속 source 기업의 evidence만 선별
        qs = SupplyChainEvidence.objects.filter(
            target_company_name=raw_name,
            target_company__isnull=True,
        )

        if sector:
            # source_company의 sector가 일치하는 것만
            qs = qs.filter(source_company__sector__iexact=sector)

        if target_stock:
            count = qs.update(target_company=target_stock, neo4j_dirty=True)
            updated += count

    if updated:
        logger.info(
            f"Resolved: {raw_name} → {resolved_ticker} "
            f"({updated} evidences updated, neo4j_dirty=True)"
        )

    # CompanyAlias 등록 (sector별)
    for sector in source_sectors:
        CompanyAlias.objects.get_or_create(
            alias=raw_name,
            context_sector=sector or '',
            defaults={
                'ticker': resolved_ticker,
                'source': 'admin_resolved',
            }
        )
        logger.info(f"CompanyAlias: {raw_name} → {resolved_ticker} [sector={sector or 'global'}]")
