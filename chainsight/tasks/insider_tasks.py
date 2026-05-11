"""
CS-2-1c: InsiderSignal 계산

Finnhub Insider Transactions API 기반.
⚠️ Finnhub 무료 60 RPM → 1.2초 딜레이 필수.
"""

import logging
import time
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings

from stocks.models import Stock, SP500Constituent
from chainsight.models import CompanyInsiderSignal

logger = logging.getLogger(__name__)

FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'

# 자발적 매수/매도만 집계 (스톡옵션 행사, 세금, 선물 제외)
BUY_CODES = {'P'}       # P = Open market Purchase
SELL_CODES = {'S'}      # S = Open market Sale
EXCLUDED_CODES = {'M', 'F', 'G', 'A', 'J', 'C', 'W', 'X'}


def _fetch_insider_transactions(symbol: str) -> list:
    """Finnhub Insider Transactions API 호출."""
    api_key = settings.FINNHUB_API_KEY
    if not api_key:
        return []

    time.sleep(1.2)  # 60 RPM rate limit

    try:
        resp = requests.get(
            f"{FINNHUB_BASE_URL}/stock/insider-transactions",
            params={'symbol': symbol, 'token': api_key},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.debug(f"Finnhub insider {symbol}: {resp.status_code}")
            return []

        data = resp.json()
        return data.get('data', [])

    except Exception as e:
        logger.debug(f"Finnhub insider {symbol}: {e}")
        return []


def _classify_insider_signal(buy_count: int, sell_count: int) -> str:
    """buy/sell ratio 기반 insider_signal 분류."""
    total = buy_count + sell_count
    if total < 3:
        return 'neutral'  # 통계적 의미 없음

    ratio = buy_count / total

    if ratio >= 0.80:
        return 'strong_buy'
    elif ratio >= 0.60:
        return 'buy'
    elif ratio >= 0.40:
        return 'neutral'
    elif ratio >= 0.20:
        return 'sell'
    return 'strong_sell'


def _classify_smart_money(insider_signal: str, institutional_pct: float,
                          short_interest_pct: float) -> str:
    """종합 smart money signal."""
    score = 0

    if insider_signal in ('strong_buy', 'buy'):
        score += 1
    elif insider_signal in ('strong_sell', 'sell'):
        score -= 1

    if institutional_pct and institutional_pct > 70:
        score += 1

    if short_interest_pct is not None:
        if short_interest_pct < 3:
            score += 1
        elif short_interest_pct > 10:
            score -= 1

    if score >= 2:
        return 'bullish'
    elif score <= -1:
        return 'bearish'
    return 'neutral'


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_insider_signals(self):
    """S&P 500 전체 InsiderSignal 계산."""
    sp500 = list(SP500Constituent.objects.filter(is_active=True).values_list('symbol', flat=True))
    success, fail, skip = 0, 0, 0

    cutoff = datetime.now() - timedelta(days=90)

    for symbol in sp500:
        try:
            stock = Stock.objects.filter(symbol=symbol).first()
            if not stock:
                continue

            transactions = _fetch_insider_transactions(symbol)
            if not transactions:
                # API 데이터 없어도 기본값으로 저장
                CompanyInsiderSignal.objects.update_or_create(
                    symbol=stock,
                    defaults={
                        'insider_signal': 'neutral',
                        'smart_money_signal': 'neutral',
                        'data_freshness': datetime.now().date(),
                    }
                )
                skip += 1
                continue

            # 90일 내 거래만 필터
            buy_count = 0
            sell_count = 0
            net_amount = 0

            for tx in transactions:
                tx_date_str = tx.get('transactionDate', '')
                if not tx_date_str:
                    continue

                try:
                    tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d')
                except ValueError:
                    continue

                if tx_date < cutoff:
                    continue

                code = tx.get('transactionCode', '')
                change = tx.get('change', 0) or 0
                price = tx.get('transactionPrice', 0) or 0

                if code in BUY_CODES:
                    buy_count += 1
                    net_amount += abs(change) * price
                elif code in SELL_CODES:
                    sell_count += 1
                    net_amount -= abs(change) * price

            insider_signal = _classify_insider_signal(buy_count, sell_count)

            # institutional_ownership, short_interest는 현재 별도 API 없음 → None
            smart_money = _classify_smart_money(insider_signal, None, None)

            CompanyInsiderSignal.objects.update_or_create(
                symbol=stock,
                defaults={
                    'insider_buy_count_90d': buy_count,
                    'insider_sell_count_90d': sell_count,
                    'insider_net_amount_90d': int(net_amount) if net_amount else None,
                    'insider_signal': insider_signal,
                    'smart_money_signal': smart_money,
                    'data_freshness': datetime.now().date(),
                },
            )
            success += 1

        except Exception as e:
            fail += 1
            logger.error(f"InsiderSignal {symbol}: {e}")

    logger.info(f"InsiderSignal 완료: {success} 성공, {fail} 실패, {skip} skip")
    return {"success": success, "fail": fail, "skip": skip}
