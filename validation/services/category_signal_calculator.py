"""
Task 4: Category Signal 계산

카테고리별 소속 지표의 percentile_rank 균등 평균 → signal(green/yellow/red/gray)
- value_status='normal'인 지표만 포함
- handling_mode='special' 산업 → 해당 카테고리 gray
"""

import logging
from decimal import Decimal

from packages.shared.stocks.models import (
    IndustryClassification,
    SP500Constituent,
    Stock,
)
from validation.models import CategorySignal, CompanyBenchmarkDelta

logger = logging.getLogger(__name__)

# 카테고리별 소속 지표 매핑
CATEGORY_METRICS = {
    "profitability": ["gross_margin", "operating_margin", "net_margin", "roe", "roic"],
    "growth": [
        "revenue_growth_yoy",
        "operating_income_growth",
        "fcf_growth_yoy",
        "rev_growth_vs_industry",
    ],
    "financial_structure": [
        "debt_to_equity",
        "current_ratio",
        "interest_coverage",
        "net_debt_to_ebitda",
        "cash_runway_years",
        "short_term_debt_pct",
    ],
    "cash_flow_quality": [
        "fcf_margin",
        "ocf_to_net_income",
        "capex_to_ocf",
        "accruals_ratio",
        "fcf_conversion",
        "cash_from_ops_trend",
    ],
    "operational_efficiency": [
        "dso",
        "ar_to_revenue",
        "inventory_turnover_days",
        "inventory_vs_sales_growth",
        "sga_to_revenue",
        "asset_turnover",
    ],
    "dilution_shareholder": [
        "dilution_3y_cum",
        "sbc_to_revenue",
        "buyback_offsets_sbc",
        "net_shareholder_yield",
    ],
    "valuation": ["pe_ratio", "ev_to_ebitda", "fcf_yield"],
}

# special 산업에서 gray 처리할 카테고리
SPECIAL_GRAY_CATEGORIES = {
    "financial_structure",  # 금융/보험
    "cash_flow_quality",  # REIT
}

CATEGORY_DISPLAY = {
    "profitability": "수익성",
    "growth": "성장성",
    "financial_structure": "재무구조",
    "cash_flow_quality": "현금흐름",
    "operational_efficiency": "운영효율",
    "dilution_shareholder": "희석/주주가치",
    "valuation": "밸류에이션",
}


class CategorySignalCalculator:
    def calculate_for_symbol(self, symbol: str, fiscal_year: int = None) -> dict:
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return {"symbol": symbol, "error": "Stock not found"}

        # fiscal_year 결정 (최신 연도)
        if fiscal_year is None:
            latest_fy = (
                CompanyBenchmarkDelta.objects.filter(symbol=stock)
                .values_list("fiscal_year", flat=True)
                .distinct()
                .order_by("-fiscal_year")
                .first()
            )
            if not latest_fy:
                return {"symbol": symbol, "error": "No benchmark data"}
            fiscal_year = latest_fy

        # handling_mode 확인
        is_special = False
        special_note = ""
        if stock.industry:
            ic = IndustryClassification.objects.filter(
                industry__iexact=stock.industry
            ).first()
            if ic and ic.handling_mode == "special":
                is_special = True
                special_note = ic.special_note

        signals_created = 0
        for category, metric_codes in CATEGORY_METRICS.items():
            signal, score, reason, metric_count, valid_count, contribs = (
                self._calc_category(
                    stock, fiscal_year, category, metric_codes, is_special, special_note
                )
            )

            CategorySignal.objects.update_or_create(
                symbol=stock,
                category=category,
                fiscal_year=fiscal_year,
                defaults={
                    "signal": signal,
                    "score": Decimal(str(round(score, 2)))
                    if score is not None
                    else None,
                    "signal_reason": reason,
                    "metric_count": metric_count,
                    "valid_metric_count": valid_count,
                    "contributing_metrics": contribs,
                },
            )
            signals_created += 1

        return {
            "symbol": symbol,
            "fiscal_year": fiscal_year,
            "signals_created": signals_created,
        }

    def calculate_for_symbols(self, symbols: list[str] = None) -> dict:
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True).values_list(
                    "symbol", flat=True
                )
            )

        total = len(symbols)
        success = 0
        fail = 0

        for i, symbol in enumerate(symbols):
            try:
                result = self.calculate_for_symbol(symbol)
                if result.get("error"):
                    fail += 1
                else:
                    success += 1
            except Exception as e:
                fail += 1
                logger.error(f"[{i + 1}/{total}] signal calc failed {symbol}: {e}")

            if (i + 1) % 50 == 0:
                logger.info(
                    f"Signal progress: {i + 1}/{total} (success={success}, fail={fail})"
                )

        return {"total": total, "success": success, "errors": fail}

    def _calc_category(
        self, stock, fiscal_year, category, metric_codes, is_special, special_note
    ):
        """
        단일 카테고리의 signal 계산.
        Returns: (signal, score, reason, metric_count, valid_count, contributing_metrics)
        """
        metric_count = len(metric_codes)

        # special 산업 + 해당 카테고리 → gray
        if is_special and category in SPECIAL_GRAY_CATEGORIES:
            return (
                "gray",
                None,
                special_note or "특수 산업 특성상 일반 해석과 다를 수 있습니다",
                metric_count,
                0,
                [],
            )

        # 해당 카테고리 지표들의 percentile_rank 수집
        deltas = CompanyBenchmarkDelta.objects.filter(
            symbol=stock,
            fiscal_year=fiscal_year,
            metric_code_id__in=metric_codes,
            percentile_rank__isnull=False,
        )

        # value_status='normal'인 snapshot과 매칭
        from packages.shared.metrics.models import CompanyMetricSnapshot

        normal_metrics = set(
            CompanyMetricSnapshot.objects.filter(
                symbol=stock,
                fiscal_year=fiscal_year,
                metric_code_id__in=metric_codes,
                value_status="normal",
            ).values_list("metric_code_id", flat=True)
        )

        valid_deltas = [d for d in deltas if d.metric_code_id in normal_metrics]
        valid_count = len(valid_deltas)

        if valid_count == 0:
            return ("gray", None, "데이터 부족", metric_count, 0, [])

        # percentile_rank 균등 평균
        pct_values = [float(d.percentile_rank) for d in valid_deltas]
        score = sum(pct_values) / len(pct_values)

        # signal 판정
        if score >= 65:
            signal = "green"
        elif score >= 35:
            signal = "yellow"
        else:
            signal = "red"

        # signal_reason 생성
        green_count = sum(1 for p in pct_values if p >= 65)
        display = CATEGORY_DISPLAY.get(category, category)
        reason = f"{valid_count}개 지표 중 {green_count}개 업종 상위 35%"

        # contributing_metrics
        contribs = [
            {
                "metric": d.metric_code_id,
                "percentile": float(d.percentile_rank),
                "value": float(d.company_value) if d.company_value else None,
            }
            for d in valid_deltas
        ]

        return (signal, score, reason, metric_count, valid_count, contribs)
