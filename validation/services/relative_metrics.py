"""
Task 3.5: 상대 지표 계산

rev_growth_vs_industry = 자사 revenue_growth_yoy - industry median revenue_growth_yoy
Task 3에서 계산된 IndustryMetricBenchmark 참조.
"""

import logging
from decimal import Decimal

from django.utils import timezone

from stocks.models import Stock, SP500Constituent
from metrics.models import CompanyMetricSnapshot, IndustryMetricBenchmark
from validation.models import CompanyBenchmarkDelta

logger = logging.getLogger(__name__)


class RelativeMetricCalculator:

    def calculate_for_symbols(self, symbols: list[str] = None) -> dict:
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True)
                .values_list('symbol', flat=True)
            )

        total = len(symbols)
        success = 0
        skip = 0

        for i, symbol in enumerate(symbols):
            try:
                result = self._calc_rev_growth_vs_industry(symbol)
                if result:
                    success += 1
                else:
                    skip += 1
            except Exception as e:
                skip += 1
                logger.error(f"relative_metrics failed {symbol}: {e}")

            if (i + 1) % 100 == 0:
                logger.info(f"Relative progress: {i+1}/{total}")

        return {'total': total, 'success': success, 'skip': skip}

    def _calc_rev_growth_vs_industry(self, symbol: str) -> bool:
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock or not stock.industry:
            return False

        # 자사 revenue_growth_yoy snapshot 조회
        company_snaps = CompanyMetricSnapshot.objects.filter(
            symbol_id=symbol,
            metric_code_id='revenue_growth_yoy',
            value_status='normal',
            metric_value__isnull=False,
        )
        if not company_snaps.exists():
            return False

        updated = False
        for snap in company_snaps:
            # industry median 조회
            ind_bench = IndustryMetricBenchmark.objects.filter(
                industry=stock.industry,
                fiscal_year=snap.fiscal_year,
                metric_code_id='revenue_growth_yoy',
            ).first()

            if not ind_bench or ind_bench.median_value is None:
                continue

            company_val = float(snap.metric_value)
            industry_median = float(ind_bench.median_value)
            relative = company_val - industry_median

            # CompanyMetricSnapshot에 rev_growth_vs_industry 저장
            CompanyMetricSnapshot.objects.update_or_create(
                symbol=stock,
                fiscal_year=snap.fiscal_year,
                metric_code_id='rev_growth_vs_industry',
                defaults={
                    'metric_value': Decimal(str(round(relative, 6))),
                    'value_status': 'normal',
                    'exclusion_reason': '',
                    'source_detail': {
                        'company_growth': company_val,
                        'industry_median': industry_median,
                        'calculated_at': timezone.now().isoformat(),
                    },
                }
            )
            updated = True

        return updated
