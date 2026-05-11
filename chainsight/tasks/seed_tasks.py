"""
Chain Sight 시드 선정 Celery Task — PR-2
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache

from stocks.models import Stock
from chainsight.utils import get_market_date
from chainsight.services.seed_selection import (
    select_seeds,
    resolve_seed_type,
    build_sector_summary,
    cache_seed_result,
)

logger = logging.getLogger(__name__)


@shared_task(name='chainsight-seed-selection', max_retries=2, default_retry_delay=60)
def run_seed_selection():
    """매일 12:00 UTC — Phase 1 시드 선정."""
    today = get_market_date()

    seeds = select_seeds(today)

    if not seeds:
        # 시드 부족 시: 전일 시드 유지
        prev_key = f'chainsight:seeds:{today - timedelta(days=1)}'
        prev = cache.get(prev_key)
        if prev:
            cache.set(f'chainsight:seeds:{today}', prev, timeout=86400)
            logger.warning(f'No seeds for {today}, carried over from previous market date')
        else:
            logger.warning(f'No seeds for {today} and no previous data available')
        return 0

    # bulk query로 Stock 메타데이터 조회 (N+1 방지)
    seed_symbols = list(seeds.keys())
    stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=seed_symbols)}

    seeds_list = []
    for symbol, info in seeds.items():
        stock = stock_map.get(symbol)
        if not stock:
            continue

        # market_cap: Decimal → float
        market_cap = float(stock.market_capitalization) if stock.market_capitalization else 0

        # change_percent: "1.23%" → float
        daily_return = info.get('daily_return', 0.0)
        if not daily_return:
            try:
                daily_return = round(float(stock.change_percent.rstrip('%')), 2)
            except (ValueError, AttributeError, TypeError):
                daily_return = 0.0

        seeds_list.append({
            'symbol': symbol,
            'name': stock.stock_name or '',
            'sector': stock.sector or '',
            'industry': stock.industry or '',
            'market_cap': market_cap,
            'daily_return': daily_return,
            'volume_ratio': info.get('volume_ratio', 0.0),
            'seed_reasons': info['reasons'],
            'seed_type': resolve_seed_type(info['reasons']),
            'signal_count': info['signal_count'],
        })

    sector_summary = build_sector_summary(seeds, today)
    cache_seed_result(today, sector_summary, seeds_list)
    logger.info(f'Seed selection complete: {len(seeds_list)} seeds, {len(sector_summary)} sectors')
    return len(seeds_list)
