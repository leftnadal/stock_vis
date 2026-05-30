"""
CS-2-1: Tier A 프로파일 계산 — GrowthStage + CapitalDNA (+ SensitivityProfile, InsiderSignal)
"""

import logging
from decimal import Decimal

from celery import shared_task

from chainsight.models import CompanyCapitalDNA, CompanyGrowthStage
from packages.shared.stocks.models import (
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
    SP500Constituent,
    Stock,
)

logger = logging.getLogger(__name__)


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _clamp_decimal(val, max_abs=9999.0):
    """Decimal(8,4) overflow 방지. 범위 초과 시 클램핑."""
    if val is None:
        return None
    val = round(val, 4)
    if abs(val) > max_abs:
        val = max_abs if val > 0 else -max_abs
    return Decimal(str(val))


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_growth_stages(self):
    """S&P 500 전체 GrowthStage 계산."""
    sp500 = set(SP500Constituent.objects.filter(is_active=True).values_list('symbol', flat=True))
    success, fail = 0, 0

    for symbol in sp500:
        try:
            stock = Stock.objects.filter(symbol=symbol).first()
            if not stock:
                continue

            # 최근 3년 Income Statement
            incomes = list(
                IncomeStatement.objects.filter(stock=stock, period_type='annual')
                .order_by('-fiscal_year')[:3]
            )
            if len(incomes) < 2:
                continue

            revenue_latest = _safe_float(incomes[0].total_revenue)
            revenue_prev = _safe_float(incomes[1].total_revenue)
            revenue_2y = _safe_float(incomes[2].total_revenue) if len(incomes) >= 3 else None

            if not revenue_latest or not revenue_prev:
                continue

            growth = (revenue_latest - revenue_prev) / abs(revenue_prev) if revenue_prev else 0
            ni_latest = _safe_float(incomes[0].net_income)

            # 3년 CAGR
            cagr_3y = None
            if revenue_2y and revenue_2y > 0 and revenue_latest > 0:
                cagr_3y = (revenue_latest / revenue_2y) ** (1 / 2) - 1

            # Stage 분류
            if revenue_latest < 500_000_000 and growth > 0.30:
                stage = 'early_growth'
            elif growth > 0.15:
                stage = 'accelerating'
            elif growth >= 0:
                # 배당 여부로 mature vs cash_cow 구분
                cf = CashFlowStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first()
                has_dividend = cf and _safe_float(cf.dividend_payout) and abs(_safe_float(cf.dividend_payout)) > 0
                stage = 'cash_cow' if has_dividend and growth < 0.05 else 'mature'
            elif growth < -0.05:
                # 2년 연속 감소 → declining
                if revenue_2y and revenue_prev < revenue_2y:
                    stage = 'declining'
                else:
                    stage = 'turnaround'
            else:
                stage = 'mature'

            # FCF 추세
            cfs = list(
                CashFlowStatement.objects.filter(stock=stock, period_type='annual')
                .order_by('-fiscal_year')[:3]
            )
            fcf_trend = ''
            if len(cfs) >= 2:
                fcf_0 = (_safe_float(cfs[0].operating_cashflow) or 0) - abs(_safe_float(cfs[0].capital_expenditures) or 0)
                fcf_1 = (_safe_float(cfs[1].operating_cashflow) or 0) - abs(_safe_float(cfs[1].capital_expenditures) or 0)
                if fcf_0 > fcf_1 * 1.05:
                    fcf_trend = 'growing'
                elif fcf_0 < fcf_1 * 0.95:
                    fcf_trend = 'declining'
                else:
                    fcf_trend = 'stable'

            confidence = 'high' if len(incomes) >= 3 else 'medium'

            CompanyGrowthStage.objects.update_or_create(
                symbol=stock,
                defaults={
                    'stage': stage,
                    'revenue_cagr_3y': Decimal(str(round(cagr_3y, 4))) if cagr_3y else None,
                    'net_income_positive_years': sum(1 for i in incomes if _safe_float(i.net_income) and _safe_float(i.net_income) > 0),
                    'net_income_turned_positive': ni_latest and ni_latest > 0 and len(incomes) >= 2 and (_safe_float(incomes[1].net_income) or 0) <= 0,
                    'fcf_trend': fcf_trend,
                    'fcf_positive_years': sum(1 for c in cfs if (_safe_float(c.operating_cashflow) or 0) - abs(_safe_float(c.capital_expenditures) or 0) > 0),
                    'dividend_started': bool(cfs and _safe_float(cfs[0].dividend_payout) and abs(_safe_float(cfs[0].dividend_payout)) > 0),
                    'confidence': confidence,
                }
            )
            success += 1
        except Exception as e:
            fail += 1
            logger.error(f"GrowthStage {symbol}: {e}")

    logger.info(f"GrowthStage 완료: {success} 성공, {fail} 실패")
    return {"success": success, "fail": fail}


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_capital_dna(self):
    """S&P 500 전체 CapitalDNA 계산."""
    sp500 = set(SP500Constituent.objects.filter(is_active=True).values_list('symbol', flat=True))
    success, fail = 0, 0

    for symbol in sp500:
        try:
            stock = Stock.objects.filter(symbol=symbol).first()
            if not stock:
                continue

            cf = CashFlowStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first()
            inc = IncomeStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first()
            bal = BalanceSheet.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year').first()
            if not cf or not inc:
                continue

            revenue = _safe_float(inc.total_revenue) or 1
            ocf = _safe_float(cf.operating_cashflow) or 0
            capex = abs(_safe_float(cf.capital_expenditures) or 0)
            fcf = ocf - capex
            buyback = abs(_safe_float(cf.payments_for_repurchase_of_common_stock) or 0)
            dividend = abs(_safe_float(cf.dividend_payout) or 0)
            mcap = _safe_float(stock.market_capitalization) or 1

            # R&D
            rd = _safe_float(inc.research_and_development) or 0

            # Cash position
            cash = _safe_float(bal.cash_and_cash_equivalents_at_carrying_value) or 0 if bal else 0
            short_debt = _safe_float(bal.short_term_debt) or 0 if bal else 0
            long_debt = _safe_float(bal.long_term_debt) or 0 if bal else 0
            net_cash = cash - short_debt - long_debt

            # Capital type
            rd_ratio = rd / revenue if revenue else 0
            capex_ratio = capex / revenue if revenue else 0
            buyback_yield = buyback / mcap
            dividend_ratio = dividend / fcf if fcf > 0 else 0

            if rd_ratio > 0.15 or capex_ratio > 0.15:
                capital_type = 'heavy_investor'
            elif buyback_yield > 0.03 or dividend_ratio > 0.5:
                capital_type = 'shareholder_first'
            elif net_cash / mcap > 0.15:
                capital_type = 'cash_hoarder'
            elif rd_ratio > 0.08 and capex_ratio > 0.08:
                capital_type = 'aggressive_growth'
            else:
                capital_type = 'balanced'

            CompanyCapitalDNA.objects.update_or_create(
                symbol=stock,
                defaults={
                    'rd_to_revenue': _clamp_decimal(rd_ratio),
                    'capex_to_revenue': _clamp_decimal(capex_ratio),
                    'dividend_payout': _clamp_decimal(dividend_ratio),
                    'buyback_yield': _clamp_decimal(buyback_yield),
                    'total_shareholder_return_pct': _clamp_decimal((dividend + buyback) / mcap),
                    'net_cash_position': int(max(min(net_cash, 9_999_999_999_999), -9_999_999_999_999)),
                    'cash_to_market_cap': _clamp_decimal(cash / mcap),
                    'capital_type': capital_type,
                }
            )
            success += 1
        except Exception as e:
            fail += 1
            logger.error(f"CapitalDNA {symbol}: {e}")

    logger.info(f"CapitalDNA 완료: {success} 성공, {fail} 실패")
    return {"success": success, "fail": fail}


@shared_task(bind=True, max_retries=1, soft_time_limit=7200, time_limit=7260)
def calculate_all_profiles(self):
    """Tier A 통합 task. Celery Beat 주 1회."""
    from .insider_tasks import calculate_insider_signals
    from .sensitivity_tasks import calculate_sensitivity_profiles

    results = {}
    results["growth_stage"] = calculate_growth_stages()
    results["capital_dna"] = calculate_capital_dna()
    results["sensitivity"] = calculate_sensitivity_profiles()
    results["insider"] = calculate_insider_signals()
    logger.info(f"All profiles: {results}")
    return results
