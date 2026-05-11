"""
1차 검증 시드 데이터 커맨드

1. MetricDefinition 34개 지표 갱신 (설계서 섹션 4 기준 unit/not_applicable_reason 반영)
2. IndustryClassification handling_mode 시딩 (Banks, Insurance, REIT, Utilities → special)
"""

from django.core.management.base import BaseCommand
from metrics.models import MetricDefinition
from stocks.models import IndustryClassification, SP500Constituent


# ── 34개 지표 시드 (설계서 섹션 4 기준) ──
METRIC_UPDATES = {
    # profitability (5)
    'gross_margin': {'unit': 'ratio', 'not_applicable_reason': ''},
    'operating_margin': {'unit': 'ratio', 'not_applicable_reason': ''},
    'net_margin': {'unit': 'ratio', 'not_applicable_reason': ''},
    'roe': {'unit': 'ratio', 'not_applicable_reason': ''},
    'roic': {'unit': 'ratio', 'not_applicable_reason': ''},
    # growth (4)
    'revenue_growth_yoy': {'unit': 'ratio', 'not_applicable_reason': ''},
    'operating_income_growth': {'unit': 'ratio', 'not_applicable_reason': ''},
    'fcf_growth_yoy': {'unit': 'ratio', 'not_applicable_reason': ''},
    'rev_growth_vs_industry': {'unit': 'percent_point', 'not_applicable_reason': ''},
    # financial_structure (6)
    'debt_to_equity': {'unit': 'multiple', 'not_applicable_reason': ''},
    'current_ratio': {'unit': 'multiple', 'not_applicable_reason': ''},
    'interest_coverage': {'unit': 'multiple', 'not_applicable_reason': '무차입 기업'},
    'net_debt_to_ebitda': {'unit': 'multiple', 'not_applicable_reason': ''},
    'cash_runway_years': {'unit': 'years', 'not_applicable_reason': '흑자 기업'},
    'short_term_debt_pct': {'unit': 'pct', 'not_applicable_reason': ''},
    # cash_flow_quality (6)
    'fcf_margin': {'unit': 'ratio', 'not_applicable_reason': ''},
    'ocf_to_net_income': {'unit': 'multiple', 'not_applicable_reason': ''},
    'capex_to_ocf': {'unit': 'ratio', 'not_applicable_reason': ''},
    'accruals_ratio': {'unit': 'ratio', 'not_applicable_reason': ''},
    'fcf_conversion': {'unit': 'ratio', 'not_applicable_reason': ''},
    'cash_from_ops_trend': {'unit': 'ratio', 'not_applicable_reason': ''},
    # operational_efficiency (6)
    'dso': {'unit': 'days', 'not_applicable_reason': ''},
    'ar_to_revenue': {'unit': 'ratio', 'not_applicable_reason': ''},
    'inventory_turnover_days': {'unit': 'days', 'not_applicable_reason': '서비스 기업 (재고 없음)'},
    'inventory_vs_sales_growth': {'unit': 'percent_point', 'not_applicable_reason': '서비스 기업 (재고 없음)'},
    'sga_to_revenue': {'unit': 'ratio', 'not_applicable_reason': ''},
    'asset_turnover': {'unit': 'multiple', 'not_applicable_reason': ''},
    # dilution_shareholder (4)
    'dilution_3y_cum': {'unit': 'pct', 'not_applicable_reason': ''},
    'sbc_to_revenue': {'unit': 'ratio', 'not_applicable_reason': ''},
    'buyback_offsets_sbc': {'unit': 'ratio', 'not_applicable_reason': ''},
    'net_shareholder_yield': {'unit': 'ratio', 'not_applicable_reason': ''},
    # valuation (3)
    'pe_ratio': {'unit': 'multiple', 'not_applicable_reason': ''},
    'ev_to_ebitda': {'unit': 'multiple', 'not_applicable_reason': ''},
    'fcf_yield': {'unit': 'ratio', 'not_applicable_reason': ''},
}

# ── 특수 산업 키워드 매칭 (handling_mode='special') ──
# DB에서 industry 값 형식이 다를 수 있으므로 (em dash vs hyphen 등) 키워드 기반 매칭
SPECIAL_KEYWORDS = {
    'Bank': '금융업 특성상 일반 기업과 다른 기준이 적용됩니다',
    'Insurance': '보험업 특성상 일반 기업과 다른 기준이 적용됩니다',
    'REIT': 'REIT 특성상 FCF 계열 지표 해석이 제한됩니다',
    'Utilit': '유틸리티 특성상 일부 지표 해석이 제한됩니다',
}


class Command(BaseCommand):
    help = '1차 검증 시드 데이터: MetricDefinition unit/not_applicable_reason 갱신 + IndustryClassification 시딩'

    def handle(self, *args, **options):
        self._update_metric_definitions()
        self._seed_industry_classifications()

    def _update_metric_definitions(self):
        updated = 0
        missing = []
        for code, updates in METRIC_UPDATES.items():
            try:
                md = MetricDefinition.objects.get(pk=code)
                changed = False
                for field, value in updates.items():
                    if getattr(md, field) != value:
                        setattr(md, field, value)
                        changed = True
                if changed:
                    md.save()
                    updated += 1
            except MetricDefinition.DoesNotExist:
                missing.append(code)

        self.stdout.write(self.style.SUCCESS(
            f'MetricDefinition 갱신: {updated}개 변경, {len(missing)}개 미존재'
        ))
        if missing:
            self.stdout.write(self.style.WARNING(f'  미존재: {missing}'))

    def _seed_industry_classifications(self):
        # S&P 500 종목들의 industry 목록 수집
        industries = set(
            SP500Constituent.objects.filter(is_active=True)
            .exclude(sub_sector='')
            .values_list('sub_sector', flat=True)
        )
        # Stock 모델에서도 industry 수집
        from stocks.models import Stock
        stock_industries = set(
            Stock.objects.exclude(industry__isnull=True)
            .exclude(industry='')
            .values_list('industry', flat=True)
        )
        all_industries = industries | stock_industries

        created = 0
        updated_special = 0
        for industry in all_industries:
            if not industry:
                continue
            mode = 'standard'
            note = ''
            for keyword, default_note in SPECIAL_KEYWORDS.items():
                if keyword.lower() in industry.lower():
                    mode = 'special'
                    note = default_note
                    break

            obj, was_created = IndustryClassification.objects.update_or_create(
                industry=industry,
                defaults={
                    'handling_mode': mode,
                    'special_note': note,
                },
            )
            if was_created:
                created += 1
            if mode == 'special':
                updated_special += 1

        total = IndustryClassification.objects.count()
        special_count = IndustryClassification.objects.filter(handling_mode='special').count()
        self.stdout.write(self.style.SUCCESS(
            f'IndustryClassification 시딩: {total}개 (신규 {created}개, special {special_count}개)'
        ))
