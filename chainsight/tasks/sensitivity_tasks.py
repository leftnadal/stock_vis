"""
CS-2-1b: SensitivityProfile 계산

FMP Revenue Geographic Segmentation + BalanceSheet + Stock.beta 기반.
"""

import logging
import time
from decimal import Decimal

import requests
from celery import shared_task
from django.conf import settings

from stocks.models import Stock, SP500Constituent, BalanceSheet, IncomeStatement
from chainsight.models import CompanySensitivityProfile

logger = logging.getLogger(__name__)

FMP_BASE_URL = 'https://financialmodelingprep.com'

# 규제 민감도 매핑 (sector/industry → regulation_type)
REGULATION_MAP = {
    # sector 기반
    'healthcare': 'fda',
    'biotechnology': 'fda',
    'pharmaceuticals': 'fda',
    'financial services': 'financial',
    'financial': 'financial',
    'utilities': 'environmental',
    'energy': 'environmental',
    'communication services': 'telecom',
    'telecommunications': 'telecom',
    # industry 기반 (더 구체적)
    'banks': 'financial',
    'insurance': 'financial',
    'capital markets': 'financial',
    'oil & gas': 'environmental',
    'electric utilities': 'environmental',
    'drug manufacturers': 'fda',
    'medical devices': 'fda',
    'health care providers': 'fda',
}


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _clamp_decimal(val, max_digits=10, decimal_places=4):
    """Decimal overflow 방지."""
    if val is None:
        return None
    max_abs = 10 ** (max_digits - decimal_places) - 1
    val = round(val, decimal_places)
    if abs(val) > max_abs:
        val = max_abs if val > 0 else -max_abs
    return Decimal(str(val))


def _fetch_geo_revenue(symbol: str) -> dict:
    """FMP Revenue Geographic Segmentation API 호출."""
    api_key = settings.FMP_API_KEY
    if not api_key:
        return {}

    url = f"{FMP_BASE_URL}/stable/revenue-geographic-segmentation"
    try:
        time.sleep(0.25)  # FMP rate limit
        resp = requests.get(url, params={
            'symbol': symbol, 'apikey': api_key,
        }, timeout=15)

        if resp.status_code != 200:
            return {}

        data = resp.json()
        if not data:
            return {}

        # 최신 연도 데이터
        latest = data[0]
        segments = latest.get('data', {})
        return segments

    except Exception as e:
        logger.debug(f"Geo revenue fetch failed for {symbol}: {e}")
        return {}


def _calculate_foreign_revenue_pct(segments: dict) -> float:
    """지역별 매출에서 해외(US 외) 비중 계산."""
    if not segments:
        return None

    total = sum(v for v in segments.values() if isinstance(v, (int, float)) and v > 0)
    if total == 0:
        return None

    # US/Americas 매출 찾기
    us_revenue = 0
    for key, val in segments.items():
        key_lower = key.lower()
        if any(term in key_lower for term in [
            'united states', 'u.s.', 'us ', 'domestic',
            'americas', 'north america',
        ]):
            us_revenue += val if isinstance(val, (int, float)) else 0

    foreign_pct = (total - us_revenue) / total * 100
    return round(foreign_pct, 2)


def _determine_primary_currency(segments: dict) -> str:
    """최대 해외 지역 기반 통화 추론."""
    if not segments:
        return ''

    # Americas 제외하고 가장 큰 지역
    non_us = {}
    for key, val in segments.items():
        key_lower = key.lower()
        if not any(term in key_lower for term in ['americas', 'united states', 'domestic']):
            if isinstance(val, (int, float)):
                non_us[key] = val

    if not non_us:
        return 'USD'

    largest = max(non_us, key=non_us.get)
    largest_lower = largest.lower()

    if 'europe' in largest_lower:
        return 'EUR'
    elif 'china' in largest_lower or 'greater china' in largest_lower:
        return 'CNY'
    elif 'japan' in largest_lower:
        return 'JPY'
    elif 'asia' in largest_lower:
        return 'JPY'  # 아시아 대표
    elif 'uk' in largest_lower or 'britain' in largest_lower:
        return 'GBP'

    return ''


def _classify_rate_sensitivity(debt_to_equity: float, interest_coverage: float) -> str:
    """금리 민감도 분류."""
    if debt_to_equity is None:
        return ''

    if debt_to_equity > 2.0 and (interest_coverage is not None and interest_coverage < 3.0):
        return 'high'
    if debt_to_equity > 1.0 or (interest_coverage is not None and interest_coverage < 5.0):
        return 'medium'
    return 'low'


def _classify_forex_sensitivity(foreign_pct: float) -> str:
    """환율 민감도 분류."""
    if foreign_pct is None:
        return ''
    if foreign_pct > 50:
        return 'high'
    if foreign_pct > 25:
        return 'medium'
    return 'low'


def _classify_debt_maturity_risk(debt_to_equity: float, interest_coverage: float) -> str:
    """부채 만기 리스크 분류."""
    if debt_to_equity is None:
        return ''
    if debt_to_equity > 3.0:
        return 'high'
    if debt_to_equity > 1.5:
        return 'medium'
    return 'low'


def _get_regulation(sector: str, industry: str) -> tuple:
    """sector/industry 기반 규제 타입 결정."""
    sector_lower = (sector or '').lower()
    industry_lower = (industry or '').lower()

    # industry 우선 (더 구체적)
    for key, reg_type in REGULATION_MAP.items():
        if key in industry_lower:
            return True, reg_type

    for key, reg_type in REGULATION_MAP.items():
        if key in sector_lower:
            return True, reg_type

    return False, 'none'


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_sensitivity_profiles(self):
    """S&P 500 전체 SensitivityProfile 계산."""
    sp500 = set(SP500Constituent.objects.filter(is_active=True).values_list('symbol', flat=True))
    success, fail = 0, 0

    # sector 평균 beta (sector_adj 계산용)
    sector_betas = {}
    for stock in Stock.objects.filter(symbol__in=sp500):
        sector = stock.sector or ''
        beta = _safe_float(stock.beta)
        if beta and sector:
            sector_betas.setdefault(sector, []).append(beta)
    sector_avg_beta = {s: sum(bs) / len(bs) for s, bs in sector_betas.items() if bs}

    for symbol in sp500:
        try:
            stock = Stock.objects.filter(symbol=symbol).first()
            if not stock:
                continue

            # ── BalanceSheet 데이터 ──
            bs = BalanceSheet.objects.filter(
                stock=stock, period_type='annual'
            ).order_by('-fiscal_year').first()

            equity = _safe_float(bs.total_shareholder_equity) if bs else None
            long_debt = _safe_float(bs.long_term_debt) if bs else 0
            short_debt = _safe_float(bs.short_term_debt) if bs else 0
            cash = _safe_float(bs.cash_and_cash_equivalents_at_carrying_value) if bs else 0

            total_debt = (long_debt or 0) + (short_debt or 0)
            net_debt = total_debt - (cash or 0)

            debt_to_equity = total_debt / abs(equity) if equity and equity != 0 else None

            # ── IncomeStatement - interest coverage ──
            inc = IncomeStatement.objects.filter(
                stock=stock, period_type='annual'
            ).order_by('-fiscal_year').first()

            ebit = _safe_float(inc.ebit) if inc else None
            interest_exp = _safe_float(inc.interest_expense) if inc else None

            interest_coverage = None
            if ebit and interest_exp and interest_exp > 0:
                interest_coverage = ebit / interest_exp

            # ── FMP Revenue Geo Segmentation ──
            geo_segments = _fetch_geo_revenue(symbol)
            foreign_pct = _calculate_foreign_revenue_pct(geo_segments)
            primary_currency = _determine_primary_currency(geo_segments)

            # ── Beta ──
            beta = _safe_float(stock.beta)
            sector = stock.sector or ''
            avg_beta = sector_avg_beta.get(sector)
            beta_adj = beta - avg_beta if beta and avg_beta else None

            # ── 규제 ──
            is_regulated, reg_type = _get_regulation(sector, stock.industry or '')

            # ── 분류 ──
            rate_sens = _classify_rate_sensitivity(debt_to_equity, interest_coverage)
            forex_sens = _classify_forex_sensitivity(foreign_pct)
            maturity_risk = _classify_debt_maturity_risk(debt_to_equity, interest_coverage)

            # ── 저장 ──
            data_source = {}
            if geo_segments:
                data_source['geo_segments'] = True
            if bs:
                data_source['balance_sheet'] = bs.fiscal_year

            CompanySensitivityProfile.objects.update_or_create(
                symbol=stock,
                defaults={
                    'debt_to_equity': _clamp_decimal(debt_to_equity),
                    'net_debt': int(max(min(net_debt, 9_999_999_999_999), -9_999_999_999_999)) if net_debt else None,
                    'interest_coverage': _clamp_decimal(interest_coverage),
                    'debt_maturity_risk': maturity_risk,
                    'rate_sensitivity': rate_sens,
                    'foreign_revenue_pct': _clamp_decimal(foreign_pct, 5, 2) if foreign_pct is not None else None,
                    'primary_currency_exposure': primary_currency[:10],
                    'forex_sensitivity': forex_sens,
                    'beta': _clamp_decimal(beta, 6, 4) if beta else None,
                    'beta_sector_adj': _clamp_decimal(beta_adj, 6, 4) if beta_adj else None,
                    'commodity_sensitivity': '',  # Tier B에서 채움
                    'sector': sector[:100],
                    'industry': (stock.industry or '')[:100],
                    'is_regulated_industry': is_regulated,
                    'regulation_type': reg_type,
                    'data_source': data_source,
                },
            )
            success += 1
        except Exception as e:
            fail += 1
            logger.error(f"SensitivityProfile {symbol}: {e}")

    logger.info(f"SensitivityProfile 완료: {success} 성공, {fail} 실패")
    return {"success": success, "fail": fail}
