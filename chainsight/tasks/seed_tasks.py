"""
Chain Sight 시드 선정 + Heat Score Celery Tasks
"""

import logging
from datetime import timedelta

import pandas as pd
from celery import shared_task
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from chainsight.models import CoMentionEdge, RelationConfidence
from chainsight.services.seed_selection import (
    build_sector_summary,
    cache_seed_result,
    resolve_seed_type,
    select_seeds,
)
from chainsight.utils import get_market_date
from packages.shared.stocks.models import DailyPrice, Stock

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


# ── CS-4-4: Heat Score 배치 ──

HEAT_WEIGHTS = {
    'price': 0.25,
    'volume': 0.25,
    'relation_change': 0.25,
    'news_activation': 0.25,
}


@shared_task(name='chainsight-heat-score-daily', max_retries=1, soft_time_limit=300)
def calculate_heat_scores():
    """매일 실행 — 모든 :Stock의 heat_score 계산 → Neo4j 저장."""
    from chainsight.graph import get_graph_repository

    start_time = timezone.now()

    # 1) 최근 가격 데이터 로드
    cutoff = timezone.localdate() - timedelta(days=25)
    qs = DailyPrice.objects.filter(date__gte=cutoff).values_list(
        'stock_id', 'date', 'close_price', 'volume'
    )
    rows = list(qs)
    if not rows:
        logger.warning('heat_score: no DailyPrice data')
        return {'processed': 0, 'errors': 0}

    price_df = pd.DataFrame(rows, columns=['symbol', 'date', 'close', 'volume'])
    price_df = price_df.sort_values(['symbol', 'date'])

    # 2) 전체 symbol
    symbols = list(Stock.objects.values_list('symbol', flat=True))

    # 3) price_signal 배치 계산 (percentile rank)
    price_signals = _compute_price_signals_batch(price_df, symbols)

    repo = get_graph_repository()
    processed, errors = 0, 0

    for symbol in symbols:
        try:
            price_sig = price_signals.get(symbol, 0.0)
            volume_sig = _compute_volume_signal(symbol, price_df)
            relation_sig = _compute_relation_change_signal(symbol)
            news_sig = _compute_news_activation(symbol)

            heat = (
                HEAT_WEIGHTS['price'] * price_sig
                + HEAT_WEIGHTS['volume'] * volume_sig
                + HEAT_WEIGHTS['relation_change'] * relation_sig
                + HEAT_WEIGHTS['news_activation'] * news_sig
            )

            repo.run_query("""
                MATCH (s:Stock {ticker: $ticker})
                SET s.heat_score = $heat,
                    s.price_signal = $ps,
                    s.volume_signal = $vs,
                    s.relation_change_signal = $rs,
                    s.news_activation = $ns,
                    s.heat_score_updated_at = datetime()
            """, {
                'ticker': symbol, 'heat': round(heat, 4),
                'ps': round(price_sig, 4), 'vs': round(volume_sig, 4),
                'rs': round(relation_sig, 4), 'ns': round(news_sig, 4),
            })
            processed += 1
        except Exception as e:
            logger.error(f'heat_score failed {symbol}: {e}')
            errors += 1

    elapsed = (timezone.now() - start_time).total_seconds()
    logger.info(f'heat_score batch: {processed} ok, {errors} err, {elapsed:.1f}s')
    return {'processed': processed, 'errors': errors, 'elapsed_s': round(elapsed, 1)}


@shared_task(name='chainsight-seed-snapshot-cleanup', max_retries=1)
def cleanup_seed_snapshots(retain_days: int = 30) -> dict:
    """SeedSnapshot 행이 무한 누적되는 것을 방지. 기본 30일 이전 스냅샷 삭제."""
    from chainsight.models import SeedSnapshot

    cutoff = timezone.localdate() - timedelta(days=retain_days)
    deleted, _ = SeedSnapshot.objects.filter(market_date__lt=cutoff).delete()
    logger.info(f'SeedSnapshot cleanup: deleted {deleted} rows older than {cutoff}')
    return {'deleted': deleted, 'cutoff': str(cutoff)}


def _compute_price_signals_batch(price_df, symbols):
    """5일 수익률 절댓값 → percentile rank."""
    if price_df.empty:
        return {s: 0.0 for s in symbols}
    returns = {}
    for sym, group in price_df.groupby('symbol'):
        if len(group) < 6:
            continue
        latest = float(group['close'].iloc[-1])
        past = float(group['close'].iloc[-6])
        if past > 0:
            returns[sym] = abs((latest - past) / past)
    if not returns:
        return {s: 0.0 for s in symbols}
    series = pd.Series(returns)
    ranks = series.rank(pct=True)
    return {s: float(ranks.get(s, 0.0)) for s in symbols}


def _compute_volume_signal(symbol, price_df):
    """당일 거래량 / 20일 평균 → min(ratio/3, 1)."""
    df = price_df[price_df['symbol'] == symbol].tail(20)
    if len(df) < 20:
        return 0.0
    today_vol = float(df['volume'].iloc[-1])
    avg_vol = float(df['volume'].mean())
    if avg_vol == 0:
        return 0.0
    return min(today_vol / avg_vol / 3.0, 1.0)


def _compute_relation_change_signal(symbol):
    """최근 7일 내 관련 RelationConfidence 갱신 수 → min(count/5, 1)."""
    cutoff = timezone.now() - timedelta(days=7)
    count = RelationConfidence.objects.filter(
        Q(symbol_a=symbol) | Q(symbol_b=symbol),
        last_observed_at__gte=cutoff,
    ).count()
    return min(count / 5.0, 1.0)


def _compute_news_activation(symbol):
    """최근 3일 내 CoMention 수 → min(count/3, 1)."""
    cutoff = (timezone.now() - timedelta(days=3)).date()
    count = CoMentionEdge.objects.filter(
        Q(symbol_a=symbol) | Q(symbol_b=symbol),
        last_co_mention_date__gte=cutoff,
    ).count()
    return min(count / 3.0, 1.0)
