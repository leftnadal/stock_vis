"""
Chain Sight 시드 선정 서비스 — Phase 1

매일 시장 시그널 + 관계 변화를 분석하여 최대 20개 시드 노드를 선정한다.
결과는 Redis에 캐싱되어 seeds/ API가 읽는다.
"""

import json
import logging
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Avg, StdDev, F, Subquery, OuterRef, DecimalField
from django.db.models.functions import Cast

from stocks.models import Stock, DailyPrice
from chainsight.models import RelationConfidence, CoMentionEdge

logger = logging.getLogger(__name__)

MAX_SEED_NODES = 20

SEED_REASONS = [
    'price_top5', 'price_bottom5', 'volume_surge',
    'sector_outlier', 'relation_upgrade', 'relation_downgrade',
    'relation_new', 'comention_surge',
]

SEED_TYPE_PRIORITY = {'price': 0, 'volume': 1, 'relation': 2, 'comention': 3}


def resolve_seed_type(reasons: list[str]) -> str:
    """reasons 목록에서 대표 seed_type 결정 (우선순위: price > volume > relation > comention)."""
    types = set()
    for r in reasons:
        if r.startswith('price'):
            types.add('price')
        elif r == 'volume_surge':
            types.add('volume')
        elif r.startswith('relation') or r == 'relation_new':
            types.add('relation')
        elif r == 'comention_surge':
            types.add('comention')
    return min(types, key=lambda t: SEED_TYPE_PRIORITY[t]) if types else 'price'


# ── 1. 시장 시그널 ──

def _get_latest_prices(market_date: date):
    """market_date의 DailyPrice + 전일 종가를 조회하여 수익률/거래량비 계산에 사용."""
    # 최근 거래일 2일치 — market_date 이하 최신
    latest_dates = (
        DailyPrice.objects
        .filter(date__lte=market_date)
        .values('date')
        .distinct()
        .order_by('-date')[:2]
    )
    dates_list = [d['date'] for d in latest_dates]
    if not dates_list:
        return {}, date.min
    latest_date = dates_list[0]
    prev_date = dates_list[1] if len(dates_list) > 1 else None
    return {
        'latest_date': latest_date,
        'prev_date': prev_date,
    }, latest_date


def get_price_seeds(market_date: date) -> dict:
    """수익률 상위/하위 2σ 이상치."""
    date_info, latest_date = _get_latest_prices(market_date)
    if not date_info:
        return {}

    prev_date = date_info.get('prev_date')
    if not prev_date:
        return {}

    # 전일 종가 서브쿼리
    prev_close_sq = Subquery(
        DailyPrice.objects.filter(
            stock=OuterRef('stock'), date=prev_date
        ).values('close_price')[:1],
        output_field=DecimalField(),
    )

    # 수익률 계산: (today_close - prev_close) / prev_close * 100
    qs = (
        DailyPrice.objects
        .filter(date=latest_date)
        .annotate(prev_close=prev_close_sq)
        .exclude(prev_close__isnull=True)
        .exclude(prev_close=0)
        .annotate(
            daily_return=Cast(
                (F('close_price') - F('prev_close')) * 100.0 / F('prev_close'),
                output_field=DecimalField(max_digits=10, decimal_places=4),
            )
        )
    )

    stats = qs.aggregate(avg=Avg('daily_return'), stddev=StdDev('daily_return'))
    avg_ret = float(stats['avg'] or 0)
    std_ret = float(stats['stddev'] or 1)

    if std_ret == 0:
        return {}

    upper = avg_ret + 2 * std_ret
    lower = avg_ret - 2 * std_ret

    top = qs.filter(daily_return__gte=upper).order_by('-daily_return')[:5]
    bottom = qs.filter(daily_return__lte=lower).order_by('daily_return')[:5]

    seeds = {}
    for dp in top:
        seeds[dp.stock_id] = {
            'reasons': ['price_top5'],
            'seed_type': 'price',
            'daily_return': round(float(dp.daily_return), 2),
        }
    for dp in bottom:
        seeds[dp.stock_id] = {
            'reasons': ['price_bottom5'],
            'seed_type': 'price',
            'daily_return': round(float(dp.daily_return), 2),
        }
    return seeds


def get_volume_seeds(market_date: date) -> dict:
    """거래량 / SMA20 >= 2.0."""
    date_info, latest_date = _get_latest_prices(market_date)
    if not date_info:
        return {}

    # SMA20 서브쿼리: 최근 20거래일 평균 거래량
    sma20_sq = Subquery(
        DailyPrice.objects.filter(
            stock=OuterRef('stock'),
            date__lte=market_date,
        ).order_by('-date').values('stock')[:20]
        .values('stock')
        .annotate(avg_vol=Avg('volume'))
        .values('avg_vol')[:1],
    )

    # 직접 계산: 최근 20일 평균 거래량을 symbol별로 구한 후 비교
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            WITH latest AS (
                SELECT stock_id, volume
                FROM stocks_daily_price
                WHERE date = (
                    SELECT MAX(date) FROM stocks_daily_price WHERE date <= %s
                )
            ),
            sma20 AS (
                SELECT dp.stock_id, AVG(dp.volume) as avg_vol
                FROM stocks_daily_price dp
                INNER JOIN (
                    SELECT stock_id, date
                    FROM stocks_daily_price
                    WHERE date <= %s
                    ORDER BY date DESC
                ) ranked ON dp.stock_id = ranked.stock_id AND dp.date = ranked.date
                GROUP BY dp.stock_id
                HAVING COUNT(*) >= 10
            )
            SELECT l.stock_id, l.volume, s.avg_vol,
                   CASE WHEN s.avg_vol > 0 THEN l.volume::float / s.avg_vol ELSE 0 END as vol_ratio
            FROM latest l
            JOIN sma20 s ON l.stock_id = s.stock_id
            WHERE s.avg_vol > 0 AND l.volume::float / s.avg_vol >= 2.0
            ORDER BY vol_ratio DESC
            LIMIT 10
        """, [market_date, market_date])
        rows = cursor.fetchall()

    seeds = {}
    for stock_id, volume, avg_vol, vol_ratio in rows:
        seeds[stock_id] = {
            'reasons': ['volume_surge'],
            'seed_type': 'volume',
            'volume_ratio': round(vol_ratio, 2),
        }
    return seeds


def get_sector_outlier_seeds(market_date: date) -> dict:
    """섹터 평균 대비 ±2σ 이상치."""
    date_info, latest_date = _get_latest_prices(market_date)
    if not date_info:
        return {}

    prev_date = date_info.get('prev_date')
    if not prev_date:
        return {}

    # Stock 테이블에서 change_percent를 사용 (이미 실시간 업데이트됨)
    stocks_with_return = (
        Stock.objects
        .exclude(change_percent__isnull=True)
        .exclude(change_percent='')
        .exclude(sector__isnull=True)
        .exclude(sector='')
    )

    # 섹터별 통계 계산
    sector_data = {}
    for stock in stocks_with_return:
        try:
            ret = float(stock.change_percent.rstrip('%'))
        except (ValueError, AttributeError):
            continue
        sector = stock.sector
        if sector not in sector_data:
            sector_data[sector] = []
        sector_data[sector].append((stock.symbol, ret))

    seeds = {}
    for sector, entries in sector_data.items():
        if len(entries) < 5:
            continue
        returns = [r for _, r in entries]
        avg_ret = sum(returns) / len(returns)
        variance = sum((r - avg_ret) ** 2 for r in returns) / len(returns)
        std_ret = variance ** 0.5
        if std_ret == 0:
            continue

        upper = avg_ret + 2 * std_ret
        lower = avg_ret - 2 * std_ret

        for symbol, ret in entries:
            if ret >= upper or ret <= lower:
                if symbol not in seeds:
                    seeds[symbol] = {
                        'reasons': ['sector_outlier'],
                        'seed_type': 'price',
                        'daily_return': round(ret, 2),
                    }
                elif 'sector_outlier' not in seeds[symbol]['reasons']:
                    seeds[symbol]['reasons'].append('sector_outlier')
    return seeds


# ── 2. 관계 변화 ──

def get_relation_change_seeds(market_date: date) -> dict:
    """RelationConfidence 상태 전이 (previous_status ≠ relation_status)."""
    yesterday = market_date - timedelta(days=1)
    changed = (
        RelationConfidence.objects
        .filter(last_observed_at__gte=yesterday)
        .exclude(previous_status='')
        .exclude(previous_status=F('relation_status'))
    )

    status_order = ['hidden', 'weak', 'probable', 'confirmed']

    seeds = {}
    for rc in changed:
        old_idx = status_order.index(rc.previous_status) if rc.previous_status in status_order else -1
        new_idx = status_order.index(rc.relation_status) if rc.relation_status in status_order else -1
        reason = 'relation_upgrade' if new_idx > old_idx else 'relation_downgrade'

        for symbol in [rc.symbol_a, rc.symbol_b]:
            if symbol not in seeds:
                seeds[symbol] = {'reasons': [], 'seed_type': 'relation'}
            if reason not in seeds[symbol]['reasons']:
                seeds[symbol]['reasons'].append(reason)
    return seeds


def get_comention_surge_seeds(market_date: date) -> dict:
    """CoMention 최근 급증: co_mention_count >= 5 && last_co_mention_date가 최근 7일 이내."""
    week_ago = market_date - timedelta(days=7)

    # 최근 7일 내 동시출현이 있고 카운트가 높은 페어
    surges = (
        CoMentionEdge.objects
        .filter(last_co_mention_date__gte=week_ago, co_mention_count__gte=5)
        .order_by('-co_mention_count')[:20]
    )

    seeds = {}
    for edge in surges:
        for symbol in [edge.symbol_a, edge.symbol_b]:
            if symbol not in seeds:
                seeds[symbol] = {'reasons': ['comention_surge'], 'seed_type': 'comention'}
            elif 'comention_surge' not in seeds[symbol]['reasons']:
                seeds[symbol]['reasons'].append('comention_surge')
    return seeds


# ── 3. 합산 및 랭킹 ──

def select_seeds(market_date: date) -> dict:
    """전체 시드 소스 합산 → 상위 MAX_SEED_NODES 선정."""
    all_sources = [
        get_price_seeds(market_date),
        get_volume_seeds(market_date),
        get_sector_outlier_seeds(market_date),
        get_relation_change_seeds(market_date),
        get_comention_surge_seeds(market_date),
    ]

    merged = {}
    for source in all_sources:
        for symbol, info in source.items():
            if symbol not in merged:
                merged[symbol] = {
                    'reasons': [],
                    'seed_type': info['seed_type'],
                    'daily_return': info.get('daily_return', 0.0),
                    'volume_ratio': info.get('volume_ratio', 0.0),
                }
            merged[symbol]['reasons'].extend(info['reasons'])
            # daily_return / volume_ratio 업데이트 (0이 아닌 값 우선)
            if info.get('daily_return') and not merged[symbol].get('daily_return'):
                merged[symbol]['daily_return'] = info['daily_return']
            if info.get('volume_ratio') and not merged[symbol].get('volume_ratio'):
                merged[symbol]['volume_ratio'] = info['volume_ratio']

    # 중복 제거 + signal_count + seed_type 우선순위 결정
    for symbol, info in merged.items():
        info['reasons'] = list(set(info['reasons']))
        info['signal_count'] = len(info['reasons'])
        info['seed_type'] = resolve_seed_type(info['reasons'])

    # signal_count DESC 정렬 → 상위 MAX_SEED_NODES
    ranked = sorted(merged.items(), key=lambda x: x[1]['signal_count'], reverse=True)
    return dict(ranked[:MAX_SEED_NODES])


# ── 4. 섹터 요약 ──

def build_sector_summary(seeds: dict, market_date: date) -> list[dict]:
    """seeds dict → sector_summary 리스트."""
    # bulk query (N+1 방지)
    stock_map = {
        s.symbol: s
        for s in Stock.objects.filter(symbol__in=seeds.keys())
    }

    sector_map = {}
    for symbol, info in seeds.items():
        stock = stock_map.get(symbol)
        if not stock or not stock.sector:
            continue
        sector = stock.sector
        if sector not in sector_map:
            sector_map[sector] = {
                'sector': sector,
                'sector_display': sector,
                'pct_change': 0.0,
                'seed_count': 0,
                'heat_total': 0.0,
                'top_seed': None,
            }
        sector_map[sector]['seed_count'] += 1
        # top_seed: signal_count 최대인 종목
        current_top = sector_map[sector]['top_seed']
        if (current_top is None or
                info['signal_count'] > seeds.get(current_top, {}).get('signal_count', 0)):
            sector_map[sector]['top_seed'] = symbol

    # 섹터 평균 수익률 계산 (Stock.change_percent 기반)
    for sector, summary in sector_map.items():
        sector_stocks = Stock.objects.filter(
            sector=sector
        ).exclude(change_percent__isnull=True).exclude(change_percent='')

        total, count = 0.0, 0
        for s in sector_stocks:
            try:
                total += float(s.change_percent.rstrip('%'))
                count += 1
            except (ValueError, AttributeError):
                continue
        summary['pct_change'] = round(total / count, 2) if count else 0.0

    # Phase 1 정렬: seed_count DESC
    return sorted(sector_map.values(), key=lambda x: x['seed_count'], reverse=True)


# ── 5. 영속 저장 + Redis 캐싱 ──

# Redis TTL을 48h로 두어 Beat 지연/Redis 장애에 여유를 준다(2026-04-24 사건 기반).
SEED_CACHE_TTL = 60 * 60 * 48


def cache_seed_result(market_date: date, sector_summary: list, seeds_list: list):
    """시드 결과를 DB(SeedSnapshot)에 영속화하고 Redis에도 캐싱한다.

    Redis 휘발 시(테스트 flush, 재시작, maxmemory eviction) DB에서 복구 가능.
    Redis write 실패는 경고로만 남기고 DB write는 반드시 성공시킨다.
    """
    from chainsight.models import SeedSnapshot  # 순환 import 회피

    payload = {
        'date': str(market_date),
        'total_seeds': len(seeds_list),
        'sector_summary': sector_summary,
        'seeds': seeds_list,
    }

    SeedSnapshot.objects.update_or_create(
        market_date=market_date,
        defaults={
            'payload': payload,
            'total_seeds': len(seeds_list),
            'sector_count': len(sector_summary),
        },
    )

    try:
        cache_key = f'chainsight:seeds:{market_date}'
        cache.set(cache_key, json.dumps(payload), timeout=SEED_CACHE_TTL)
    except Exception as e:
        logger.warning(f'seed cache write failed (DB persisted): {e}')
