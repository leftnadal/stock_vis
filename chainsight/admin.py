from django.contrib import admin
from .models import CompanySensitivityProfile, CompanyGrowthStage, CompanyCapitalDNA


@admin.register(CompanySensitivityProfile)
class CompanySensitivityProfileAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'rate_sensitivity', 'forex_sensitivity', 'commodity_sensitivity', 'beta']
    list_filter = ['rate_sensitivity', 'forex_sensitivity', 'is_regulated_industry']
    search_fields = ['symbol__symbol']


@admin.register(CompanyGrowthStage)
class CompanyGrowthStageAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'stage', 'revenue_cagr_3y', 'fcf_trend', 'confidence']
    list_filter = ['stage', 'confidence', 'fcf_trend']
    search_fields = ['symbol__symbol']


@admin.register(CompanyCapitalDNA)
class CompanyCapitalDNAAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'capital_type', 'rd_to_revenue', 'capex_to_revenue', 'buyback_yield']
    list_filter = ['capital_type', 'rd_trend', 'capex_trend']
    search_fields = ['symbol__symbol']
