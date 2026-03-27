from django.contrib import admin
from .models import (
    CompanySensitivityProfile, CompanyGrowthStage, CompanyCapitalDNA,
    CompanyInsiderSignal, CompanyNarrativeTag, CompanyEventReaction,
)


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


@admin.register(CompanyInsiderSignal)
class CompanyInsiderSignalAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'insider_signal', 'smart_money_signal', 'institutional_ownership_pct', 'short_interest_pct']
    list_filter = ['insider_signal', 'smart_money_signal', 'top_holder_action']
    search_fields = ['symbol__symbol']


@admin.register(CompanyNarrativeTag)
class CompanyNarrativeTagAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'primary_narrative', 'narrative_sentiment', 'analyst_consensus', 'generated_by']
    list_filter = ['narrative_sentiment', 'analyst_consensus', 'generated_by']
    search_fields = ['symbol__symbol', 'primary_narrative']


@admin.register(CompanyEventReaction)
class CompanyEventReactionAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'event_type', 'sample_count', 'avg_return_1d', 'reaction_grade', 'confidence']
    list_filter = ['reaction_grade', 'confidence', 'event_type']
    search_fields = ['symbol__symbol', 'event_type']
